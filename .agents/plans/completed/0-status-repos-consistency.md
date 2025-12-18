# Fix: Status and Repos Command Inconsistency

## Problem

`/status` and `/repos` commands show inconsistent codebase state:

```
!status → "No codebase configured"
!repos  → "remote-coding-agent ← active"
```

## Root Cause

- `/status` checks `conversation.codebase_id` (strict - must be explicitly linked)
- `/repos` infers "active" from `cwd` matching a codebase's `default_cwd` (loose)

## Proposed Solution

**Option A: Make /status smarter (recommended)**
- If `codebase_id` is null but `cwd` matches a known codebase's `default_cwd`, show that codebase
- Auto-link the codebase to the conversation when detected

**Option B: Make /repos stricter**
- Only show "← active" if `codebase_id` is actually set on conversation
- Don't infer from `cwd`

## Files to Modify

- `src/handlers/command-handler.ts` - `/status` and `/repos` handlers

## Implementation Steps

1. Read current `/status` implementation (~line 100-130)
2. Read current `/repos` implementation (search for `case 'repos'`)
3. Decide on Option A or B
4. Implement consistent logic
5. Add test cases for the edge case

## Acceptance Criteria

- [ ] `/status` and `/repos` show consistent codebase state
- [ ] When `cwd` matches a codebase path, both commands agree on active state
- [ ] Tests cover the edge case of `cwd` set without `codebase_id`
