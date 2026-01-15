---
description: Regression Test Runner - Run complete test suite to catch regressions after fixes
argument-hint: <project> <url> <deployment-type> <session-id>
---

# UI Regression Test Runner

## Mission

Execute complete Playwright test suite to verify all features still work after bug fixes. Detects regressions introduced during fix implementations.

**Context Usage**: ~25-35k tokens (comprehensive, exits after reporting)

**Lifecycle**: Spawn → Test All Features → Report → Exit

## Arguments

- **$1**: Project name (e.g., "consilio")
- **$2**: Deployment URL (e.g., "http://localhost:3002")
- **$3**: Deployment type (docker|native|production)
- **$4**: Session ID (e.g., "ui-test-1736621400")

## Task Flow

### Step 1: Setup Regression Test

```bash
PROJECT=$1
URL=$2
DEPLOY_TYPE=$3
SESSION=$4

# Create regression test directory
REGRESSION_DIR=".agents/ui-testing/session-$SESSION/regression"
mkdir -p $REGRESSION_DIR

echo "Running regression test suite..."
echo "Project: $PROJECT"
echo "URL: $URL"
echo "Type: $DEPLOY_TYPE"
```

### Step 2: Verify All Features Passed Initial Tests

Check test-state.json to ensure all features completed:

```bash
# Read test state
TEST_STATE=".agents/ui-testing/test-state.json"

if [ ! -f "$TEST_STATE" ]; then
  echo "❌ ERROR: Test state file not found"
  exit 1
fi

# Count features
TOTAL_FEATURES=$(jq -r '.stats.total_features' $TEST_STATE)
PASSED_FEATURES=$(jq -r '.stats.passed' $TEST_STATE)
FAILED_FEATURES=$(jq -r '.stats.failed' $TEST_STATE)
IN_PROGRESS=$(jq -r '.stats.in_progress' $TEST_STATE)

echo "Feature Status:"
echo "  Total: $TOTAL_FEATURES"
echo "  Passed: $PASSED_FEATURES"
echo "  Failed: $FAILED_FEATURES"
echo "  In Progress: $IN_PROGRESS"

if [ "$FAILED_FEATURES" -gt 0 ] || [ "$IN_PROGRESS" -gt 0 ]; then
  echo "⚠️ WARNING: Not all features passed or completed"
  echo "Regression test should only run when all features pass."
  echo ""
  echo "Continue anyway? (y/n)"

  # In automated context, skip regression if not ready
  echo "Skipping regression - features not ready"
  exit 1
fi

echo "✅ All $TOTAL_FEATURES features passed - proceeding with regression"
```

### Step 3: Run Complete Test Suite

Run ALL Playwright tests (not individual features):

```bash
echo "Running full test suite..." | tee $REGRESSION_DIR/regression.log

# Determine test command
if [ "$DEPLOY_TYPE" = "docker" ]; then
  TEST_CMD="npm run test:e2e:docker"
else
  TEST_CMD="npm run test:e2e"
fi

echo "Command: $TEST_CMD" | tee -a $REGRESSION_DIR/regression.log

# Run complete suite
$TEST_CMD > $REGRESSION_DIR/test-output.log 2>&1
EXIT_CODE=$?

# Display output
cat $REGRESSION_DIR/test-output.log | tee -a $REGRESSION_DIR/regression.log
```

### Step 4: Analyze Results

Parse complete test results:

```bash
# Count results
TOTAL_TESTS=$(grep -c "✓\|✗" $REGRESSION_DIR/test-output.log || echo "0")
TESTS_PASSED=$(grep -c "✓" $REGRESSION_DIR/test-output.log || echo "0")
TESTS_FAILED=$(grep -c "✗" $REGRESSION_DIR/test-output.log || echo "0")

echo "" | tee -a $REGRESSION_DIR/regression.log
echo "Regression Results:" | tee -a $REGRESSION_DIR/regression.log
echo "  Total tests: $TOTAL_TESTS" | tee -a $REGRESSION_DIR/regression.log
echo "  Passed: $TESTS_PASSED" | tee -a $REGRESSION_DIR/regression.log
echo "  Failed: $TESTS_FAILED" | tee -a $REGRESSION_DIR/regression.log

# Calculate success rate
if [ "$TOTAL_TESTS" -gt 0 ]; then
  SUCCESS_RATE=$((TESTS_PASSED * 100 / TOTAL_TESTS))
  echo "  Success rate: $SUCCESS_RATE%" | tee -a $REGRESSION_DIR/regression.log
fi
```

### Step 5A: Handle Clean Regression

If all tests passed:

```bash
if [ $EXIT_CODE -eq 0 ] && [ $TESTS_FAILED -eq 0 ]; then
  echo "✅ REGRESSION CLEAN - All tests pass!" | tee -a $REGRESSION_DIR/regression.log

  # Create regression report
  cat > $REGRESSION_DIR/report.md <<EOF
# ✅ Regression Test: CLEAN

**Project**: $PROJECT
**Deployment**: $URL ($DEPLOY_TYPE)
**Completed**: $(date -u +%Y-%m-%dT%H:%M:%SZ)

---

## Summary

**All features working correctly** ✅

No regressions detected after bug fixes.

---

## Test Results

**Total Tests**: $TOTAL_TESTS
**Passed**: $TESTS_PASSED ✅
**Failed**: 0
**Success Rate**: 100%

---

## Tested Features

$(jq -r '.features | to_entries[] | "- \(.key): ✅ PASSED"' $TEST_STATE)

---

## Conclusion

🚀 **UI is production-ready!**

All features tested, all bugs fixed, regression clean.
Safe to deploy or merge to production.

---

**Full test output**: $REGRESSION_DIR/test-output.log
EOF

  # Update test-state.json
  cat > $REGRESSION_DIR/state-update.json <<EOF
{
  "regression_test": {
    "status": "passed",
    "total_tests": $TOTAL_TESTS,
    "passed": $TESTS_PASSED,
    "failed": 0,
    "success_rate": 100,
    "completed": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "report": "$REGRESSION_DIR/report.md"
  }
}
EOF

  echo "✅ Regression test complete - CLEAN" | tee -a $REGRESSION_DIR/regression.log

  # Exit with success
  exit 0
fi
```

### Step 5B: Handle Regression Failures

If any tests failed:

```bash
echo "❌ REGRESSION FAILURES DETECTED" | tee -a $REGRESSION_DIR/regression.log

# Capture failure evidence
mkdir -p $REGRESSION_DIR/failures
cp -r playwright-report test-results $REGRESSION_DIR/failures/ 2>/dev/null

# Extract failed tests
grep "✗" $REGRESSION_DIR/test-output.log > $REGRESSION_DIR/failures/failed-tests.txt

# Extract errors
grep -B 2 -A 5 "Error:" $REGRESSION_DIR/test-output.log > $REGRESSION_DIR/failures/errors.txt

echo "" | tee -a $REGRESSION_DIR/regression.log
echo "Failed tests:" | tee -a $REGRESSION_DIR/regression.log
cat $REGRESSION_DIR/failures/failed-tests.txt | tee -a $REGRESSION_DIR/regression.log

# Identify which features regressed
# Compare against test-state.json to see which features passed before
REGRESSED_FEATURES=""

# Parse failed test file names to identify features
while read -r failed_test; do
  # Extract feature name from test path
  # e.g., "✗ User Authentication › should login" → "user-authentication"
  FEATURE_NAME=$(echo "$failed_test" | grep -oP '(?<=tests/)[^/]+(?=\.spec)')

  if [ ! -z "$FEATURE_NAME" ]; then
    # Check if this feature passed before
    PREV_STATUS=$(jq -r ".features[\"$FEATURE_NAME\"].status" $TEST_STATE 2>/dev/null)

    if [ "$PREV_STATUS" = "passed" ]; then
      echo "⚠️ REGRESSION: $FEATURE_NAME (was passing, now failing)" | tee -a $REGRESSION_DIR/regression.log
      REGRESSED_FEATURES="$REGRESSED_FEATURES $FEATURE_NAME"
    fi
  fi
done < $REGRESSION_DIR/failures/failed-tests.txt

# Create GitHub issues for regressions
for feature in $REGRESSED_FEATURES; do
  # Create regression issue
  ISSUE_NUM=$(gh issue create \
    --repo "gpt153/$PROJECT" \
    --title "Regression: $feature (regression test failure)" \
    --label "bug,regression,ui-test-failure,$feature" \
    --body "$(cat <<EOF
## 🐛 Regression Detected: $feature

**Feature**: $feature
**Previous Status**: ✅ Passed
**Current Status**: ❌ Failing (regression)
**Detected**: $(date -u +%Y-%m-%dT%H:%M:%SZ)

---

## Problem

This feature was passing in initial tests but is now failing in the regression test.
This indicates a bug was introduced during fix implementation.

---

## Failed Tests

\`\`\`
$(grep "$feature" $REGRESSION_DIR/failures/failed-tests.txt)
\`\`\`

---

## Error Details

\`\`\`
$(grep -A 10 "$feature" $REGRESSION_DIR/failures/errors.txt | head -50)
\`\`\`

---

## Evidence

**Full test output**: $REGRESSION_DIR/test-output.log
**Screenshots**: Available in regression test artifacts
**Original passing test**: See test-state.json

---

## Analysis Needed

This regression likely occurred because:
1. A fix for another feature broke this feature
2. Shared components were modified incorrectly
3. State management changes affected multiple features

**Required Action**:

@scar please investigate and fix this regression:
1. Identify which recent fix caused this regression
2. Run RCA: \`/command-invoke rca {ISSUE_NUMBER}\`
3. Implement fix: \`/command-invoke fix-rca {ISSUE_NUMBER}\`

---

**Created by**: UI Regression Test Runner (automated)
EOF
)" --json number -q '.number')

  echo "Created regression issue #$ISSUE_NUM for $feature" | tee -a $REGRESSION_DIR/regression.log
done

# Create regression report
cat > $REGRESSION_DIR/report.md <<EOF
# ❌ Regression Test: FAILURES DETECTED

**Project**: $PROJECT
**Deployment**: $URL ($DEPLOY_TYPE)
**Completed**: $(date -u +%Y-%m-%dT%H:%M:%SZ)

---

## Summary

**Regressions detected** ❌

Some features that were passing now fail.
This indicates bugs introduced during fix implementations.

---

## Test Results

**Total Tests**: $TOTAL_TESTS
**Passed**: $TESTS_PASSED ✅
**Failed**: $TESTS_FAILED ❌
**Success Rate**: $SUCCESS_RATE%

---

## Regressed Features

$(echo "$REGRESSED_FEATURES" | tr ' ' '\n' | sed 's/^/- /')

---

## New Issues Created

$(gh issue list --repo "gpt153/$PROJECT" --label regression --limit 10 --json number,title --jq '.[] | "- #\(.number): \(.title)"')

---

## Next Steps

1. Fix-Retest Monitors will be spawned for each regression
2. Fixes will be implemented and verified
3. Regression test will run again
4. Process repeats until regression clean

---

## Evidence

**Full test output**: $REGRESSION_DIR/test-output.log
**Failed tests**: $REGRESSION_DIR/failures/failed-tests.txt
**Error details**: $REGRESSION_DIR/failures/errors.txt
**Screenshots**: $REGRESSION_DIR/failures/
EOF

  # Update test-state.json
  NEW_ISSUES=$(gh issue list --repo "gpt153/$PROJECT" --label regression --limit 10 --json number --jq '.[].number' | tr '\n' ',' | sed 's/,$//')

  cat > $REGRESSION_DIR/state-update.json <<EOF
{
  "regression_test": {
    "status": "failed",
    "total_tests": $TOTAL_TESTS,
    "passed": $TESTS_PASSED,
    "failed": $TESTS_FAILED,
    "success_rate": $SUCCESS_RATE,
    "new_bugs": [$NEW_ISSUES],
    "completed": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "report": "$REGRESSION_DIR/report.md"
  }
}
EOF

  echo "❌ Regression test complete - FAILURES FOUND" | tee -a $REGRESSION_DIR/regression.log

  # Exit with failure code
  exit 1
fi
```

### Step 6: Report to Supervisor

Results reported via:
1. **state-update.json** - Atomic state update for supervisor
2. **report.md** - Detailed markdown report
3. **Exit code** - 0 for success, 1 for failures

Supervisor will:
- If clean: Mark UI testing complete
- If failures: Spawn Fix-Retest Monitors for new issues, then rerun regression

## Regression Report Format

### Success Report

```markdown
# ✅ Regression Test: CLEAN

**Total Tests**: 35
**Passed**: 35 ✅
**Failed**: 0
**Success Rate**: 100%

All features working correctly. No regressions detected.

🚀 UI is production-ready!
```

### Failure Report

```markdown
# ❌ Regression Test: FAILURES DETECTED

**Total Tests**: 35
**Passed**: 33 ✅
**Failed**: 2 ❌
**Success Rate**: 94%

## Regressed Features
- coach-chat (was passing, now failing)
- payment-processing (was passing, now failing)

## New Issues Created
- #147: Regression - coach-chat
- #148: Regression - payment-processing

## Next Steps
Fix-Retest Monitors will be spawned for each regression.
Process continues until regression clean.
```

## Optimization: Parallel Test Execution

If project supports parallel Playwright execution:

```bash
# Run tests in parallel (faster)
npm run test:e2e:docker -- --workers=4

# Or configure in playwright.config.ts:
# workers: process.env.CI ? 1 : 4
```

## Communication

**To Supervisor**: Results via state-update.json and exit code

**To GitHub**: Create issues for regressions found

**To User**: None directly (supervisor handles user communication)

## Success Criteria

- ✅ Complete test suite executed
- ✅ Results accurately analyzed
- ✅ Regressions identified and reported
- ✅ GitHub issues created for failures
- ✅ State updated correctly
- ✅ Context freed (exit after reporting)

---

**Run regression test** - this runner completes and exits after reporting results.
