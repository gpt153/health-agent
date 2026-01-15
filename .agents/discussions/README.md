# Design Discussion Documents

This directory stores design discussion documents created by the autonomous supervisor when complex features require strategic decision-making.

## Purpose

When the supervisor detects that an issue is too complex or requires architectural decisions, it creates a prefilled discussion document here and notifies you to discuss it in a separate Claude Code session.

## Naming Convention

```
{YYYY-MM-DD}-{feature-name}.md                 # Before issue created
{YYYY-MM-DD}-{feature-name}-issue-{N}.md       # After issue created
```

**Examples:**
- `2024-01-08-streaming-api.md`
- `2024-01-08-streaming-api-issue-42.md` (renamed after issue #42 created)

## Workflow

1. **Supervisor detects complexity** during issue assessment
2. **Supervisor creates prefilled doc** with:
   - Problem statement
   - Possible approaches
   - Trade-offs
   - Questions to resolve
   - Project context
3. **Supervisor notifies you** to discuss in new session
4. **You open new terminal**: `cd <workspace> && claude`
5. **You say**: "Read .agents/discussions/{filename}"
6. **Discuss with Claude**, make decisions, update doc
7. **Update doc status** to "Complete" at top
8. **Supervisor reads results**, recommends next actions (create issues, revise plan, etc.)

## Document Structure

Each discussion doc contains:

```markdown
# {Feature Name} - Design Discussion

**Status**: In Progress / Complete
**Date**: YYYY-MM-DD
**Related Issue**: #{N} (if applicable)

## Problem Statement
{What needs to be solved}

## Context
{Where this fits in the project}

## Possible Approaches
### Option 1: {Name}
- Pros: ...
- Cons: ...
- Effort: ...

### Option 2: {Name}
...

## Questions to Resolve
1. {Question 1}
2. {Question 2}

## Decisions Made
{To be filled during discussion}

## Next Steps
{To be filled during discussion}
```

## When Discussions Happen

The supervisor creates discussion docs when:
- Architectural decisions needed (e.g., database schema design, API architecture)
- Multiple valid approaches exist with unclear best choice
- Feature requires trade-off analysis (performance vs simplicity, cost vs features)
- User preferences matter significantly
- Scope needs clarification before implementation

## After Discussion

Once discussion is complete:
1. Supervisor reads your decisions
2. Supervisor recommends concrete actions:
   - Create new issues based on decisions
   - Revise PRD or meta-plan
   - Update existing issues
   - Start implementation
3. You approve/reject recommendations
4. Supervisor executes approved actions

## More Information

See full documentation: `docs/autonomous-supervision.md` (section: Design Discussions)
