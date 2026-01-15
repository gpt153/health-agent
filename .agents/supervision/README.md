# Supervision State Directory

This directory stores autonomous supervision session data and state tracking.

## Purpose

When using the autonomous supervision system (`/supervise` or `/supervise-issue`), session state and progress tracking files are stored here.

## Structure

After running `/supervise`, the following structure will be created:

```
.agents/supervision/
├── project-state.json           # Current supervision state
├── session-{timestamp}/         # Active session directory
│   ├── meta-plan.md            # High-level project roadmap
│   ├── issues.json             # All issues snapshot
│   ├── progress-log.md         # Detailed activity log
│   └── handoff.md              # Context handoff doc (if needed)
└── archives/                    # Completed sessions
    └── session-{old-timestamp}/
```

## Files

### project-state.json
Current supervision state including:
- Active issues being monitored
- Completed issues
- Pending issues
- Monitor subagent tracking
- Context usage tracking

### session-{timestamp}/
Each supervision session gets a timestamped directory containing:
- **meta-plan.md**: High-level phases and dependencies
- **issues.json**: Snapshot of all GitHub issues at session start
- **progress-log.md**: Detailed timeline of all activities
- **handoff.md**: Created when context limit approaches, contains complete state for next supervisor instance

### archives/
Completed supervision sessions are moved here for reference.

## Usage

You typically won't interact with these files directly. The supervisor creates and manages them automatically.

**To resume supervision after handoff:**
1. Start new Claude Code session
2. Run `/prime-supervisor` (auto-loads handoff.md)
3. Run `/supervise` (resumes from saved state)

## More Information

See full documentation: `docs/autonomous-supervision.md`
