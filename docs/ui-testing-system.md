# Autonomous UI Testing System

**Version**: 1.0
**Last Updated**: 2026-01-11

Complete guide to SCAR's autonomous UI testing system for comprehensive E2E testing with automatic bug detection, fixing, and retesting.

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [Agent Types](#agent-types)
5. [Complete Workflow](#complete-workflow)
6. [File Structure](#file-structure)
7. [Conflict Prevention](#conflict-prevention)
8. [Troubleshooting](#troubleshooting)

---

## Overview

### What Is the UI Testing System?

An autonomous multi-agent system that:
- Tests all UI features comprehensively with Playwright
- Finds bugs and creates GitHub issues with evidence
- Delegates bug fixes to SCAR automatically
- Retests features after fixes
- Detects regressions
- Continues until all tests pass

### Key Features

✅ **Fully Autonomous** - Finds → Fixes → Retests → Repeats until clean
✅ **Minimal Supervisor Context** - ~10-15k tokens (all work delegated)
✅ **Parallel Execution** - 3 features tested concurrently, 5 bugs fixed in parallel
✅ **Evidence Capture** - Screenshots, videos, error logs for all failures
✅ **Regression Detection** - Final validation catches bugs introduced by fixes
✅ **Self-Healing** - If fix fails retest, creates new issue and tries again

### When to Use

**Perfect for:**
- After deploying UI to dev/production
- Before releasing new features
- Validating entire frontend after major changes
- Ensuring all implementation plan requirements met

**Not suitable for:**
- Unit testing (use Jest)
- API testing (use integration tests)
- Backend validation (use verify-scar-phase)

---

## Quick Start

### Prerequisites

1. **UI deployed and accessible**
   ```bash
   # Check deployment is running
   curl -I http://localhost:3002
   ```

2. **Playwright infrastructure exists**
   ```bash
   # Verify files exist
   ls Dockerfile.test playwright.config.ts tests/
   ```

3. **Implementation plan available**
   ```bash
   # Find plan file
   ls .agents/plans/*frontend*.md || ls *PLAN.md
   ```

4. **In project workspace** (not SCAR repo)
   ```bash
   cd /home/samuel/.archon/workspaces/consilio
   # NOT: /home/samuel/scar
   ```

### Run UI Testing

```bash
# Start Claude in project workspace
claude

# Run UI testing command
/command-invoke ui-test-supervise consilio http://localhost:3002 docker

# That's it! Supervisor handles everything autonomously
```

### What Happens Next

1. **Initialization** (~1 minute)
   - Supervisor creates session directory
   - Reads implementation plan
   - Identifies features to test
   - Initializes state tracking

2. **Parallel Testing** (~30-60 minutes)
   - Spawns 3 Test Suite Runners
   - Tests features concurrently
   - Reports pass/fail for each feature

3. **Bug Fixing** (~1-3 hours per bug)
   - Spawns Fix-Retest Monitor for each failure
   - Monitors delegate RCA to SCAR
   - Monitors track fix implementation
   - Monitors retest after fixes

4. **Regression Testing** (~10-20 minutes)
   - Runs complete test suite
   - Detects any regressions
   - If clean: Reports completion
   - If failures: Fixes and retests again

5. **Completion** (when all pass)
   - Final report with all results
   - Evidence archived
   - UI marked production-ready

---

## Architecture

### System Structure

```
UI Test Supervisor (1 instance, ~10-15k tokens)
    ├── Reads plan, orchestrates testing
    ├── Spawns Test Suite Runners (max 3 concurrent)
    ├── Spawns Fix-Retest Monitors (max 5 concurrent)
    └── Reports progress every 10min
         ↓
    ┌────────────────┴────────────────┐
    ↓                                 ↓
Test Suite Runners              Fix-Retest Monitors
(1-3 concurrent)                (1 per bug, max 5)
    ↓                                 ↓
Generate tests from plan        Delegate to SCAR
Run Playwright tests            Monitor RCA + fix
Report pass/fail                Verify + retest
Create issues on failure        Report success/failure
    ↓                                 ↓
Exit (free context)             Exit (free context)
```

### Context Usage Pattern

**Traditional approach**: Context grows linearly, hits 200k limit in ~6 hours

**This approach**: Supervisor context stays flat
- Supervisor: ~10-15k tokens (strategic only)
- Test Runner: ~20-30k tokens (exits after test)
- Fix Monitor: ~15-20k tokens (exits after retest)
- Regression Runner: ~25-35k tokens (exits after validation)

**Result**: Can test 50+ features without hitting context limits

---

## Agent Types

### 1. UI Test Supervisor

**Command**: `/command-invoke ui-test-supervise <project> <url> <type>`

**Role**: Lightweight orchestrator with minimal context usage

**Responsibilities**:
- Read implementation plan
- Identify features to test
- Spawn Test Suite Runners (max 3 concurrent)
- Track test state in JSON
- Receive results from runners
- Spawn Fix-Retest Monitors for failures
- Report progress every 10min
- Spawn Regression Runner when all pass
- Detect completion

**Context**: ~10-15k tokens (stays constant)

**Lifecycle**: Runs until all tests pass or stopped by user

---

### 2. Test Suite Runner

**Command**: `/command-invoke ui-test-suite-runner <project> <url> <type> <feature> <session>`

**Role**: Execute Playwright tests for a specific feature

**Responsibilities**:
- Read plan section for assigned feature
- Generate Playwright test code from requirements
- Run tests in isolated browser context
- Capture screenshots/videos on failure
- Create GitHub issue with evidence if failure
- Report results to supervisor
- Exit (free context)

**Context**: ~20-30k tokens (feature-specific)

**Lifecycle**: Spawn → Test → Report → Exit

**Example Generated Test**:
```typescript
test.describe('User Authentication', () => {
  test('should login with valid credentials', async ({ page }) => {
    await page.goto('http://localhost:3002/login');
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[type="password"]', 'password123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/.*dashboard/);
    await expect(page.locator('.user-name')).toBeVisible();
  });

  // More tests based on plan requirements...
});
```

---

### 3. Fix-Retest Monitor

**Command**: `/command-invoke ui-fix-retest-monitor <project> <issue> <feature> <url> <type> <session>`

**Role**: Monitor SCAR fixing a specific bug and retest

**Responsibilities**:
- Post @scar RCA instruction to GitHub
- Poll every 2min for RCA completion
- Post @scar fix instruction
- Monitor fix implementation
- When PR ready: Run verify-scar-phase
- Retest the specific feature
- If retest passes: Report success
- If retest fails: Create new issue and exit
- Exit (free context)

**Context**: ~15-20k tokens (issue-specific)

**Lifecycle**: Spawn → Delegate RCA → Monitor Fix → Verify → Retest → Exit

**State Locking**: Locks feature during fix to prevent conflicts

---

### 4. Regression Test Runner

**Command**: `/command-invoke ui-regression-test <project> <url> <type> <session>`

**Role**: Final validation - run complete test suite

**Responsibilities**:
- Verify all features passed initial tests
- Run complete Playwright test suite (all features)
- Detect regressions introduced by fixes
- Create GitHub issues for any regressions
- Report clean or failures to supervisor
- Exit (free context)

**Context**: ~25-35k tokens (comprehensive)

**Lifecycle**: Spawn → Test All → Report → Exit

**When Spawned**: After all Fix-Retest Monitors complete successfully

---

## Complete Workflow

### Scenario: Testing Consilio UI with 8 Features

#### Initial State

```
Deployment: http://localhost:3002 (docker)
Features to test: 8
- User Authentication
- Coach Chat Interface
- Payment Processing
- Profile Management
- Settings Panel
- Admin Dashboard
- Notification System
- Analytics Dashboard
```

#### Phase 1: Initialization (1 minute)

```
14:30 - Supervisor starts
14:30 - Reads .agents/plans/frontend-implementation.md
14:30 - Identifies 8 features
14:31 - Creates session-1736621400/
14:31 - Initializes test-state.json
```

#### Phase 2: Parallel Testing (30 minutes)

```
14:31 - Spawns 3 Test Suite Runners:
        Runner 1 → User Authentication
        Runner 2 → Coach Chat Interface
        Runner 3 → Payment Processing

14:40 - Runner 1 completes: ✅ User Auth PASSED (5/5 tests)
14:41 - Spawns Runner 4 → Profile Management

14:45 - Runner 2 completes: ❌ Coach Chat FAILED (1/3 tests)
        Creates issue #142 with evidence
14:45 - Spawns Fix Monitor 1 → Issue #142
14:46 - Spawns Runner 5 → Settings Panel

14:50 - Runner 3 completes: ❌ Payment FAILED (1/2 tests)
        Creates issue #143 with evidence
14:50 - Spawns Fix Monitor 2 → Issue #143
14:51 - Spawns Runner 6 → Admin Dashboard

[Continues until all 8 features tested...]

15:00 - All runners complete:
        - 6 features passed initially
        - 2 features failed (issues #142, #143)
```

#### Phase 3: Bug Fixing (2 hours)

```
Fix Monitor 1 (Issue #142 - Chat History):

14:45 - Posts: "@scar /command-invoke rca 142"
14:45 - SCAR acknowledges
15:10 - RCA complete: "React state not updating on WebSocket"
15:11 - Posts: "@scar /command-invoke fix-rca 142"
16:20 - SCAR posts: "PR created at #145"
16:21 - Runs verify-scar-phase: ✅ APPROVED
16:23 - Retests feature: npm run test:e2e:docker -- tests/coach-chat.spec.ts
16:25 - Retest: ✅ ALL PASS
16:26 - Reports: Issue #142 FIXED
16:26 - Unlocks "coach-chat" feature
16:26 - Exits

Fix Monitor 2 (Issue #143 - Payment):

14:50 - Posts: "@scar /command-invoke rca 143"
15:05 - RCA complete: "Missing STRIPE_SECRET_KEY"
15:06 - BLOCKS: Asks user for secret
15:10 - User provides secret
15:12 - Posts: "@scar /command-invoke fix-rca 143"
15:45 - PR created
15:47 - Verification: ✅ APPROVED
15:48 - Retest: ✅ PASS
15:49 - Reports: Issue #143 FIXED
15:49 - Exits
```

#### Phase 4: Regression Testing (15 minutes)

```
16:30 - All features passed, all bugs fixed
16:30 - Supervisor spawns Regression Runner
16:31 - Regression runs: npm run test:e2e:docker
16:45 - Results: 32/32 tests passed ✅
16:45 - No regressions detected
16:45 - Regression exits
```

#### Phase 5: Completion

```
16:46 - Supervisor generates final report:

🎉 UI Testing Complete for Consilio

Session: ui-test-1736621400
Duration: 2h 16min

Features Tested: 8 (all passing ✅)
Bugs Found: 2 (both fixed ✅)
Total Tests: 32
Success Rate: 100%
Regression: CLEAN ✅

🚀 UI is production-ready!

16:47 - Session archived
16:47 - Supervisor exits
```

---

## File Structure

```
.agents/ui-testing/
├── test-state.json              # Current state (atomic updates)
├── test-state.lock              # Lock file for atomic writes
│
├── session-1736621400/          # Active session
│   ├── test-plan.md            # Features to test (from plan)
│   │
│   ├── runners/                # Test Suite Runner outputs
│   │   ├── user-authentication/
│   │   │   ├── requirements.md
│   │   │   ├── test-spec.ts
│   │   │   ├── test-output.log
│   │   │   ├── results.md
│   │   │   └── screenshots/
│   │   │
│   │   ├── coach-chat/
│   │   │   ├── requirements.md
│   │   │   ├── test-spec.ts
│   │   │   ├── test-output.log
│   │   │   ├── results.md
│   │   │   └── screenshots/
│   │   │       ├── chat-failure-1.png
│   │   │       └── chat-failure-1.webm
│   │   │
│   │   └── [other features...]
│   │
│   ├── monitors/               # Fix-Retest Monitor logs
│   │   ├── issue-142/
│   │   │   ├── monitor.log
│   │   │   ├── verification.log
│   │   │   ├── retest-output.log
│   │   │   └── retest-failure/ (if applicable)
│   │   │
│   │   ├── issue-143/
│   │   │   └── [same structure]
│   │   │
│   │   └── [other issues...]
│   │
│   └── regression/             # Regression Test output
│       ├── regression.log
│       ├── test-output.log
│       ├── report.md
│       └── failures/           (if any)
│
└── archives/                    # Completed sessions
    └── session-1736600000/     (old sessions)
```

---

## Conflict Prevention

### 1. Feature Locking

When bug found in feature X:

```json
{
  "features": {
    "coach-chat": {
      "status": "locked_for_fix",
      "locked_by": "issue-142",
      "monitor_id": "agent-jkl012"
    }
  }
}
```

**Supervisor ensures**:
- No other Test Runner can test "coach-chat" until unlocked
- Only Fix-Retest Monitor #142 can modify it
- Lock released when fix verified and retested

### 2. Sequential Retest After Fix

```
1. SCAR fixes bug in worktree
2. Monitor runs verify-scar-phase (build check)
3. If build passes → Monitor runs Playwright test
4. ONLY AFTER test passes → unlock feature
5. Supervisor can then test it again if needed
```

Prevents "partially fixed" features causing cascading failures.

### 3. Isolated Browser Contexts

```typescript
// Each Test Suite Runner gets fresh browser
test.use({
  contextOptions: {
    viewport: { width: 1920, height: 1080 },
    // Fresh session, no shared state
  }
});
```

No cookies, localStorage, or session data shared between runners.

### 4. Atomic State Updates

```typescript
// Supervisor uses file locking for test-state.json
async function updateTestState(update) {
  const lockFile = '.agents/ui-testing/test-state.lock';

  // Wait for lock
  while (await fs.access(lockFile).catch(() => false)) {
    await sleep(100);
  }

  // Acquire lock
  await fs.writeFile(lockFile, process.pid);

  try {
    // Read → Modify → Write (atomic)
    const state = JSON.parse(await fs.readFile('test-state.json'));
    Object.assign(state, update);
    await fs.writeFile('test-state.json', JSON.stringify(state, null, 2));
  } finally {
    await fs.unlink(lockFile);
  }
}
```

### 5. Dependency Tracking

```json
{
  "features": {
    "payment-processing": {
      "depends_on": ["user-authentication"],
      "reason": "Must be logged in to access payments"
    },
    "analytics-dashboard": {
      "depends_on": ["coach-chat", "payment-processing"],
      "reason": "Dashboard shows data from these features"
    }
  }
}
```

Supervisor respects dependencies:
- Don't test "payment-processing" until "user-authentication" passes
- Don't test "analytics-dashboard" until its deps pass
- If dependency fails → mark dependent as "blocked"

---

## Troubleshooting

### Deployment Not Accessible

**Symptom**: Supervisor exits with "Deployment not accessible"

**Solution**:
```bash
# Verify deployment is running
docker ps | grep consilio
# or
curl -I http://localhost:3002

# Restart deployment if needed
docker-compose up -d
# or
npm run dev
```

### No Implementation Plan Found

**Symptom**: "ERROR: No implementation plan found"

**Solution**:
```bash
# Verify plan exists
ls .agents/plans/*.md
# or
ls *PLAN.md

# If missing, create plan first or specify location
```

### Playwright Tests Not Found

**Symptom**: "Test file not found" errors

**Solution**:
```bash
# Verify Playwright infrastructure
ls Dockerfile.test playwright.config.ts

# If missing, run setup script
/home/samuel/scar/scripts/setup-playwright-testing.sh .

# Then retry UI testing
```

### SCAR Not Responding

**Symptom**: Fix Monitor reports "SCAR still not responding after 60s"

**Solutions**:
1. Check SCAR status: `https://code.153.se/health`
2. Check GitHub webhook deliveries
3. Verify @scar mention in issue comments
4. Check SCAR container logs

### Too Many Failures

**Symptom**: 5+ bugs found in first testing batch

**Recommendation**:
```markdown
⚠️ High failure rate suggests systemic issues.

Consider:
1. Run code review first: /command-invoke code-review
2. Fix critical issues before E2E testing
3. Verify deployment is production-ready
```

### Regression Loop

**Symptom**: Regression test keeps finding new bugs

**Cause**: Fixes are introducing new bugs

**Solution**:
1. Review fix PRs carefully
2. Consider broader code review
3. Check if fixes are too isolated (not considering side effects)

### Monitor Timeout

**Symptom**: "RCA timeout after 30 attempts (60 minutes)"

**Cause**: SCAR analysis taking longer than expected

**Solution**:
- Check if SCAR encountered blockers
- Review issue comments for status
- Consider manual intervention if stuck

---

## Best Practices

### DO:

✅ Run from project workspace (not SCAR repo)
✅ Ensure deployment is stable before testing
✅ Have implementation plan ready
✅ Let system run autonomously
✅ Review final report before deploying

### DON'T:

❌ Run from `/home/samuel/scar` directory
❌ Start testing on broken deployment
❌ Interrupt monitors while they're working
❌ Merge PRs without reviewing
❌ Skip regression test

---

## Success Metrics

**Excellent Performance**:
- All features tested: ✅
- All bugs found and fixed: ✅
- Regression clean: ✅
- Total duration: 2-4 hours for 8 features
- Supervisor context: Under 20k tokens

**System Health Indicators**:
- Feature locking prevents conflicts
- Atomic state updates work correctly
- Evidence captured for all failures
- GitHub issues actionable and clear
- Regression detects new bugs

---

## Integration with SCAR Workflows

### Used By Supervisor

When user runs `/supervise` on a project with UI:

```markdown
1. Supervisor deploys UI (docker/native)
2. Supervisor runs: /command-invoke ui-test-supervise
3. UI testing system runs autonomously
4. Supervisor receives completion report
5. Supervisor proceeds with other tasks
```

### Standalone Usage

Can also be run independently:

```bash
# Deploy UI
docker-compose up -d

# Run UI testing
claude
/command-invoke ui-test-supervise myproject http://localhost:3000 docker

# Wait for completion
[System runs autonomously until all tests pass]
```

---

**Last Updated**: 2026-01-11
**Maintained By**: SCAR Development Team
**Version**: 1.0
