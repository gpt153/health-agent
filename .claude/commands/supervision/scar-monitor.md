---
description: Monitor subagent - tracks SCAR progress on a single issue (spawned by supervisor)
argument-hint: <issue-number> <scar-command>
---

# SCAR Monitor: Issue Monitoring Subagent

**NOTE**: This subagent is typically spawned by `/supervise` or `/supervise-issue`. You rarely invoke it directly.

## Arguments

- `$1`: Issue number (e.g., "42")
- `$2`: SCAR command to post (e.g., "/command-invoke plan-feature-github 'Add notifications'")

## Mission

Autonomous monitoring of SCAR's work on a specific issue. Handles instruction posting, start verification, progress tracking, completion detection, and verification.

## Design Principle

**Minimal context usage** - This is a worker subagent that reports back concisely.

## Workflow

### 1. Post SCAR Instruction

```bash
ISSUE_NUM=$1
SCAR_CMD="$2"

# Post the @scar instruction
gh issue comment $ISSUE_NUM --body "@scar $SCAR_CMD"

# Log the action
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) POSTED: $SCAR_CMD" >> /tmp/monitor-$ISSUE_NUM.log
```

### 2. Verify SCAR Started

**20-second check:**
```bash
sleep 20

# Check for acknowledgment
RESPONSE=$(gh issue view $ISSUE_NUM --json comments --jq '.comments[-5:] | .[] | select(.body | contains("SCAR is on the case")) | .body')

if [ -n "$RESPONSE" ]; then
  echo "✅ SCAR acknowledged"
else
  echo "❌ No acknowledgment - retry 1"
  sleep 40
  # Check again...
fi
```

**Retry logic:**
- Attempt 1: 20s wait
- Attempt 2: 40s wait (cumulative 60s)
- Attempt 3: 60s wait (cumulative 120s)
- After 3 failures: Report unresponsive to supervisor

**If unresponsive:**
```markdown
Return to supervisor:
{
  "issue": 42,
  "status": "failed_start",
  "error": "SCAR unresponsive after 3 attempts (2min total)",
  "action": "manual_intervention_needed"
}
```

### 3. Monitor Progress

**Polling loop (every 2min):**

```bash
while true; do
  sleep 120  # 2 minutes

  # Fetch recent activity
  COMMENTS=$(gh issue view $ISSUE_NUM --json comments --jq '.comments[-10:]')

  # Check for signals
  COMPLETION=$(echo "$COMMENTS" | grep -E "Implementation complete|PR created|All validation passed")
  ERROR=$(echo "$COMMENTS" | grep -E "Error:|Failed:|Cannot proceed")
  ACTIVITY=$(echo "$COMMENTS" | grep -E "Working on|Created|Running tests")

  # Detect completion
  if [ -n "$COMPLETION" ]; then
    echo "✅ SCAR completed"
    break
  fi

  # Detect errors
  if [ -n "$ERROR" ]; then
    echo "⚠️ Error detected: $ERROR"
    # Log but continue monitoring (SCAR may retry)
  fi

  # Track last activity
  if [ -n "$ACTIVITY" ]; then
    LAST_ACTIVITY=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  fi

  # Inactivity check (30min without updates)
  TIME_SINCE_ACTIVITY=$(($(date +%s) - $(date -d "$LAST_ACTIVITY" +%s)))
  if [ $TIME_SINCE_ACTIVITY -gt 1800 ]; then
    echo "⚠️ No activity for 30min - assuming completion"
    break
  fi
done
```

### 4. Extract Implementation Details

**Parse SCAR's final comments for:**
- PR URL: Extract from "PR created at {url}" or PR link
- Branch name: Extract from "feature-{name}" mentions
- Worktree path: Infer from project structure
- Phase number: Usually 1 (planning+implementation) or 2 (if separate)

**Store details:**
```json
{
  "pr_url": "https://github.com/user/repo/pull/52",
  "branch": "feature-streaming-api",
  "worktree": "/home/samuel/.archon/worktrees/consilio/issue-42/",
  "phase": 1
}
```

### 5. Verify Implementation

**Invoke verification subagent:**

```bash
# Get project name from current directory
PROJECT=$(basename $(pwd))

# Run verification
# (This would be via Task tool invoking /verify-scar-phase)
```

**Verification command:**
`/verify-scar-phase $PROJECT $ISSUE_NUM 1`

**Wait for result:**
- APPROVED ✅
- REJECTED ❌
- NEEDS_FIXES 🔧

### 6. Handle Verification Result

**If APPROVED:**
```markdown
## ✅ Issue #$ISSUE_NUM Complete

**PR**: {pr-url}
**Verification**: APPROVED ✅

{High-level summary}

**Supervision**: Complete
```

Post to issue and return to supervisor:
```json
{
  "issue": 42,
  "status": "completed",
  "pr_url": "{url}",
  "verification": "approved",
  "duration_minutes": 45
}
```

**If REJECTED:**
```bash
# Post verification failures to issue
gh issue comment $ISSUE_NUM --body "## ⚠️ Verification Failed

{List of failures from verification}

@scar please fix these issues and re-validate."
```

Return to supervisor:
```json
{
  "issue": 42,
  "status": "verification_failed",
  "retry_attempt": 1,
  "failures": [{verification errors}]
}
```

**If NEEDS_FIXES:**
Post specific fixes needed, wait for SCAR to address, re-verify.

### 7. Report Back to Supervisor

**Final report structure:**

```json
{
  "issue": 42,
  "status": "completed" | "failed" | "blocked",
  "pr_url": "https://...",
  "branch": "feature-name",
  "verification": "approved" | "rejected" | "needs_fixes",
  "duration_minutes": 45,
  "scar_retries": 0,
  "verification_retries": 1,
  "final_state": {
    "files_changed": 5,
    "tests_added": 12,
    "build_passing": true
  }
}
```

## Error Handling

### SCAR Unresponsive
- Try 3 times with increasing delays
- Report to supervisor
- Don't block indefinitely

### SCAR Asks Question
- Detect question patterns in comments
- Report to supervisor with question text
- Pause monitoring until user responds
- Resume when answer detected

### Verification Fails Multiple Times
- Allow up to 3 verification attempts
- After 3 failures: Escalate to supervisor
- Don't loop forever

### Build Breaks
- If verification shows build failure
- Report to supervisor immediately
- Suggest rollback or hotfix

## State Tracking

**Maintain minimal state:**
```json
{
  "issue": 42,
  "current_status": "monitoring",
  "started": "2024-01-08T10:00:00Z",
  "last_activity": "2024-01-08T10:45:00Z",
  "retries": 0,
  "errors_seen": []
}
```

**Update every poll cycle** to detect hangs/crashes.

## Communication

**To Supervisor (Concise JSON):**
```json
{
  "issue": 42,
  "status": "update",
  "progress": "60%",
  "current_action": "Running tests",
  "errors": []
}
```

**To User (via supervisor, strategic):**
Supervisor handles user communication - monitor just reports data.

**To SCAR (via GitHub comments, technical):**
```markdown
@scar verification failed:
- Build error: TypeScript type mismatch in src/api/routes.ts:45
- Missing test: No test for error handling in streamHandler
- Mock detected: src/services/notification.ts line 78 uses MOCK_DATA

Please fix and re-run validation.
```

## Performance

**Target metrics:**
- Detection latency: <2min from SCAR completion
- Verification latency: <5min from detection
- False positives: <5% (don't mark incomplete as done)
- False negatives: <1% (don't miss actual completions)

## Success Criteria

- ✅ Detects SCAR start within 2min
- ✅ Polls every 2min reliably
- ✅ Detects completion within 2min of signal
- ✅ Runs verification automatically
- ✅ Reports results accurately to supervisor
- ✅ Minimal context usage (short reports)

---

**This subagent runs autonomously** - spawned by supervisor, runs until completion, reports back.
