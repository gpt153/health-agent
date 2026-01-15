---
description: Autonomous UI testing with Playwright - test all features, find bugs, delegate fixes, retest until all pass
argument-hint: <project> <url> <deployment-type>
---

# UI Test Supervise: Autonomous E2E Testing Pipeline

## Mission

Orchestrate comprehensive UI testing by spawning test runners, monitoring bug fixes, and ensuring all features pass before completion.

**Duration**: Runs until all tests pass or stopped by user.

**Context Usage**: Minimal (~10-15k tokens) - all work delegated to subagents.

## Arguments

- **$1**: Project name (e.g., "consilio", "openhorizon.cc")
- **$2**: Deployment URL (e.g., "http://localhost:3002")
- **$3**: Deployment type (docker|native|production)

## Prerequisites

**Required:**
- UI must be deployed and accessible at provided URL
- Health check endpoint must respond (typically /api/health or /health)
- Playwright test infrastructure exists (Dockerfile.test, playwright.config.ts)
- Implementation plan exists (.agents/plans/*.md or IMPLEMENTATION_PLAN.md)

**Verify before starting:**
```bash
# Check URL is accessible
curl -I $2

# Check Playwright infrastructure
[ -f Dockerfile.test ] && echo "✅ Dockerfile.test exists" || echo "❌ Missing Dockerfile.test"
[ -f playwright.config.ts ] && echo "✅ playwright.config.ts exists" || echo "❌ Missing playwright.config.ts"

# Check for plan
ls .agents/plans/*.md 2>/dev/null || ls *PLAN.md 2>/dev/null
```

## Phase 1: Initialize Testing Session

### 1.1 Create Session Directory

```bash
# Create timestamp-based session directory
SESSION_TIME=$(date +%s)
mkdir -p .agents/ui-testing/session-$SESSION_TIME/{runners,monitors,regression,screenshots}

echo "Session ID: ui-test-$SESSION_TIME"
```

### 1.2 Verify Deployment Health

```bash
# Test deployment accessibility
echo "Testing deployment at $2..."

# Try health check endpoint
curl -f "$2/api/health" 2>/dev/null || curl -f "$2/health" 2>/dev/null || curl -f "$2" 2>/dev/null

if [ $? -ne 0 ]; then
  echo "❌ ERROR: Deployment not accessible at $2"
  echo "Please ensure the UI is running before starting tests."
  exit 1
fi

echo "✅ Deployment accessible"
```

### 1.3 Extract Features from Plan

Read the implementation plan and identify all features to test:

```bash
# Find the plan file
PLAN_FILE=$(find .agents/plans -name "*frontend*" -o -name "*implementation*" -o -name "*ui*" 2>/dev/null | head -1)

if [ -z "$PLAN_FILE" ]; then
  PLAN_FILE=$(find . -maxdepth 2 -name "*PLAN.md" 2>/dev/null | head -1)
fi

if [ -z "$PLAN_FILE" ]; then
  echo "❌ ERROR: No implementation plan found"
  echo "Expected: .agents/plans/*.md or *PLAN.md"
  exit 1
fi

echo "Using plan: $PLAN_FILE"
```

**Extract feature list:**

Look for sections like:
- "## Features"
- "### Phase N: Feature Name"
- "## Components"
- Feature bullet points

Create feature list (example):
```markdown
## Features to Test

1. **User Authentication**
   - Login/logout
   - Password reset
   - Session persistence

2. **Coach Chat Interface**
   - Load chat history
   - Send messages
   - Receive AI responses

3. **Payment Processing**
   - Display pricing plans
   - Process payments
   - Handle errors

4. **Profile Management**
   - View profile
   - Update settings
   - Upload avatar

5. **Admin Dashboard**
   - View analytics
   - Manage users
   - System settings

[Add all features from plan]
```

Save to: `.agents/ui-testing/session-$SESSION_TIME/test-plan.md`

### 1.4 Initialize Test State

Create state tracking file:

```bash
cat > .agents/ui-testing/test-state.json <<EOF
{
  "session_id": "ui-test-$SESSION_TIME",
  "started": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "last_update": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "project": "$1",
  "deployment": {
    "type": "$3",
    "url": "$2",
    "health_check_passed": true
  },
  "features": {},
  "bugs": {},
  "runners": {},
  "monitors": {},
  "stats": {
    "total_features": 0,
    "passed": 0,
    "failed": 0,
    "in_progress": 0,
    "blocked": 0
  }
}
EOF

echo "✅ Test state initialized"
```

## Phase 2: Spawn Test Suite Runners

### 2.1 Determine Initial Batch

**Rules:**
- Max 3 Test Suite Runners concurrent
- Start with features that have no dependencies
- Prioritize critical user flows first

**Decision logic:**

For each feature in test plan:
1. Check if has dependencies (e.g., "requires authentication")
2. If no dependencies → candidate for testing
3. If dependencies → mark as blocked until deps pass
4. Select up to 3 candidates for initial batch

### 2.2 Spawn Runners

For each feature to test:

```bash
# Use Task tool to spawn ui-test-suite-runner subagent
# Example (done via Claude Code Task tool in practice):

Task(
  subagent_type: "general-purpose",
  description: "Test User Authentication feature",
  prompt: "/command-invoke ui-test-suite-runner '$1' '$2' '$3' 'User Authentication' 'session-$SESSION_TIME'"
)
```

**Track in state:**
```json
{
  "runners": {
    "user-authentication": {
      "subagent_id": "agent-abc123",
      "status": "running",
      "started": "2026-01-11T14:30:00Z",
      "feature": "User Authentication"
    }
  },
  "features": {
    "user-authentication": {
      "status": "in_progress",
      "runner_id": "agent-abc123",
      "started": "2026-01-11T14:30:00Z"
    }
  }
}
```

**Update stats:**
```json
{
  "stats": {
    "total_features": 8,
    "in_progress": 3,
    "passed": 0,
    "failed": 0,
    "blocked": 5
  }
}
```

### 2.3 Initial Status Report

```markdown
## 🧪 UI Testing Started

**Session**: ui-test-$SESSION_TIME
**Project**: $1
**Deployment**: $2 ($3)
**Total Features**: 8

**Testing Now** (3/8):
- User Authentication
- Coach Chat Interface
- Payment Processing

**Queued** (5/8):
- Profile Management (blocked: needs auth)
- Settings Panel (blocked: needs auth)
- Admin Dashboard (blocked: needs auth + role)
- Notification System
- Analytics Dashboard

**Next Update**: 10 minutes
```

## Phase 3: Monitor and Coordinate

### 3.1 Polling Loop

**Every 2 minutes:**

1. Check TaskOutput for each runner
2. Detect completions, failures, errors
3. Update test-state.json
4. Spawn new runners if slots available
5. Spawn Fix-Retest Monitors for failures

### 3.2 Handle Runner Completion (Passed)

When runner reports feature PASSED:

```json
{
  "features": {
    "user-authentication": {
      "status": "passed",
      "tests_run": 5,
      "all_passed": true,
      "completed": "2026-01-11T14:45:00Z",
      "evidence": ".agents/ui-testing/session-X/runners/user-auth.log"
    }
  },
  "stats": {
    "passed": 1,
    "in_progress": 2
  }
}
```

**Actions:**
1. Mark feature as passed
2. Check if any blocked features can now start
3. If authentication passed → unblock features that depend on it
4. Spawn new runners for unblocked features

### 3.3 Handle Runner Completion (Failed)

When runner reports feature FAILED with bug:

```json
{
  "features": {
    "coach-chat": {
      "status": "failed",
      "tests_run": 3,
      "tests_passed": 1,
      "tests_failed": 2,
      "bug_issue": 142,
      "completed": "2026-01-11T14:50:00Z",
      "locked_for_fix": true
    }
  },
  "bugs": {
    "142": {
      "feature": "coach-chat",
      "title": "Chat history not loading",
      "created": "2026-01-11T14:50:00Z",
      "status": "pending_rca",
      "monitor_id": null
    }
  },
  "stats": {
    "failed": 1,
    "in_progress": 2
  }
}
```

**Actions:**
1. Mark feature as failed and locked
2. Spawn Fix-Retest Monitor for the bug
3. Continue testing other features

### 3.4 Spawn Fix-Retest Monitor

```bash
# Spawn monitor for bug fix
Task(
  subagent_type: "general-purpose",
  description: "Monitor fix for issue #142",
  prompt: "/command-invoke ui-fix-retest-monitor '$1' 142 'coach-chat' '$2' '$3' 'session-$SESSION_TIME'"
)
```

**Track in state:**
```json
{
  "monitors": {
    "142": {
      "subagent_id": "agent-def456",
      "status": "rca_requested",
      "started": "2026-01-11T14:52:00Z",
      "feature": "coach-chat",
      "issue": 142
    }
  },
  "bugs": {
    "142": {
      "monitor_id": "agent-def456",
      "status": "rca_in_progress"
    }
  }
}
```

### 3.5 Handle Monitor Completion (Fix Verified)

When monitor reports bug FIXED and retested:

```json
{
  "features": {
    "coach-chat": {
      "status": "passed",
      "tests_run": 3,
      "all_passed": true,
      "fixed_from_issue": 142,
      "locked_for_fix": false,
      "completed": "2026-01-11T16:25:00Z"
    }
  },
  "bugs": {
    "142": {
      "status": "fixed_verified",
      "pr": 145,
      "retest_passed": true,
      "completed": "2026-01-11T16:25:00Z"
    }
  },
  "stats": {
    "passed": 2,
    "failed": 0,
    "in_progress": 1
  }
}
```

**Actions:**
1. Mark feature as passed
2. Unlock feature (remove lock)
3. Update stats

### 3.6 Handle Monitor Completion (Fix Failed Retest)

When monitor reports bug fix failed retest:

```json
{
  "bugs": {
    "142": {
      "status": "fix_failed_retest",
      "pr": 145,
      "retest_passed": false,
      "new_issue": 146
    },
    "146": {
      "feature": "coach-chat",
      "title": "Chat history still not loading after fix",
      "created": "2026-01-11T16:30:00Z",
      "status": "pending_rca",
      "previous_attempt": 142
    }
  }
}
```

**Actions:**
1. Create new monitor for new issue #146
2. Keep feature locked
3. Continue monitoring other features

## Phase 4: Progress Reporting

### 4.1 Status Updates

**Every 10 minutes OR on significant events:**

```markdown
## 📊 UI Testing Progress Update

**Time**: HH:MM
**Session**: ui-test-$SESSION_TIME
**Duration**: Xh Ym

**Progress**: 5/8 features complete

**✅ Passed** (5):
- User Authentication
- Payment Processing
- Profile Management
- Settings Panel
- Notification System

**🔧 Being Fixed** (1):
- Coach Chat Interface (Issue #142, RCA complete, fix in progress)

**🧪 Testing Now** (1):
- Analytics Dashboard (runner active, 2min elapsed)

**⏳ Queued** (1):
- Admin Dashboard (blocked: needs analytics data)

**Bugs Found**: 2
- #142: Chat history not loading → Fixing...
- #143: Missing Stripe secret → Fixed ✅

**ETA**: ~45 minutes (1 feature testing + 1 bug fix)

**Next Update**: 10 minutes
```

### 4.2 Significant Event Alerts

**Feature Passed:**
```markdown
✅ **Feature Passed: User Authentication**

All 5 tests passed successfully:
- Login with valid credentials ✅
- Reject invalid credentials ✅
- Password reset flow ✅
- Session persistence ✅
- Logout ✅

Evidence: .agents/ui-testing/session-X/runners/user-auth.log
```

**Bug Found:**
```markdown
⚠️ **Bug Found: Coach Chat Interface**

Issue #142 created: Chat history not loading

**Evidence**:
- Screenshot: .agents/ui-testing/session-X/screenshots/chat-failure-1.png
- Video: Available in test artifacts
- Error: TimeoutError - .chat-history not visible after 30s

**Action**: Fix-Retest Monitor spawned, delegating to @scar for RCA
```

**Bug Fixed:**
```markdown
✅ **Bug Fixed: Chat History Loading**

Issue #142 resolved via PR #145

**Root Cause**: React state not updating on WebSocket message
**Fix**: Added useEffect dependency
**Retest**: All 3 tests now pass ✅

Feature "Coach Chat Interface" is now PASSING
```

## Phase 5: Completion and Regression

### 5.1 Check Completion Criteria

When all features show "passed":

```json
{
  "stats": {
    "total_features": 8,
    "passed": 8,
    "failed": 0,
    "in_progress": 0,
    "blocked": 0
  }
}
```

**Before declaring complete:**
1. Verify all bugs are fixed and closed
2. Verify no monitors are still active
3. Check for any regressions

### 5.2 Spawn Regression Test Runner

```bash
# Final validation - run ALL tests
Task(
  subagent_type: "general-purpose",
  description: "Regression test all features",
  prompt: "/command-invoke ui-regression-test '$1' '$2' '$3' 'session-$SESSION_TIME'"
)
```

**Wait for regression results:**

If regression PASSES:
```json
{
  "regression_test": {
    "status": "passed",
    "total_tests": 32,
    "passed": 32,
    "failed": 0,
    "completed": "2026-01-11T17:00:00Z"
  }
}
```

If regression FAILS:
```json
{
  "regression_test": {
    "status": "failed",
    "total_tests": 32,
    "passed": 30,
    "failed": 2,
    "new_bugs": [147, 148]
  }
}
```

**If new bugs found:**
- Spawn Fix-Retest Monitors for new bugs
- Continue monitoring until all pass
- Run regression again

### 5.3 Final Report

**When regression passes:**

```markdown
🎉 **UI Testing Complete for $1**

**Session**: ui-test-$SESSION_TIME
**Duration**: 2h 45min
**Deployment**: $2 ($3)

---

## Summary

**Features Tested**: 8
All features PASSING ✅

**Feature List**:
- User Authentication ✅
- Coach Chat Interface ✅ (fixed #142)
- Payment Processing ✅ (fixed #143)
- Profile Management ✅
- Settings Panel ✅
- Admin Dashboard ✅
- Notification System ✅
- Analytics Dashboard ✅

---

## Bugs Found and Fixed

**Total Bugs**: 3
**All Fixed**: ✅

1. **#142**: Chat history not loading
   - Root cause: React state not updating on WebSocket
   - Fix PR: #145
   - Retest: PASSED ✅

2. **#143**: Missing Stripe secret key
   - Root cause: Missing STRIPE_SECRET_KEY in .env
   - Resolution: Secret added, config updated
   - Retest: PASSED ✅

3. **#147**: Admin dashboard pagination (found in regression)
   - Root cause: Off-by-one error in pagination logic
   - Fix PR: #149
   - Retest: PASSED ✅

---

## Test Results

**Total Tests Run**: 35
**Passed**: 35
**Failed**: 0
**Success Rate**: 100%

**Regression Test**: ✅ CLEAN (no regressions detected)

---

## Evidence

**Test Logs**: `.agents/ui-testing/session-$SESSION_TIME/`
**Screenshots**: `.agents/ui-testing/session-$SESSION_TIME/screenshots/`
**Test State**: `.agents/ui-testing/test-state.json`

---

## Status

🚀 **UI is production-ready!**

All features tested, all bugs fixed, regression clean.
Safe to deploy or merge to production.

---

**Session ended**: $(date -u +%Y-%m-%dT%H:%M:%SZ)
```

### 5.4 Archive Session

```bash
# Move session to archives
mv .agents/ui-testing/session-$SESSION_TIME .agents/ui-testing/archives/

# Update test-state.json with final status
cat > .agents/ui-testing/test-state.json <<EOF
{
  "status": "completed",
  "last_session": "ui-test-$SESSION_TIME",
  "completed": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo "✅ Session archived"
```

## Emergency Procedures

### Deployment Becomes Inaccessible

If deployment URL stops responding during testing:

```bash
# Test health
curl -I $2

if [ $? -ne 0 ]; then
  echo "⚠️ CRITICAL: Deployment no longer accessible"
  echo "All testing paused. Please fix deployment and restart UI testing."

  # Update state
  # Mark all in_progress features as blocked
  # Pause all runners and monitors

  exit 1
fi
```

### Too Many Concurrent Failures

If more than 3 bugs found in first batch:

```markdown
⚠️ **High Failure Rate Detected**

3+ bugs found in initial testing batch.
This suggests potential systemic issues.

**Recommendation**:
1. Pause further testing
2. Review implementation quality with SCAR
3. Consider running code review first: /command-invoke code-review
4. Fix critical issues before continuing E2E tests

**Current Bugs**:
- #142: Chat history not loading
- #143: Missing Stripe secret
- #144: Payment form validation broken

Proceed with testing? (y/n)
```

### Context Limit Approaching

If supervisor context approaches limit:

```markdown
⚠️ **Context Limit Warning**

Supervisor context: ~140k/200k tokens

This is unusual - supervisor should stay under 20k tokens.
Possible causes:
- Too many updates in logs
- Subagent outputs being included

**Action**: Create handoff document and restart supervisor session.

Handoff doc: `.agents/ui-testing/session-$SESSION_TIME/handoff.md`

To resume:
```
/command-invoke ui-test-supervise-resume 'session-$SESSION_TIME'
```
```

## Communication Rules

### To User (Strategic Only)

**YES:**
- Progress updates every 10min
- Feature pass/fail notifications
- Bug found alerts
- Completion reports
- Blocker escalations

**NO:**
- Code snippets
- Test implementation details
- Technical error messages (link to logs instead)
- Detailed debugging info

### To Subagents (Technical Allowed)

**Test Suite Runners:**
- Feature name and requirements
- Plan file path
- Deployment URL
- Test criteria

**Fix-Retest Monitors:**
- Issue number
- Feature name
- Deployment URL for retesting
- Retest criteria

## File Structure

```
.agents/ui-testing/
├── test-state.json              # Current state (atomic updates)
├── test-state.lock              # Lock file for atomic writes
├── session-{timestamp}/         # Active session
│   ├── test-plan.md            # Features to test
│   ├── runners/                # Runner outputs
│   │   ├── user-auth.log
│   │   └── coach-chat.log
│   ├── monitors/               # Monitor logs
│   │   ├── issue-142.log
│   │   └── issue-143.log
│   ├── screenshots/            # Failure evidence
│   │   ├── chat-failure-1.png
│   │   └── payment-failure-1.png
│   └── regression/             # Final regression output
│       └── full-suite.log
└── archives/                    # Completed sessions
    └── session-{old-timestamp}/
```

## Success Criteria

- ✅ All features tested comprehensively
- ✅ All bugs found, fixed, and retested
- ✅ Regression test passes
- ✅ No features locked or blocked
- ✅ Evidence captured for all failures
- ✅ Minimal supervisor context usage (<20k tokens)

---

**Begin UI testing** - this command runs until all tests pass or you stop it.
