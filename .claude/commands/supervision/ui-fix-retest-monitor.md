---
description: Fix-Retest Monitor - Delegate bug fix to SCAR, monitor progress, retest when fixed
argument-hint: <project> <issue-number> <feature-name> <url> <deployment-type> <session-id>
---

# UI Fix-Retest Monitor

## Mission

Monitor SCAR fixing a specific UI bug. Delegate RCA and fix implementation, verify the fix, retest the feature, and report results.

**Context Usage**: ~15-20k tokens (issue-specific, exits after completion)

**Lifecycle**: Spawn → Delegate → Monitor → Verify → Retest → Exit

## Arguments

- **$1**: Project name (e.g., "consilio")
- **$2**: Issue number (e.g., "142")
- **$3**: Feature name (e.g., "coach-chat")
- **$4**: Deployment URL (e.g., "http://localhost:3002")
- **$5**: Deployment type (docker|native|production)
- **$6**: Session ID (e.g., "ui-test-1736621400")

## Task Flow

### Step 1: Initialize Monitor

```bash
PROJECT=$1
ISSUE=$2
FEATURE=$3
URL=$4
DEPLOY_TYPE=$5
SESSION=$6

# Create monitor directory
MONITOR_DIR=".agents/ui-testing/session-$SESSION/monitors/issue-$ISSUE"
mkdir -p $MONITOR_DIR

echo "Monitoring issue #$ISSUE for feature: $FEATURE"
echo "URL: $URL"

# Initialize monitor log
cat > $MONITOR_DIR/monitor.log <<EOF
UI Fix-Retest Monitor
Issue: #$ISSUE
Feature: $FEATURE
Started: $(date -u +%Y-%m-%dT%H:%M:%SZ)

---

EOF
```

### Step 2: Delegate RCA to SCAR

**Post instruction to GitHub issue:**

```bash
# Post RCA instruction
gh issue comment $ISSUE --repo "gpt153/$PROJECT" --body "@scar /command-invoke rca $ISSUE"

echo "Posted RCA instruction to issue #$ISSUE" | tee -a $MONITOR_DIR/monitor.log
```

**Wait for acknowledgment (20 seconds):**

```bash
sleep 20

# Check if SCAR acknowledged
LATEST_COMMENT=$(gh issue view $ISSUE --repo "gpt153/$PROJECT" --json comments --jq '.comments[-1].body')

if echo "$LATEST_COMMENT" | grep -q "SCAR is on the case\|I'll analyze\|Starting RCA"; then
  echo "✅ SCAR acknowledged RCA request" | tee -a $MONITOR_DIR/monitor.log
else
  echo "⚠️ No acknowledgment from SCAR yet" | tee -a $MONITOR_DIR/monitor.log

  # Retry after 40 seconds
  sleep 40
  LATEST_COMMENT=$(gh issue view $ISSUE --repo "gpt153/$PROJECT" --json comments --jq '.comments[-1].body')

  if echo "$LATEST_COMMENT" | grep -q "SCAR is on the case\|I'll analyze\|Starting RCA"; then
    echo "✅ SCAR acknowledged (retry 1)" | tee -a $MONITOR_DIR/monitor.log
  else
    echo "❌ SCAR still not responding after 60s" | tee -a $MONITOR_DIR/monitor.log
    echo "CRITICAL: SCAR may not be active. Please check SCAR status." | tee -a $MONITOR_DIR/monitor.log

    # Report blocker to supervisor
    # Update test-state.json with blocker
    exit 1
  fi
fi
```

### Step 3: Monitor RCA Progress

**Poll every 2 minutes until RCA complete:**

```bash
RCA_COMPLETE=false
RCA_ATTEMPTS=0
MAX_RCA_WAIT=30  # 30 attempts = 60 minutes max

while [ "$RCA_COMPLETE" = false ] && [ $RCA_ATTEMPTS -lt $MAX_RCA_WAIT ]; do
  sleep 120  # 2 minutes

  # Check issue comments for RCA completion indicators
  RECENT_COMMENTS=$(gh issue view $ISSUE --repo "gpt153/$PROJECT" --json comments --jq '.comments[-5:] | .[].body')

  # Look for RCA completion signals
  if echo "$RECENT_COMMENTS" | grep -q "Root Cause Analysis Complete\|RCA complete\|Root cause identified\|\.agents/rca-reports/"; then
    echo "✅ RCA complete detected" | tee -a $MONITOR_DIR/monitor.log
    RCA_COMPLETE=true
    break
  fi

  # Check if SCAR is asking for secrets/blockers
  if echo "$RECENT_COMMENTS" | grep -q "BLOCKED\|Missing secret\|requires.*secret\|STRIPE_SECRET_KEY\|OPENAI_API_KEY"; then
    echo "⚠️ BLOCKER DETECTED: Missing secret" | tee -a $MONITOR_DIR/monitor.log

    # Extract blocker message
    BLOCKER_MSG=$(echo "$RECENT_COMMENTS" | grep -A 5 "BLOCKED\|Missing secret")

    # Report to supervisor and user
    gh issue comment $ISSUE --repo "gpt153/$PROJECT" --body "$(cat <<EOF
⚠️ **UI Test Monitor: Blocker Detected**

SCAR has identified a blocker that requires user intervention:

$BLOCKER_MSG

**Required Action**: User must provide the missing secret or configuration.

After resolving, I will resume monitoring automatically.

---

**Monitor Status**: Paused (waiting for blocker resolution)
EOF
)"

    echo "Monitor paused - waiting for blocker resolution" | tee -a $MONITOR_DIR/monitor.log

    # Poll less frequently while blocked
    sleep 300  # 5 minutes
    RCA_ATTEMPTS=$((RCA_ATTEMPTS - 1))  # Don't count blocked time
    continue
  fi

  RCA_ATTEMPTS=$((RCA_ATTEMPTS + 1))
  echo "RCA in progress... (attempt $RCA_ATTEMPTS/$MAX_RCA_WAIT)" | tee -a $MONITOR_DIR/monitor.log
done

if [ "$RCA_COMPLETE" = false ]; then
  echo "❌ RCA timeout after $MAX_RCA_WAIT attempts (60 minutes)" | tee -a $MONITOR_DIR/monitor.log
  echo "CRITICAL: SCAR RCA did not complete in expected time" | tee -a $MONITOR_DIR/monitor.log

  # Report timeout to supervisor
  exit 1
fi
```

### Step 4: Delegate Fix Implementation

**Post fix instruction:**

```bash
# Post fix-rca instruction
gh issue comment $ISSUE --repo "gpt153/$PROJECT" --body "@scar /command-invoke fix-rca $ISSUE"

echo "Posted fix implementation instruction" | tee -a $MONITOR_DIR/monitor.log

# Wait for acknowledgment
sleep 20

LATEST_COMMENT=$(gh issue view $ISSUE --repo "gpt153/$PROJECT" --json comments --jq '.comments[-1].body')

if echo "$LATEST_COMMENT" | grep -q "SCAR is on the case\|implementing fix\|I'll fix"; then
  echo "✅ SCAR acknowledged fix request" | tee -a $MONITOR_DIR/monitor.log
else
  echo "⚠️ No acknowledgment from SCAR" | tee -a $MONITOR_DIR/monitor.log
fi
```

### Step 5: Monitor Fix Implementation

**Poll every 2 minutes until PR created:**

```bash
FIX_COMPLETE=false
FIX_ATTEMPTS=0
MAX_FIX_WAIT=60  # 60 attempts = 2 hours max

while [ "$FIX_COMPLETE" = false ] && [ $FIX_ATTEMPTS -lt $MAX_FIX_WAIT ]; do
  sleep 120  # 2 minutes

  # Check for PR creation
  RECENT_COMMENTS=$(gh issue view $ISSUE --repo "gpt153/$PROJECT" --json comments --jq '.comments[-5:] | .[].body')

  # Look for PR creation signals
  if echo "$RECENT_COMMENTS" | grep -q "PR created\|Pull request.*created\|#[0-9]\+"; then
    echo "✅ PR creation detected" | tee -a $MONITOR_DIR/monitor.log

    # Extract PR number
    PR_NUM=$(echo "$RECENT_COMMENTS" | grep -oP '#\K[0-9]+' | tail -1)
    echo "PR #$PR_NUM created" | tee -a $MONITOR_DIR/monitor.log

    FIX_COMPLETE=true
    break
  fi

  FIX_ATTEMPTS=$((FIX_ATTEMPTS + 1))
  echo "Fix implementation in progress... (attempt $FIX_ATTEMPTS/$MAX_FIX_WAIT)" | tee -a $MONITOR_DIR/monitor.log
done

if [ "$FIX_COMPLETE" = false ]; then
  echo "❌ Fix timeout after $MAX_FIX_WAIT attempts (2 hours)" | tee -a $MONITOR_DIR/monitor.log
  echo "CRITICAL: SCAR fix did not complete in expected time" | tee -a $MONITOR_DIR/monitor.log

  # Report timeout
  exit 1
fi
```

### Step 6: Verify Fix Implementation

**Run verify-scar-phase on the fix:**

```bash
# Determine phase number (usually 1 for fixes)
PHASE=1

echo "Verifying fix implementation..." | tee -a $MONITOR_DIR/monitor.log

# Run verification
VERIFY_OUTPUT=$(claude /command-invoke verify-scar-phase "$PROJECT" "$ISSUE" "$PHASE" 2>&1)

echo "$VERIFY_OUTPUT" > $MONITOR_DIR/verification.log

# Check verdict
if echo "$VERIFY_OUTPUT" | grep -q "✅ APPROVED"; then
  echo "✅ Verification APPROVED" | tee -a $MONITOR_DIR/monitor.log
  VERIFICATION_PASSED=true
elif echo "$VERIFY_OUTPUT" | grep -q "⚠️ NEEDS FIXES"; then
  echo "⚠️ Verification needs fixes" | tee -a $MONITOR_DIR/monitor.log
  VERIFICATION_PASSED=false

  # Post verification results to issue
  gh issue comment $ISSUE --repo "gpt153/$PROJECT" --body "$(cat <<EOF
⚠️ **Verification Needs Fixes**

The build verification found issues that need to be addressed:

\`\`\`
$(echo "$VERIFY_OUTPUT" | grep -A 20 "Issues to Fix")
\`\`\`

@scar please address the verification issues and update the PR.

---

**Monitor Status**: Waiting for fixes
EOF
)"

  # Wait for fixes and re-verify
  # (simplified: in practice, loop back to monitoring)
  exit 1

elif echo "$VERIFY_OUTPUT" | grep -q "❌ REJECTED"; then
  echo "❌ Verification REJECTED" | tee -a $MONITOR_DIR/monitor.log
  VERIFICATION_PASSED=false

  # Post rejection to issue
  gh issue comment $ISSUE --repo "gpt153/$PROJECT" --body "$(cat <<EOF
❌ **Verification Rejected**

The implementation verification failed:

\`\`\`
$(echo "$VERIFY_OUTPUT" | grep -A 20 "Issues to Fix")
\`\`\`

@scar please fix the issues listed above.

---

**Monitor Status**: Waiting for corrections
EOF
)"

  exit 1
fi
```

### Step 7: Retest Feature

**Run Playwright test for this specific feature:**

```bash
echo "Running feature retest..." | tee -a $MONITOR_DIR/monitor.log

# Navigate to worktree where fix was implemented
WORKTREE="/home/samuel/.archon/worktrees/$PROJECT/issue-$ISSUE"

if [ ! -d "$WORKTREE" ]; then
  echo "❌ Worktree not found: $WORKTREE" | tee -a $MONITOR_DIR/monitor.log
  exit 1
fi

cd "$WORKTREE"

# Find test file for this feature
FEATURE_SLUG=$(echo "$FEATURE" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
TEST_FILE="tests/$FEATURE_SLUG.spec.ts"

if [ ! -f "$TEST_FILE" ]; then
  echo "⚠️ Test file not found: $TEST_FILE" | tee -a $MONITOR_DIR/monitor.log
  echo "Searching for test file..." | tee -a $MONITOR_DIR/monitor.log

  # Try to find by feature name
  TEST_FILE=$(find tests -name "*$FEATURE_SLUG*" -o -name "*$(echo $FEATURE | tr ' ' '-')*" 2>/dev/null | head -1)

  if [ -z "$TEST_FILE" ]; then
    echo "❌ Cannot find test file for feature: $FEATURE" | tee -a $MONITOR_DIR/monitor.log
    exit 1
  fi
fi

echo "Test file: $TEST_FILE" | tee -a $MONITOR_DIR/monitor.log

# Run test
if [ "$DEPLOY_TYPE" = "docker" ]; then
  npm run test:e2e:docker -- "$TEST_FILE" > $MONITOR_DIR/retest-output.log 2>&1
else
  npm run test:e2e -- "$TEST_FILE" > $MONITOR_DIR/retest-output.log 2>&1
fi

RETEST_EXIT_CODE=$?

# Analyze retest results
cat $MONITOR_DIR/retest-output.log | tee -a $MONITOR_DIR/monitor.log

TESTS_RUN=$(grep -c "✓\|✗" $MONITOR_DIR/retest-output.log || echo "0")
TESTS_PASSED=$(grep -c "✓" $MONITOR_DIR/retest-output.log || echo "0")
TESTS_FAILED=$(grep -c "✗" $MONITOR_DIR/retest-output.log || echo "0")

echo "Retest results: $TESTS_PASSED/$TESTS_RUN passed" | tee -a $MONITOR_DIR/monitor.log
```

### Step 8A: Handle Retest Success

If retest passed:

```bash
if [ $RETEST_EXIT_CODE -eq 0 ] && [ $TESTS_FAILED -eq 0 ]; then
  echo "✅ RETEST PASSED - Bug is fixed!" | tee -a $MONITOR_DIR/monitor.log

  # Post success to issue
  gh issue comment $ISSUE --repo "gpt153/$PROJECT" --body "$(cat <<EOF
✅ **UI Test Retest: PASSED**

The fix has been verified and the feature now passes all tests.

**Retest Results**:
- Tests run: $TESTS_RUN
- Passed: $TESTS_PASSED ✅
- Failed: 0

**Evidence**: $MONITOR_DIR/retest-output.log

**PR**: #$PR_NUM

---

**Monitor Status**: ✅ COMPLETE

Feature "$FEATURE" is now working correctly.
EOF
)"

  # Update test-state.json
  # (Atomic update)
  cat >> $MONITOR_DIR/state-update.json <<EOF
{
  "features": {
    "$FEATURE": {
      "status": "passed",
      "tests_run": $TESTS_RUN,
      "all_passed": true,
      "fixed_from_issue": $ISSUE,
      "locked_for_fix": false,
      "completed": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    }
  },
  "bugs": {
    "$ISSUE": {
      "status": "fixed_verified",
      "pr": $PR_NUM,
      "retest_passed": true,
      "completed": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    }
  },
  "monitors": {
    "$ISSUE": {
      "status": "complete",
      "result": "success"
    }
  }
}
EOF

  echo "✅ Monitor complete - bug fixed and verified" | tee -a $MONITOR_DIR/monitor.log

  # Exit with success
  exit 0
fi
```

### Step 8B: Handle Retest Failure

If retest failed:

```bash
echo "❌ RETEST FAILED - Bug not fully fixed" | tee -a $MONITOR_DIR/monitor.log

# Capture new evidence
mkdir -p $MONITOR_DIR/retest-failure
cp -r playwright-report test-results $MONITOR_DIR/retest-failure/ 2>/dev/null

# Extract failure details
grep "✗" $MONITOR_DIR/retest-output.log > $MONITOR_DIR/retest-failure/failed-tests.txt
grep -A 5 "Error:" $MONITOR_DIR/retest-output.log > $MONITOR_DIR/retest-failure/errors.txt

# Create new GitHub issue for regression
NEW_ISSUE=$(gh issue create \
  --repo "gpt153/$PROJECT" \
  --title "UI Test Retest Failure: $FEATURE (after fix #$ISSUE)" \
  --label "bug,ui-test-failure,retest-failure,$FEATURE" \
  --body "$(cat <<EOF
## 🐛 UI Test Retest Failure: $FEATURE

**Original Issue**: #$ISSUE
**Fix PR**: #$PR_NUM
**Retest Failed**: $(date -u +%Y-%m-%dT%H:%M:%SZ)

---

## Problem

After implementing the fix in PR #$PR_NUM, the retest still fails.
This indicates either:
1. The fix is incomplete
2. The fix introduced a new bug
3. The test expectations need adjustment

---

## Retest Results

**Tests Run**: $TESTS_RUN
**Passed**: $TESTS_PASSED
**Failed**: $TESTS_FAILED ❌

**Failed Tests**:
\`\`\`
$(cat $MONITOR_DIR/retest-failure/failed-tests.txt)
\`\`\`

**Error Details**:
\`\`\`
$(head -50 $MONITOR_DIR/retest-failure/errors.txt)
\`\`\`

---

## Previous Fix Summary

**Original RCA**: See issue #$ISSUE
**Fix Implemented**: PR #$PR_NUM
**Verification**: ✅ Build passed
**Retest**: ❌ Tests still failing

---

## Recommended Action

@scar please:
1. Review the original fix in PR #$PR_NUM
2. Analyze why the retest is failing
3. Run deeper RCA: \`/command-invoke rca {NEW_ISSUE_NUMBER}\`
4. Implement additional fix: \`/command-invoke fix-rca {NEW_ISSUE_NUMBER}\`

---

**Created by**: UI Fix-Retest Monitor (automated)
EOF
)" --json number -q '.number')

echo "Created new issue #$NEW_ISSUE for retest failure" | tee -a $MONITOR_DIR/monitor.log

# Post to original issue
gh issue comment $ISSUE --repo "gpt153/$PROJECT" --body "$(cat <<EOF
❌ **Retest Failed**

The fix was implemented but tests still fail.

**New Issue Created**: #$NEW_ISSUE

The fix-retest monitor will now track the new issue.

---

**Monitor Status**: Transitioning to issue #$NEW_ISSUE
EOF
)"

# Update test-state.json
cat >> $MONITOR_DIR/state-update.json <<EOF
{
  "bugs": {
    "$ISSUE": {
      "status": "fix_failed_retest",
      "pr": $PR_NUM,
      "retest_passed": false,
      "new_issue": $NEW_ISSUE,
      "completed": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    },
    "$NEW_ISSUE": {
      "feature": "$FEATURE",
      "title": "UI Test Retest Failure: $FEATURE (after fix #$ISSUE)",
      "created": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
      "status": "pending_rca",
      "previous_attempt": $ISSUE
    }
  },
  "monitors": {
    "$ISSUE": {
      "status": "complete",
      "result": "retest_failed",
      "new_issue": $NEW_ISSUE
    }
  }
}
EOF

echo "❌ Monitor complete - retest failed, new issue created" | tee -a $MONITOR_DIR/monitor.log

# Exit with failure (supervisor will spawn new monitor for new issue)
exit 1
```

## Polling Strategy

**RCA Phase**: Poll every 2 minutes, max 30 attempts (60 minutes)

**Fix Phase**: Poll every 2 minutes, max 60 attempts (2 hours)

**Blocker Detected**: Poll every 5 minutes until resolved

## Blocker Handling

### Missing Secrets

If SCAR reports missing secret:

```markdown
⚠️ **BLOCKER: Missing Secret**

SCAR cannot proceed without: STRIPE_SECRET_KEY

**Required Action**:
1. Set secret: `/secret-set STRIPE_SECRET_KEY sk_test_...`
2. Sync to workspace: `/secret-sync`
3. Reply in issue when done

Monitor will resume automatically.
```

### Unclear Requirements

If SCAR asks for clarification:

```markdown
⚠️ **BLOCKER: Unclear Requirement**

SCAR needs clarification on expected behavior.

**Required Action**: User must respond to SCAR's question in the issue.

Monitor paused until resolved.
```

## State Updates

All updates to test-state.json should be atomic:

```bash
# Create temporary update file
cat > /tmp/state-update-$ISSUE.json <<EOF
{...}
EOF

# Apply update atomically (supervisor handles locking)
# In practice, write to a .pending file that supervisor processes
mv /tmp/state-update-$ISSUE.json .agents/ui-testing/session-$SESSION/updates/issue-$ISSUE.pending
```

## Communication

**To SCAR** (via GitHub): Technical instructions, verification results

**To Supervisor** (via state updates): Status changes, completion, failures

**To User** (via GitHub): Blockers that require intervention

## Success Criteria

- ✅ RCA delegated and completed
- ✅ Fix delegated and implemented
- ✅ Build verification passed
- ✅ Feature retest passed
- ✅ State updated correctly
- ✅ Context freed (exit after completion)

---

**Monitor bug fix cycle** - this monitor completes and exits after fix is verified or new issue created.
