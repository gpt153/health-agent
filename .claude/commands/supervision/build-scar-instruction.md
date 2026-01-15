---
description: Build properly formatted SCAR instruction from issue context (helper subagent)
argument-hint: <issue-number> <task-type> [context]
---

# Build SCAR Instruction: Format Commands for GitHub

**NOTE**: Helper subagent, typically called by `/supervise-issue` or `/scar-monitor`. Rarely invoked directly.

## Arguments

- `$1`: Issue number (e.g., "42")
- `$2`: Task type (plan | execute | fix | rca)
- `$3`: Additional context (optional - feature description, plan path, etc.)

## Mission

Construct the correct SCAR command with proper formatting and context for posting to GitHub issues.

## Task Types

### Type: `plan`

**For new features needing planning:**

```markdown
@scar /command-invoke plan-feature-github "Issue #$1: {issue-title}

{issue-body}

Additional context:
$3

Please create a comprehensive implementation plan following the project's patterns and conventions."
```

**Why this format:**
- Includes issue number for tracking
- Full issue context for SCAR
- Any additional context from supervisor
- Clear instruction to follow project patterns

### Type: `execute`

**For implementing from an existing plan:**

```markdown
@scar /command-invoke execute-github .agents/plans/$3.md feature-$3

Issue: #$1

Follow the implementation plan and create a PR to staging when complete.
```

**Arguments needed in $3:**
- Plan filename (without path or extension)
- Becomes both plan path and branch name

**Example:**
- $3 = "streaming-api"
- Plan: `.agents/plans/streaming-api.md`
- Branch: `feature-streaming-api`

### Type: `fix`

**For bug fixes:**

```markdown
@scar /command-invoke fix-issue $1
```

**Simple and direct** - SCAR's fix-issue command handles everything:
- Fetches issue details
- Investigates root cause
- Implements fix
- Creates PR with tests

### Type: `rca`

**For root cause analysis (before fixing):**

```markdown
@scar /command-invoke rca

Issue #$1: {issue-title}

{issue-body}

Please perform a root cause analysis and document findings in .agents/rca/issue-$1.md

Do NOT implement fixes yet - analysis only.
```

**Use when:**
- Complex bugs needing investigation first
- Want to review cause before approving fix
- User wants to understand problem deeply

## Context Enhancement

### Adding Related Issues

If issue depends on or relates to others:

```markdown
@scar /command-invoke plan-feature-github "Issue #$1: {title}

{body}

Related work:
- Depends on: #7 (completed)
- Related to: #15 (in progress)
- Blocks: #20, #21

{Additional context}"
```

### Adding Design Decisions

If design discussion occurred:

```markdown
@scar /command-invoke execute-github .agents/plans/feature.md feature-branch

Issue: #$1

Design decisions from .agents/discussions/2024-01-08-feature-issue-$1.md:
- Use SSE instead of WebSockets
- Implement retry logic with exponential backoff
- JWT auth integration

Follow the plan and incorporate these decisions.
```

### Adding Constraints

If special constraints exist:

```markdown
@scar /command-invoke plan-feature-github "Issue #$1: {title}

{body}

Important constraints:
- Must work in serverless (Cloud Run)
- Database: PostgreSQL only
- Must maintain backward compatibility

{Additional context}"
```

## Output Format

**Return formatted instruction ready to post:**

```json
{
  "issue": 42,
  "instruction": "@scar /command-invoke plan-feature-github \"Issue #42: Add notifications\n\nImplement real-time notifications for coach messages.\n\nAdditional context:\nMust use SSE (not WebSockets due to Cloud Run)\n\nPlease create a comprehensive implementation plan following the project's patterns and conventions.\"",
  "command_type": "plan",
  "estimated_duration": "Planning: 30-60min, Implementation: 2-3h"
}
```

## Command Templates

### Template: New Feature (No Plan)

```
@scar /command-invoke plan-feature-github "Issue #{number}: {title}

{description}

{additional-context}

Please create a comprehensive implementation plan."
```

### Template: Execute from Plan

```
@scar /command-invoke execute-github .agents/plans/{plan-name}.md feature-{branch-name}

Issue: #{number}

{any-specific-notes}
```

### Template: Bug Fix

```
@scar /command-invoke fix-issue {number}
```

### Template: RCA Only

```
@scar /command-invoke rca

Issue #{number}: {title}

{description}

Document findings in .agents/rca/issue-{number}.md
Analysis only - do NOT implement fixes yet.
```

### Template: Enhancement

```
@scar /command-invoke plan-feature-github "Issue #{number}: {title} (Enhancement)

Current behavior:
{describe current}

Desired behavior:
{describe desired}

{additional-context}

Please plan the enhancement following existing patterns."
```

## Validation

**Before returning instruction:**

1. ✅ Verify `@scar` mention at start
2. ✅ Verify `/command-invoke` format correct
3. ✅ Verify command name valid (plan-feature-github, execute-github, fix-issue, rca)
4. ✅ Verify arguments match command requirements
5. ✅ Verify issue number included somewhere
6. ✅ Verify no syntax errors in markdown

## Error Handling

### Missing Required Context

If $2 is "execute" but no plan name in $3:
```json
{
  "error": "execute requires plan name in context",
  "example": "build-scar-instruction 42 execute streaming-api"
}
```

### Invalid Task Type

If $2 not in [plan, execute, fix, rca]:
```json
{
  "error": "Invalid task type: {$2}",
  "valid_types": ["plan", "execute", "fix", "rca"]
}
```

### Issue Not Found

If `gh issue view $1` fails:
```json
{
  "error": "Issue #{$1} not found",
  "suggestion": "Verify issue exists: gh issue list"
}
```

## Examples

### Example 1: Plan New Feature

**Input:**
- $1 = "42"
- $2 = "plan"
- $3 = "Real-time notifications for coach messages. Must work in Cloud Run (serverless)."

**Output:**
```
@scar /command-invoke plan-feature-github "Issue #42: Add real-time notifications

Real-time notifications for coach messages. Must work in Cloud Run (serverless).

Please create a comprehensive implementation plan following the project's patterns and conventions."
```

### Example 2: Execute from Plan

**Input:**
- $1 = "43"
- $2 = "execute"
- $3 = "streaming-api"

**Output:**
```
@scar /command-invoke execute-github .agents/plans/streaming-api.md feature-streaming-api

Issue: #43

Follow the implementation plan and create a PR to staging when complete.
```

### Example 3: Fix Bug

**Input:**
- $1 = "44"
- $2 = "fix"
- $3 = ""

**Output:**
```
@scar /command-invoke fix-issue 44
```

### Example 4: RCA First

**Input:**
- $1 = "45"
- $2 = "rca"
- $3 = "Intermittent database connection failures"

**Output:**
```
@scar /command-invoke rca

Issue #45: Database connection failures

Intermittent database connection failures

Please perform a root cause analysis and document findings in .agents/rca/issue-45.md

Do NOT implement fixes yet - analysis only.
```

## Success Criteria

- ✅ Generates syntactically correct @scar mentions
- ✅ Includes proper /command-invoke format
- ✅ Passes all validation checks
- ✅ Includes sufficient context for SCAR
- ✅ Returns quickly (<1s)

---

**This is a helper subagent** - formats instructions for posting to GitHub.
