---
description: Supervise single GitHub issue - monitor SCAR progress and verify completion
argument-hint: <issue-number>
---

# Supervise Issue: Single-Issue Autonomous Monitoring

## ⏰ TIMEZONE: Europe/Stockholm (CET/CEST)
**ALL time references, logging, and scheduling use Stockholm time, NOT UTC.**
- Current: 2026-01-13 (UTC+1 in winter, UTC+2 in summer)
- When mentioning times: Always specify "Stockholm time" or "CET/CEST"
- When logging: Convert UTC timestamps to Stockholm time for display

## Arguments

- `$1`: Issue number (e.g., "42")

## Mission

Monitor SCAR's work on a specific GitHub issue from instruction through completion and verification.

**Scope**: One issue only (for multi-issue, use `/supervise`)

## Prerequisites

**Required**:
- Issue must exist: `gh issue view $1`
- Must be in project workspace (not /scar directory)
- Must have run `/prime-supervisor` first (recommended)

## Phase 1: Assess Issue

### 1.1 Load Issue Details

```bash
gh issue view $1 --json number,title,body,labels,state,comments
```

**Extract**:
- Issue title and description
- Labels (bug, feature, enhancement, etc.)
- Current state (open/closed)
- Existing comments (check if SCAR already active)

### 1.2 Determine Approach

**Based on labels and content:**

| Issue Type | SCAR Command |
|-----------|--------------|
| Feature request | `/command-invoke plan-feature-github "{title}"` |
| Bug fix | `/command-invoke fix-issue $1` |
| Technical debt | `/command-invoke rca` then fix |
| Enhancement | `/command-invoke plan-feature-github "{description}"` |

**Assess complexity:**
- Simple: 1-2 hours estimated
- Medium: 2-6 hours estimated
- Complex: Needs design discussion first

**If complex**, trigger design discussion:
1. Create discussion doc (prefilled)
2. Notify user
3. Wait for discussion completion
4. Resume after decisions made

## Phase 2: Build SCAR Instruction

### 2.1 Determine Correct Command

Use `build-scar-instruction` subagent internally or construct:

**For new features:**
```
@scar /command-invoke plan-feature-github "Issue #$1: {title}

{body content}

Please create an implementation plan following the project's patterns."
```

**For bug fixes:**
```
@scar /command-invoke fix-issue $1
```

**For with existing plan:**
```
@scar /command-invoke execute-github .agents/plans/{plan-name}.md feature-{branch-name}
```

### 2.2 Add Context (if needed)

**Include relevant context:**
- Related issues: "Depends on #X, Related to #Y"
- Previous discussions: Link to discussion doc
- Design decisions: Reference to PRD or architecture docs

## Phase 3: Start SCAR

### 3.1 Post Instruction

```bash
# Post @scar mention with command
gh issue comment $1 --body "{SCAR instruction}"
```

**Log action:**
```bash
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) - Posted SCAR instruction" >> .agents/supervision/issue-$1-log.md
```

### 3.2 Verify SCAR Started (20s check)

**Wait and check:**
```bash
sleep 20

# Check for SCAR acknowledgment
gh issue view $1 --json comments --jq '.comments[-5:] | .[] | select(.body | contains("SCAR is on the case"))'
```

**If found:**
- SCAR acknowledged ✅
- Proceed to monitoring

**If NOT found:**
- Retry 1: Wait 40s, check again
- Retry 2: Wait 60s, check again
- Retry 3: Fail - notify user

**After 3 failures:**
```markdown
⚠️ **SCAR Unresponsive on Issue #$1**

Posted instruction but no acknowledgment after 3 attempts (2min total).

**Possible causes:**
- SCAR webhook not configured
- SCAR server down
- GitHub webhook delivery issues

**Recommended actions:**
1. Check SCAR status: Visit https://code.153.se/health
2. Check webhook deliveries in repo settings
3. Manually verify SCAR received instruction

**Manual fallback**: Add @scar comment directly in issue #$1
```

## Phase 4: Monitor Progress

### 4.1 Polling Loop

**Every 2 minutes:**
```bash
while true; do
  sleep 120

  # Fetch recent comments
  gh issue view $1 --json comments --jq '.comments[-10:]' > /tmp/issue-$1-comments.json

  # Check for completion signals, errors, activity
  # (Parse JSON and detect patterns)
done
```

### 4.2 Detect Activity Patterns

**Look for**:
- SCAR progress updates
- File creation mentions
- PR creation messages
- Error messages
- Completion indicators

**Completion signals:**
- "Implementation complete"
- "PR created at {url}"
- "All validation passed"
- Sees PR link pattern

**Error signals:**
- "Error:"
- "Failed:"
- "Cannot proceed"
- "Need clarification"

**Progress indicators:**
- "Working on {task}"
- "Created {file}"
- "Running tests"

### 4.3 Track State

Maintain state file:
```json
{
  "issue": 42,
  "status": "monitoring",
  "scar_started": true,
  "last_activity": "2024-01-08T10:45:00Z",
  "last_comment": "Creating streaming endpoint...",
  "progress_estimate": "60%",
  "retries": 0,
  "errors": []
}
```

### 4.4 Detect Completion

**When SCAR signals done:**
1. Stop polling loop
2. Extract key info (PR URL, branch name, worktree path)
3. Proceed to verification

**Inactivity timeout:**
- If no activity for 30min AND last message looks final
- Assume completion
- Proceed to verification

## Phase 5: Verify Implementation

### 5.1 Extract Implementation Details

From SCAR's comments, extract:
- **Feature branch**: e.g., `feature-streaming-api`
- **Worktree path**: e.g., `/home/samuel/.archon/worktrees/consilio/issue-42/`
- **Phase number**: Usually 1 or 2 (depends on complexity)
- **PR URL**: Link to created PR

### 5.2 Run Verification

```bash
# Use the verify-scar-phase subagent
# (Invoked via Claude Code Skill tool)
```

Invoke: `/verify-scar-phase consilio 42 1`

**Verification checks:**
- All claimed files exist in worktree
- Build succeeds (`npm run build` or equivalent)
- No mocks/placeholders in production code
- Tests pass
- Type checking passes

**Result**: APPROVED / REJECTED / NEEDS_FIXES

### 5.3 Handle Verification Result

**APPROVED ✅**:
```markdown
## ✅ Issue #$1 Complete

**Issue**: #{number} - {title}
**PR**: {pr-url}
**Verification**: APPROVED ✅

**What was built:**
{High-level summary from SCAR's report}

**Files changed:**
- {file}: {purpose}
- {file}: {purpose}

**Testing**: All tests passing ✅
**Build**: Passing ✅

**Ready for**: Review and merge

---

**Supervision complete** - Issue #{number} successfully implemented and verified.
```

**REJECTED ❌**:
```bash
# Post verification failures back to issue
gh issue comment $1 --body "## ⚠️ Verification Failed

SCAR's implementation has issues that need fixing:

{List of verification failures}

@scar please address these issues and re-run validation."
```

Wait for SCAR to fix and re-verify.

**NEEDS_FIXES 🔧**:
Similar to REJECTED but less severe. Post specific fixes needed.

## Phase 6: Report Completion

### 6.1 Final Report

**Post summary** (NO CODE):

```markdown
## 📊 Issue #$1 Supervision Complete

**Duration**: {X}h {Y}m
**Outcome**: {Completed / Blocked / Needs Discussion}

**Timeline**:
- Started: {timestamp}
- SCAR acknowledged: {timestamp}
- Implementation complete: {timestamp}
- Verification: {timestamp}
- Total time: {duration}

**Deliverables**:
- PR #{N}: {pr-url}
- Feature branch: `{branch-name}`
- Files changed: {count}
- Tests added: {count}

**Next Steps**:
{What should happen - review PR, merge, deploy, etc.}

---

**Status**: Supervision ended ✅
```

### 6.2 Update Supervision State

If part of project-level supervision:
```bash
# Update project-state.json
# Move issue from active to completed
# Trigger any dependent issues
```

## Edge Cases

### SCAR Needs Clarification

If SCAR asks questions:
```markdown
⚠️ **Issue #$1 Needs Your Input**

SCAR is asking:
"{SCAR's question}"

**Context**: {What SCAR was working on}

**Please respond** in issue #$1 with your answer, then supervision will continue.

Monitoring paused until you respond.
```

### Multiple Attempts Needed

If SCAR's first attempt fails:
- Don't panic
- Let SCAR retry (it will)
- Monitor retry attempts
- Only escalate after 3 failed attempts

### Depends on Another Issue

If issue depends on incomplete work:
```markdown
⚠️ **Issue #$1 Blocked**

**Blocker**: Issue #{N} must complete first

**Recommendation**:
- Wait for #{N} to finish
- Or remove dependency and proceed anyway

Should I wait or proceed?
```

## Communication Principles

**To User** (Strategic):
- Progress updates every 10min
- Completion summary
- Blocker alerts
- NO CODE

**To SCAR** (Technical):
- Detailed instructions in GitHub comments
- Specific file references
- Technical requirements
- Code examples allowed

## Success Criteria

- ✅ SCAR starts within 2min of instruction
- ✅ Progress monitored every 2min
- ✅ Completion detected accurately
- ✅ Verification runs automatically
- ✅ User receives clear status updates
- ✅ Blockers escalated immediately

---

**Monitor issue #{$1}** - runs until complete or blocked.
