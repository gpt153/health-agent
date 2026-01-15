---
description: Supervise entire project - monitor all issues, manage dependencies, track progress
argument-hint: none
---

# Supervise: Project-Level Autonomous Supervision

## ⏰ TIMEZONE: Europe/Stockholm (CET/CEST)
**ALL time references, logging, and scheduling use Stockholm time, NOT UTC.**
- Current: 2026-01-13 (UTC+1 in winter, UTC+2 in summer)
- When mentioning times: Always specify "Stockholm time" or "CET/CEST"
- When logging: Convert UTC timestamps to Stockholm time for display

## Mission

Maintain continuous oversight of the entire project, managing issue decomposition, SCAR delegation, dependency tracking, and progress reporting.

**Duration**: Runs indefinitely until stopped or context limit reached.

**Scope**: All open issues, not just one.

## Prerequisites

Must have run `/prime-supervisor` first to load context.

## Phase 1: Initialize Supervision

### 1.1 Create Session Directory

```bash
# Create timestamp-based session directory
SESSION_TIME=$(date +%s)
mkdir -p .agents/supervision/session-$SESSION_TIME

# Initialize project state
cat > .agents/supervision/project-state.json <<EOF
{
  "status": "active",
  "started": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "last_update": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "session_id": "session-$SESSION_TIME",
  "phase": "initializing",
  "active_issues": [],
  "completed_issues": [],
  "pending_issues": [],
  "monitors": {},
  "context_usage": 0
}
EOF
```

### 1.2 Load All Open Issues

```bash
gh issue list --state open --json number,title,labels,state --limit 50 > .agents/supervision/session-$SESSION_TIME/issues.json
```

### 1.3 Build Meta-Plan

Analyze all issues and create high-level roadmap:

**Group by labels/milestones:**
- Foundation issues (dependencies, setup, architecture)
- Core feature issues (main functionality)
- Polish issues (UI/UX improvements, edge cases)
- Testing issues (validation, E2E tests)

**Identify dependencies:**
- Which issues must complete before others can start?
- Which issues can run in parallel?
- What's the critical path?

**Create phase structure:**
```markdown
## Project Phases

**Phase 1: Foundation** (Issues #1-#5)
- Status: {Completed/In Progress/Pending}
- Blockers: {None/List}

**Phase 2: Core Features** (Issues #6-#15)
- Status: {Completed/In Progress/Pending}
- Dependencies: Phase 1 complete
- Blockers: {None/List}

**Phase 3: Integration** (Issues #16-#20)
- Status: {Completed/In Progress/Pending}
- Dependencies: Phase 2 complete
- Blockers: {None/List}
```

Save to: `.agents/supervision/session-$SESSION_TIME/meta-plan.md`

### 1.4 Port Conflict Prevention Protocol

**CRITICAL**: Before instructing SCAR to start ANY service (native or Docker), prevent port conflicts:

**Check Ports First:**
```bash
# Always check which ports are in use before starting services
netstat -tlnp | grep LISTEN 2>/dev/null || ss -tlnp | grep LISTEN
# or
lsof -i -P -n | grep LISTEN
```

**Common Default Ports to Check:**
- 3000 (React, Next.js, Express)
- 3001 (Alt web server)
- 4000 (GraphQL, Alt API)
- 5000 (Flask, Alt server)
- 5432 (PostgreSQL)
- 6379 (Redis)
- 8000 (Django, FastAPI)
- 8080 (Alt HTTP)
- 9000 (Alt service)

**Instruction Pattern for SCAR:**
```markdown
Before implementing, check for port conflicts:

1. Run: `netstat -tlnp | grep LISTEN` or `lsof -i -P -n | grep LISTEN`
2. Document which ports are in use
3. If service defaults to port 3000 and it's taken → choose 3002, 3003, etc.
4. Update configuration files (package.json, docker-compose.yml, .env) with chosen port
5. Document the chosen port in implementation summary

**Do NOT waste time debugging port conflicts after starting services.**
```

**Why This Matters:**
- Port 3000 conflicts waste 5-15 minutes of debugging time
- SCAR often discovers conflict AFTER implementation
- Proactive checking takes 30 seconds, saves significant time

**Track Port Allocations:**
Maintain `.agents/supervision/port-allocations.json`:
```json
{
  "allocations": {
    "3000": "main-app",
    "3001": "scar-remote-agent",
    "3002": "health-agent-web"
  },
  "last_updated": "2026-01-09T08:30:00Z"
}
```

## Phase 2: Spawn Issue Monitors

### 2.1 Determine Which Issues to Start

**Rules**:
- Max 5 concurrent issues (VM limit)
- Respect dependencies (don't start blocked issues)
- Prioritize by labels (high priority first)
- Balance parallel work when possible

**Decision logic**:
```markdown
For each open issue:
1. Check dependencies - are prerequisites complete?
2. Check priority - high priority issues first
3. Check concurrency - under 5 active monitors?
4. If all YES → spawn monitor
5. If NO → add to pending queue
```

### 2.2 Spawn Monitors

For each issue to monitor:

**Spawn using Skill tool:**

```markdown
/supervision:scar-monitor {issue_number} "{scar_command}"
```

Example invocation via Skill tool:
- skill: "supervision:scar-monitor"
- args: "42 \"/command-invoke plan-feature-github 'Add notifications'\""

Spawn with:
- Issue number
- SCAR command to execute
- Monitor frequency (2min polling)

Track in state:
```json
{
  "monitors": {
    "42": {
      "subagent_id": "agent-abc123",
      "status": "waiting_start",
      "started": "2024-01-08T10:00:00Z",
      "command": "/command-invoke plan-feature-github 'Add notifications'",
      "retries": 0
    }
  }
}
```

## Phase 3: Monitor and Coordinate

### 3.1 Poll Monitor States

**Every 2 minutes**:
- Check each subagent's progress
- Update project-state.json
- Detect completions, blockers, errors

### 3.2 Handle Completions and Merge Decisions

When monitor reports issue VERIFIED_APPROVED:

#### Step 1: Receive Verification Report

Monitor has already run `/verify-scar-phase` and reports:
```json
{
  "issue": 42,
  "status": "verified_approved",
  "pr_number": 52,
  "pr_url": "https://github.com/user/repo/pull/52",
  "verification": "approved",
  "files_changed": 5,
  "tests_added": 12
}
```

**Extract PR details from monitor report:**
```bash
ISSUE_NUM=42  # From report
PR_NUM=52     # From report
PR_URL="https://github.com/user/repo/pull/52"
```

#### Step 2: Assess Merge Safety (Strategic Decision)

**You have full project context:**
- All active issues and their PRs
- Dependency graph from meta-plan
- Main branch state
- Other pending merges

**Evaluate merge safety:**

**1. Dependency Check** - Does any in-progress issue depend on current main?
```bash
# Check if any active issues would break
for active_issue in "${!monitors[@]}"; do
  if issue_depends_on_current_main "$active_issue"; then
    DEPENDENCY_BLOCKER=true
    BLOCKER_REASON="Issue #$active_issue building on current main"
  fi
done
```

**2. Conflict Check** - Are other approved PRs waiting to merge?
```bash
# List all PRs with verified_approved status
APPROVED_PRS=$(jq -r '.monitors[] | select(.status=="verified_approved") | .pr_number' project-state.json)

if [ $(echo "$APPROVED_PRS" | wc -l) -gt 1 ]; then
  MULTIPLE_APPROVED=true
  # Determine merge order based on dependencies
fi
```

**3. Stability Check** - Is main branch currently stable?
```bash
# Check recent CI status on main
MAIN_STATUS=$(gh run list --branch main --limit 1 --json conclusion -q '.[0].conclusion')

if [ "$MAIN_STATUS" != "success" ]; then
  MAIN_UNSTABLE=true
  BLOCKER_REASON="Main branch CI failing"
fi
```

**4. UI Deployment Check** - Is this a UI feature requiring tests?
```bash
# Check issue labels
LABELS=$(gh issue view $ISSUE_NUM --json labels -q '.labels[].name')

if echo "$LABELS" | grep -qE "frontend|ui|web|dashboard"; then
  UI_FEATURE=true
  # Check if UI testing complete (see 3.3)
  UI_TEST_STATUS=$(jq -r ".ui_deployments.issue_$ISSUE_NUM.status" project-state.json)

  if [ "$UI_TEST_STATUS" != "passed" ]; then
    HOLD_FOR_UI_TESTS=true
    BLOCKER_REASON="UI testing not complete"
  fi
fi
```

**Decision Matrix:**

```bash
# Determine action based on assessment
if [ "$HOLD_FOR_UI_TESTS" = true ]; then
  DECISION="HOLD"
  REASON="Waiting for UI testing to complete"
elif [ "$MAIN_UNSTABLE" = true ]; then
  DECISION="HOLD"
  REASON="Main branch unstable - waiting for fix"
elif [ "$DEPENDENCY_BLOCKER" = true ]; then
  DECISION="HOLD"
  REASON="$BLOCKER_REASON"
elif [ "$MULTIPLE_APPROVED" = true ]; then
  # Check merge order - backend before frontend, etc.
  if should_merge_first "$PR_NUM" "$APPROVED_PRS"; then
    DECISION="MERGE_NOW"
  else
    DECISION="HOLD"
    REASON="Other PR should merge first (dependency order)"
  fi
else
  # No blockers - safe to merge
  DECISION="MERGE_NOW"
fi
```

#### Step 3: Execute Decision

**If MERGE_NOW:**

```bash
echo "🔍 Merge Assessment for PR #$PR_NUM (Issue #$ISSUE_NUM):"
echo "  ✅ Verification: APPROVED"
echo "  ✅ Dependencies: None blocking"
echo "  ✅ Main status: Stable"
echo "  ✅ Other PRs: None waiting"
echo "  ✅ Decision: MERGE NOW"
echo ""

# Get current PR merge status
MERGE_STATUS=$(gh pr view $PR_NUM --json mergeStateStatus -q '.mergeStateStatus')

# Handle PR state
if [ "$MERGE_STATUS" = "BEHIND" ]; then
  echo "PR behind main - rebasing first..."
  gh pr checkout $PR_NUM
  git fetch origin main
  git rebase origin/main

  if [ $? -ne 0 ]; then
    echo "❌ Auto-rebase failed - manual conflict resolution needed"
    git rebase --abort

    # Post to issue
    gh issue comment $ISSUE_NUM --body "## ⚠️ Merge Conflict

PR #$PR_NUM has conflicts with main branch.

**Action needed**: Manual conflict resolution required.

Holding merge until conflicts resolved."

    DECISION="HOLD"
    REASON="Merge conflicts - needs manual resolution"
  else
    git push --force-with-lease
    echo "✅ Rebased successfully"
  fi
fi

# Execute merge (if still MERGE_NOW after rebase check)
if [ "$DECISION" = "MERGE_NOW" ]; then
  gh pr merge $PR_NUM --squash --delete-branch --admin

  if [ $? -eq 0 ]; then
    echo "✅ PR #$PR_NUM merged to main"

    # Update project state
    jq ".monitors.\"$ISSUE_NUM\".status = \"merged\" |
        .monitors.\"$ISSUE_NUM\".merged_at = \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"" \
        project-state.json > tmp.json && mv tmp.json project-state.json

    # Proceed to Step 4
  else
    echo "❌ Merge failed - investigating..."
    gh pr view $PR_NUM --json mergeStateStatus,statusCheckRollup

    DECISION="HOLD"
    REASON="Merge command failed - needs investigation"
  fi
fi
```

**If HOLD:**

```bash
echo "⏸️  Holding PR #$PR_NUM - merge later"
echo "Reason: $REASON"
echo ""

# Update state to pending_merge
jq ".monitors.\"$ISSUE_NUM\".status = \"pending_merge\" |
    .monitors.\"$ISSUE_NUM\".hold_reason = \"$REASON\"" \
    project-state.json > tmp.json && mv tmp.json project-state.json

# Will be re-evaluated in next polling cycle
echo "Will reassess in next cycle (2min)"
```

**If REJECT:**

```bash
echo "❌ Not merging PR #$PR_NUM"
echo "Reason: $REASON"
echo ""

# Post to issue
gh issue comment $ISSUE_NUM --body "## ❌ Merge Rejected

**Reason**: $REASON

**Action needed**: Address the issues before merge can proceed."

# Update state
jq ".monitors.\"$ISSUE_NUM\".status = \"merge_rejected\" |
    .monitors.\"$ISSUE_NUM\".reject_reason = \"$REASON\"" \
    project-state.json > tmp.json && mv tmp.json project-state.json
```

#### Step 4: Post-Merge Actions (After Successful Merge)

**1. Update main branch locally:**
```bash
git checkout main
git pull origin main

echo "📥 Updated main to latest (includes PR #$PR_NUM)"
```

**2. Notify all active monitors about main update:**
```bash
# All active work needs to know main changed
for issue in "${!monitors[@]}"; do
  status=$(jq -r ".monitors.\"$issue\".status" project-state.json)

  if [[ "$status" == "monitoring" || "$status" == "pending_merge" ]]; then
    echo "🔔 Notifying monitor for issue #$issue: main updated"
    # Monitors may need to rebase their PRs
  fi
done
```

**3. Check for UI deployment** (if applicable):
- If UI feature, proceed to 3.3 (Automatic UI Testing)
- Wait for UI tests to pass before marking truly complete

**4. Move to completed_issues:**
```bash
# Only mark complete if NOT a UI feature awaiting tests
if [ "$UI_FEATURE" != true ] || [ "$UI_TEST_STATUS" = "passed" ]; then
  # Update project state
  jq ".completed_issues += [$ISSUE_NUM] |
      del(.monitors.\"$ISSUE_NUM\")" \
      project-state.json > tmp.json && mv tmp.json project-state.json

  echo "✅ Issue #$ISSUE_NUM moved to completed"
fi
```

**5. Check if dependent issues can now start:**
```bash
# Check pending queue for issues that were blocked by this one
PENDING=$(jq -r '.pending_issues[]' project-state.json)

for pending_issue in $PENDING; do
  # Check if dependencies now satisfied
  DEPENDS_ON=$(gh issue view $pending_issue --json body -q '.body' | grep -oP 'Depends on #\K[0-9]+')

  if [ "$DEPENDS_ON" = "$ISSUE_NUM" ]; then
    echo "🚀 Issue #$pending_issue now unblocked - spawning monitor"

    # Spawn monitor for newly unblocked issue
    # Invoke Skill: /supervision:scar-monitor
    # Example: /supervision:scar-monitor $pending_issue "/command-invoke plan-feature-github 'Feature title'"

    # Remove from pending, add to active
    jq ".pending_issues -= [$pending_issue]" project-state.json > tmp.json && mv tmp.json project-state.json
  fi
done
```

**6. Spawn new monitors for unblocked issues** (see step 5 above)

**7. Update meta-plan:**
```bash
# Update meta-plan with progress
cat >> .agents/supervision/session-$SESSION_TIME/meta-plan.md <<EOF

## Updated $(date -u +%Y-%m-%dT%H:%M:%S)

**Issue #$ISSUE_NUM**: ✅ Merged to main
- PR #$PR_NUM merged
- Dependencies unblocked: $(echo $UNBLOCKED_ISSUES | tr '\n' ', ')

**Next**: $(echo $NEXT_ISSUES | head -1)

EOF
```

#### Step 5: Report to User (Strategic Summary)

```markdown
## 📊 Supervision Update

**Issue #$ISSUE_NUM**: {title} - ✅ **MERGED**
  - Verification: APPROVED ✅
  - Merge assessment: Safe (no conflicts, stable main)
  - PR #$PR_NUM merged to main at $(date -u +%H:%M:%S)
  - Files changed: {count}
  - Tests added: {count}

**Impact**:
  - Main branch updated
  - {N} issues now unblocked: {list}

**Next**: Starting Issue #{next} (now unblocked)

**Active**: {N} issues in progress
**Pending**: {N} issues waiting on dependencies
```

### 3.3 Automatic UI Testing After Deployment

**CRITICAL**: After deploying ANY UI (frontend, web app, dashboard), automatically trigger comprehensive testing.

**Detection Triggers:**
You deployed a UI if ANY of these apply:
- Started/deployed a React, Next.js, Vue, Angular, or similar frontend app
- Deployed a web interface to localhost, Docker, or production
- Started a service on ports 3000-3999, 8000-8999 (common web ports)
- SCAR completed a frontend implementation issue
- Issue labels include: `frontend`, `ui`, `web`, `dashboard`
- Issue mentions: "deploy", "start server", "npm run dev", "docker-compose up"

**Automatic Testing Protocol:**

When UI deployment detected:

```bash
# 1. Extract deployment details from your actions or SCAR's responses
PROJECT_NAME=$(basename $PWD)  # e.g., "consilio"
URL="<the URL you deployed to>"  # e.g., "http://localhost:3002"
DEPLOY_TYPE="<docker|native|production>"  # How it was deployed

# 2. Immediately spawn UI testing supervisor
# DO NOT wait, DO NOT ask user - this is automatic
```

**Spawn UI Test Supervisor:**
```markdown
Spawning UI testing for deployed frontend:
- Project: {project}
- URL: {url}
- Type: {deployment_type}

Starting: /command-invoke ui-test-supervise {project} {url} {type}

UI testing will run automatically. I'll report when complete.
```

**Wait for UI Testing Completion:**
- UI Test Supervisor runs autonomously
- Polls `.agents/ui-testing/test-state.json` for completion
- Check every 5 minutes
- Max wait: 3 hours (typical UI testing takes 2-3h)

**Integration with Issue Tracking:**

```json
{
  "monitors": {
    "42": {
      "status": "ui_testing",
      "ui_testing": {
        "started": "2026-01-11T18:00:00Z",
        "url": "http://localhost:3002",
        "type": "docker",
        "session": "session-1736621400",
        "status": "in_progress"
      }
    }
  }
}
```

**UI Testing Completion Handling:**

```bash
# Poll UI testing state
UI_TEST_STATE=".agents/ui-testing/test-state.json"

# When complete, read results
if [ -f "$UI_TEST_STATE" ]; then
  REGRESSION_STATUS=$(jq -r '.regression_test.status' $UI_TEST_STATE)

  if [ "$REGRESSION_STATUS" = "passed" ]; then
    echo "✅ UI Testing Complete - All tests passed"
    # NOW mark issue as complete
    # Move to completed_issues
    # Continue supervision
  else
    echo "❌ UI Testing Found Bugs"
    BUGS=$(jq -r '.regression_test.new_bugs[]' $UI_TEST_STATE)
    echo "New issues created: $BUGS"
    # Add bugs to supervision tracking
    # Fix-Retest Monitors will handle them automatically
    # Wait for all bugs to be fixed and retested
    # Then mark original issue complete
  fi
fi
```

**Do NOT Mark UI Issues Complete Until:**
- ✅ Implementation verified
- ✅ UI deployed successfully
- ✅ **UI testing complete with all tests passing**
- ✅ No regressions detected

**Common UI Deployment Scenarios:**

1. **Docker Deployment:**
   ```
   URL: http://localhost:3002
   Type: docker
   Detection: docker-compose up, container started
   ```

2. **Native Deployment:**
   ```
   URL: http://localhost:3000
   Type: native
   Detection: npm run dev, npm start
   ```

3. **Production Deployment:**
   ```
   URL: https://app.example.com
   Type: production
   Detection: Cloud Run deploy, vercel deploy, netlify deploy
   ```

**State Updates:**

Update project-state.json to track UI testing:
```json
{
  "phase": "ui_testing",
  "ui_deployments": {
    "issue_42": {
      "url": "http://localhost:3002",
      "type": "docker",
      "testing_session": "session-1736621400",
      "status": "testing",
      "started": "2026-01-11T18:00:00Z"
    }
  }
}
```

**Progress Reporting:**

Include UI testing in status updates:
```markdown
**Active Work**:
- Issue #42: Frontend Implementation - ✅ Complete
  - UI Testing: In Progress (15/20 features tested)
  - Found 2 bugs (being fixed automatically)
```

**Why This Matters:**

Without automatic UI testing:
- ❌ Manual testing required (hours of user time)
- ❌ Bugs discovered later in production
- ❌ No systematic feature coverage
- ❌ Regressions go undetected

With automatic UI testing:
- ✅ Every feature tested systematically
- ✅ Bugs caught and fixed before completion
- ✅ Regression detection automatic
- ✅ Zero user intervention needed
- ✅ Confidence in UI quality

### 3.4 Handle Blockers

When issue gets blocked:
- Pause monitoring
- Assess blocker type:
  - Needs design discussion? → Create discussion doc, notify user
  - Dependency not ready? → Wait for prerequisite
  - SCAR error? → Retry with different approach
  - Unclear requirement? → Ask user for clarification

### 3.5 Manage Dependencies

**Dependency graph tracking**:
```markdown
Issue #8: Coach agent (BLOCKED - needs #7)
  ↑ depends on
Issue #7: Streaming API (IN PROGRESS - 70% done)
  ↑ depends on
Issue #6: Database schema (COMPLETED ✅)
```

**When dependency completes**:
- Automatically start dependent issues
- Update all affected monitors
- Recalculate critical path

## Phase 4: Progress Reporting

### 4.1 Status Updates

**Every 10 minutes OR on significant events**:

Post update (NO CODE):
```markdown
## 📊 Supervision Update

**Time**: {HH:MM}
**Phase**: {current phase}
**Progress**: {X/Y issues complete}

**Active Work**:
- Issue #{N}: {title} - {status} ({progress}%)
- Issue #{N}: {title} - {status} ({progress}%)

**Completed Since Last Update**:
- Issue #{N}: {title} ✅

**Next Up**:
- Issue #{N}: {title} (starts after #{N})

**Blockers**: {None / List}

**ETA**: {estimated time to phase completion}
```

### 4.2 Session Summary

**Every hour OR on phase completion**:

```markdown
## 📈 Session Summary

**Session Duration**: {hours}h {minutes}m
**Issues Completed**: {count}
**Issues Active**: {count}
**Issues Pending**: {count}

**Velocity**: {issues per hour}

**Phase Progress**:
{Bar chart or percentage}

**Critical Path Status**:
{On track / Delayed by {X} / Ahead by {X}}

**Recommendations**:
{Strategic adjustments if needed}
```

## Phase 5: Context Management

### 5.1 Monitor Token Usage

Track approximate context usage:
- Every response ~2-5k tokens
- At ~150k tokens → prepare handoff

### 5.2 Context Handoff Protocol

**When approaching limit**:

1. **Save complete state**:
```bash
# Write comprehensive handoff document
cat > .agents/supervision/session-$SESSION_TIME/handoff.md <<EOF
# Supervision Handoff

**Session**: session-$SESSION_TIME
**Handoff Time**: $(date -u +%Y-%m-%dT%H:%M:%SZ)
**Reason**: Context limit approaching

## Current State
{Full state dump}

## Active Monitors
{All active subagents with their states}

## Pending Actions
{What needs to happen next}

## Instructions for Next Instance
1. Run /prime-supervisor
2. Read this handoff doc
3. Resume monitoring from current state
4. Continue supervision
EOF
```

2. **Notify user**:
```markdown
⚠️ **Context Limit Approaching**

This supervision session has been running for {duration}.
Context usage: ~{percentage}%

**Handoff prepared**: `.agents/supervision/session-{ID}/handoff.md`

**To resume supervision**:
1. Start new Claude session
2. Run `/prime-supervisor`
3. Run `/supervise` (will auto-resume from handoff)

**Current work will continue** - all SCAR monitors remain active in GitHub.
This is just the supervisor instance transitioning.

Handing off in 5 minutes...
```

3. **Clean exit**:
- Update project-state.json with handoff info
- Close gracefully
- Next instance will resume seamlessly

## Phase 6: Completion

**When all issues complete**:

```markdown
🎉 **Project Supervision Complete**

**Session**: {session-id}
**Duration**: {total time}
**Issues Completed**: {count}

**Summary**:
{List all completed issues with PRs}

**Metrics**:
- Average time per issue: {X}h
- Total PRs created: {count}
- Total lines changed: {count} (from git)
- Build passing: ✅
- All tests: ✅

**Final State**: All open issues resolved

**Next Steps**:
{Suggest next phase of development or maintenance mode}

---

**Supervision session ended** ✅
```

## Emergency Procedures

### SCAR Unresponsive
If SCAR doesn't respond after 3 retries:
1. Report to user immediately
2. Don't block other issues
3. Suggest manual intervention
4. Continue monitoring other issues

### Critical Blocker
If blocker affects multiple issues:
1. Pause affected monitors
2. Escalate to user immediately
3. Recommend design discussion
4. Don't make major decisions autonomously

### Build Breakage
If PR merges break main:
1. Alert immediately
2. Identify culprit PR
3. Recommend revert or hotfix
4. Pause new work until fixed

## Communication Rules (CRITICAL)

**To User** (Strategic only):
- High-level status updates
- Completion reports
- Blocker alerts
- Recommendations

**NO CODE to user** - see communication principles in `/prime-supervisor`

**To SCAR** (Technical allowed):
- Detailed instructions in GitHub comments
- Code examples if needed for clarity
- Technical specifications

## File Structure

```
.agents/supervision/
├── project-state.json          # Current state (updated continuously)
├── session-{timestamp}/        # Session-specific data
│   ├── issues.json             # All issues snapshot
│   ├── meta-plan.md            # High-level roadmap
│   ├── progress-log.md         # Detailed log
│   └── handoff.md              # Handoff doc (if needed)
└── archives/                   # Completed sessions
    └── session-{old-timestamp}/
```

## Success Criteria

- ✅ All issues monitored continuously
- ✅ Dependencies respected and managed
- ✅ User receives regular updates
- ✅ Blockers identified and escalated quickly
- ✅ Context handoff works seamlessly
- ✅ No SCAR work duplicated or missed

---

**Begin supervision** - this command runs until all issues complete or you stop it.
