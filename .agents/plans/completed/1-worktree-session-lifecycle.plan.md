# Plan: Worktree and Session Lifecycle Management

## Summary

Improve the UX around worktree and session management for GitHub issues and PRs by:
1. **Immediate fix**: Handle stale worktrees gracefully - validate cwd exists before resume, deactivate sessions when worktrees are cleaned up
2. **Issue-PR linking**: When a PR references an issue (via "Fixes #X"), share the issue's worktree instead of creating a new one
3. **Flexible context management**: Allow users to reset AI context (new session) while preserving code state (same worktree)

The core insight is separating three concepts:
- **Worktree**: Physical code state on disk (can be shared)
- **Conversation**: GitHub issue/PR thread (identity)
- **Session**: AI context window (can be reset independently)

## External Research

### GitHub API for Linked Issues
- [GitHub GraphQL API](https://docs.github.com/en/graphql) - `closingIssuesReferences` field on PR returns linked issues
- [Stack Overflow Discussion](https://stackoverflow.com/questions/60717142/getting-linked-issues-and-projects-associated-with-a-pull-request-form-github-ap) - No REST API support, must use GraphQL
- [GitHub CLI Discussions](https://github.com/cli/cli/discussions/7097) - Can query via `gh api graphql`

### Key Finding
```bash
# Get issues that will be closed when PR is merged
gh api graphql -F owner='{owner}' -F repo='{repo}' -F pr=NUMBER -f query='
query ($owner: String!, $repo: String!, $pr: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      closingIssuesReferences(first: 10) {
        nodes { number }
      }
    }
  }
}'
```

### Gotchas
- GraphQL requires authentication (token must have `repo` scope)
- `closingIssuesReferences` only returns issues linked via closing keywords ("fixes", "closes", etc.)
- Issues manually linked without keywords won't appear

## Patterns to Mirror

### Session Deactivation Pattern (existing)
```typescript
// FROM: src/db/sessions.ts:40-45
export async function deactivateSession(id: string): Promise<void> {
  await pool.query(
    'UPDATE remote_agent_sessions SET active = false, ended_at = NOW() WHERE id = $1',
    [id]
  );
}
```

### Worktree Cleanup Pattern (existing)
```typescript
// FROM: src/adapters/github.ts:396-431
private async cleanupWorktree(owner: string, repo: string, number: number): Promise<void> {
  const conversationId = this.buildConversationId(owner, repo, number);
  const conversation = await db.getConversationByPlatformId('github', conversationId);

  if (!conversation?.worktree_path) {
    console.log(`[GitHub] No worktree to cleanup for ${conversationId}`);
    return;
  }
  // ... removes worktree, updates conversation
  // NOTE: Does NOT deactivate session - this is the bug
}
```

### Conversation Update Pattern (existing)
```typescript
// FROM: src/db/conversations.ts:79-111
export async function updateConversation(
  id: string,
  updates: Partial<Pick<Conversation, 'codebase_id' | 'cwd' | 'worktree_path'>>
): Promise<void> {
  // ... builds dynamic UPDATE query
}
```

### fs.access for Path Validation (existing)
```typescript
// FROM: src/adapters/github.ts:293-294
await access(repoPath);
// throws if path doesn't exist
```

## Files to Change

| File | Action | Justification |
|------|--------|---------------|
| `src/adapters/github.ts` | UPDATE | Add session deactivation to cleanup, add linked issue detection for PR worktree sharing |
| `src/orchestrator/orchestrator.ts` | UPDATE | Add cwd validation before resume, handle stale worktree gracefully |
| `src/db/conversations.ts` | UPDATE | Add function to find conversations by worktree_path |
| `src/utils/github-graphql.ts` | CREATE | Utility for GitHub GraphQL queries (linked issues) |
| `src/utils/github-graphql.test.ts` | CREATE | Tests for GraphQL utility |
| `src/adapters/github.test.ts` | UPDATE | Add tests for session deactivation on cleanup, worktree sharing |
| `src/orchestrator/orchestrator.test.ts` | UPDATE | Add tests for stale cwd handling |
| `migrations/002_worktree_sharing.sql` | CREATE | Add index for worktree_path lookups |

## NOT Building

- ❌ Manual worktree management UI (out of scope for this fix)
- ❌ Cross-repository worktree sharing (too complex)
- ❌ Automatic worktree garbage collection (separate feature)
- ❌ Session forking/branching (Claude Code doesn't support this well)
- ❌ Multiple AI assistants per worktree (existing model is fine)

## Tasks

### Task 1: Add migration for worktree_path index

**Why**: Enable efficient lookup of conversations by worktree_path for sharing detection.

**Mirror**: `migrations/001_initial_schema.sql` index patterns

**Do**:
Create `migrations/002_worktree_sharing.sql`:
```sql
-- Add index for worktree_path lookups (for sharing worktrees between issue/PR)
CREATE INDEX IF NOT EXISTS idx_remote_agent_conversations_worktree
ON remote_agent_conversations(worktree_path)
WHERE worktree_path IS NOT NULL;
```

**Don't**:
- Add new columns (not needed)
- Modify existing data

**Verify**: `psql $DATABASE_URL < migrations/002_worktree_sharing.sql`

---

### Task 2: Add conversation lookup by worktree_path

**Why**: To find if another conversation already uses a worktree (for sharing).

**Mirror**: `src/db/conversations.ts:11-20` (`getConversationByPlatformId`)

**Do**:
Add to `src/db/conversations.ts`:
```typescript
/**
 * Find a conversation that uses a specific worktree path
 * Used to share worktrees between linked issues and PRs
 */
export async function getConversationByWorktreePath(
  worktreePath: string
): Promise<Conversation | null> {
  const result = await pool.query<Conversation>(
    'SELECT * FROM remote_agent_conversations WHERE worktree_path = $1 LIMIT 1',
    [worktreePath]
  );
  return result.rows[0] ?? null;
}
```

**Don't**:
- Return multiple results (we just need to know if ANY conversation uses it)

**Verify**: `npm run type-check`

---

### Task 3: Create GitHub GraphQL utility for linked issues

**Why**: To detect when a PR fixes an issue, so we can share the issue's worktree.

**Mirror**: `src/utils/github-auth.ts` for utility pattern

**Do**:
Create `src/utils/github-graphql.ts`:
```typescript
/**
 * GitHub GraphQL utilities
 * Used for queries not available in REST API
 */
import { execFile } from 'child_process';
import { promisify } from 'util';

const execFileAsync = promisify(execFile);

/**
 * Get issue numbers that will be closed when a PR is merged
 * Uses "closingIssuesReferences" from GraphQL API
 *
 * @returns Array of issue numbers linked via closing keywords (fixes, closes, etc.)
 */
export async function getLinkedIssueNumbers(
  owner: string,
  repo: string,
  prNumber: number
): Promise<number[]> {
  const query = `
    query ($owner: String!, $repo: String!, $pr: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $pr) {
          closingIssuesReferences(first: 10) {
            nodes { number }
          }
        }
      }
    }
  `;

  try {
    const { stdout } = await execFileAsync('gh', [
      'api', 'graphql',
      '-F', `owner=${owner}`,
      '-F', `repo=${repo}`,
      '-F', `pr=${String(prNumber)}`,
      '-f', `query=${query}`,
      '--jq', '.data.repository.pullRequest.closingIssuesReferences.nodes[].number'
    ], { timeout: 10000 });

    // Parse output: each line is an issue number
    return stdout.trim().split('\n')
      .filter(line => line.length > 0)
      .map(line => parseInt(line, 10))
      .filter(num => !isNaN(num));
  } catch (error) {
    // GraphQL query failed (no token, network issue, etc.)
    // Gracefully return empty - we'll create a new worktree
    console.warn('[GitHub GraphQL] Failed to fetch linked issues:', (error as Error).message);
    return [];
  }
}
```

**Don't**:
- Throw on failure (graceful degradation)
- Use Octokit's GraphQL (adds complexity, gh CLI is simpler)

**Verify**: `npm run type-check`

---

### Task 4: Add tests for GitHub GraphQL utility

**Why**: Ensure linked issue detection works correctly.

**Mirror**: `src/utils/github-auth.test.ts`

**Do**:
Create `src/utils/github-graphql.test.ts`:
```typescript
import { getLinkedIssueNumbers } from './github-graphql';
import { execFile } from 'child_process';

jest.mock('child_process', () => ({
  execFile: jest.fn(),
}));

const mockExecFile = execFile as unknown as jest.Mock;

describe('github-graphql', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('getLinkedIssueNumbers', () => {
    test('returns issue numbers from GraphQL response', async () => {
      mockExecFile.mockImplementation(
        (_cmd: string, _args: string[], callback: (err: Error | null, result: { stdout: string }) => void) => {
          callback(null, { stdout: '42\n45\n' });
        }
      );

      const result = await getLinkedIssueNumbers('owner', 'repo', 123);

      expect(result).toEqual([42, 45]);
      expect(mockExecFile).toHaveBeenCalledWith(
        'gh',
        expect.arrayContaining(['api', 'graphql']),
        expect.any(Object)
      );
    });

    test('returns empty array when no linked issues', async () => {
      mockExecFile.mockImplementation(
        (_cmd: string, _args: string[], callback: (err: Error | null, result: { stdout: string }) => void) => {
          callback(null, { stdout: '' });
        }
      );

      const result = await getLinkedIssueNumbers('owner', 'repo', 123);

      expect(result).toEqual([]);
    });

    test('returns empty array on error (graceful degradation)', async () => {
      mockExecFile.mockImplementation(
        (_cmd: string, _args: string[], callback: (err: Error | null) => void) => {
          callback(new Error('gh: command not found'));
        }
      );

      const result = await getLinkedIssueNumbers('owner', 'repo', 123);

      expect(result).toEqual([]);
    });

    test('filters out invalid numbers', async () => {
      mockExecFile.mockImplementation(
        (_cmd: string, _args: string[], callback: (err: Error | null, result: { stdout: string }) => void) => {
          callback(null, { stdout: '42\nnot-a-number\n45\n' });
        }
      );

      const result = await getLinkedIssueNumbers('owner', 'repo', 123);

      expect(result).toEqual([42, 45]);
    });
  });
});
```

**Verify**: `npm test -- src/utils/github-graphql.test.ts`

---

### Task 5: Deactivate session on worktree cleanup

**Why**: Prevent "process exited with code 1" when resuming with deleted worktree.

**Mirror**: Pattern exists in orchestrator plan→execute transition

**Do**:
Update `src/adapters/github.ts` `cleanupWorktree` method.

Add import at top:
```typescript
import * as sessionDb from '../db/sessions';
```

Update the method (insert after line 403, before getting codebase):
```typescript
private async cleanupWorktree(owner: string, repo: string, number: number): Promise<void> {
  const conversationId = this.buildConversationId(owner, repo, number);
  const conversation = await db.getConversationByPlatformId('github', conversationId);

  if (!conversation?.worktree_path) {
    console.log(`[GitHub] No worktree to cleanup for ${conversationId}`);
    return;
  }

  // Deactivate any active session for this conversation
  // This prevents resume attempts with a stale cwd
  const activeSession = await sessionDb.getActiveSession(conversation.id);
  if (activeSession) {
    await sessionDb.deactivateSession(activeSession.id);
    console.log(`[GitHub] Deactivated session ${activeSession.id} for worktree cleanup`);
  }

  const { codebase } = await this.getOrCreateCodebaseForRepo(owner, repo);
  // ... rest of method unchanged
```

**Don't**:
- Change the worktree removal logic
- Add new error handling (existing is fine)

**Verify**: `npm run type-check && npm test -- src/adapters/github.test.ts`

---

### Task 6: Add cwd validation in orchestrator

**Why**: Defense in depth - handle cases where worktree is deleted without proper cleanup.

**Mirror**: `src/adapters/github.ts:293-294` uses `access()` for path validation

**Do**:
Update `src/orchestrator/orchestrator.ts`.

Add import:
```typescript
import { access } from 'fs/promises';
```

After line 200 (where cwd is computed), add validation:
```typescript
const cwd = conversation.worktree_path ?? conversation.cwd ?? codebase?.default_cwd ?? '/workspace';

// Validate cwd exists - handle stale worktree paths gracefully
try {
  await access(cwd);
} catch {
  console.warn(`[Orchestrator] Working directory ${cwd} does not exist`);

  // Deactivate stale session to force fresh start
  if (session) {
    await sessionDb.deactivateSession(session.id);
    session = null;
    console.log('[Orchestrator] Deactivated session with stale worktree');
  }

  // Clear stale worktree reference from conversation
  if (conversation.worktree_path) {
    await db.updateConversation(conversation.id, {
      worktree_path: null,
      cwd: codebase?.default_cwd ?? '/workspace'
    });
    console.log('[Orchestrator] Cleared stale worktree path from conversation');
  }

  // Use default cwd for this request
  // Note: Reassignment needed - declare cwd with let instead of const
}
```

Also change line 200 from `const cwd` to `let cwd` and add reassignment at end of catch block:
```typescript
  cwd = codebase?.default_cwd ?? '/workspace';
}
```

**Don't**:
- Throw errors (graceful recovery)
- Recreate the worktree (let user/system handle that explicitly)

**Verify**: `npm run type-check`

---

### Task 7: Add worktree sharing for linked PRs

**Why**: When a PR fixes an issue, use the issue's existing worktree instead of creating new one.

**Mirror**: Existing `isNewConversation` branching in `handleWebhook`

**Do**:
Update `src/adapters/github.ts` webhook handling.

Add imports:
```typescript
import { getLinkedIssueNumbers } from '../utils/github-graphql';
import * as conversationDb from '../db/conversations';
```

In `handleWebhook`, before the worktree creation block (around line 544), add logic to check for linked issues:
```typescript
// 10. Create worktree for this issue/PR (if new conversation)
let worktreePath: string | null = null;
let prHeadBranch: string | undefined;
const isPR = eventType === 'pull_request' || !!pullRequest || !!issue?.pull_request;

if (isNewConversation) {
  // For PRs: Check if this PR is linked to an existing issue with a worktree
  if (isPR) {
    const linkedIssues = await getLinkedIssueNumbers(owner, repo, number);

    for (const issueNum of linkedIssues) {
      // Check if the linked issue has a worktree we can reuse
      const issueConvId = this.buildConversationId(owner, repo, issueNum);
      const issueConv = await db.getConversationByPlatformId('github', issueConvId);

      if (issueConv?.worktree_path) {
        // Reuse the issue's worktree
        worktreePath = issueConv.worktree_path;
        console.log(`[GitHub] PR #${String(number)} linked to issue #${String(issueNum)}, sharing worktree: ${worktreePath}`);

        // Update this conversation to use the shared worktree
        await db.updateConversation(existingConv.id, {
          codebase_id: codebase.id,
          cwd: worktreePath,
          worktree_path: worktreePath,
        });
        break; // Use first found worktree
      }
    }
  }

  // If no shared worktree found, create new one
  if (!worktreePath) {
    try {
      // ... existing worktree creation code
```

Wrap the existing worktree creation in the `if (!worktreePath)` block and close it properly.

**Don't**:
- Change the worktree creation logic itself
- Block on GraphQL errors (graceful degradation already handled)

**Verify**: `npm run type-check && npm test -- src/adapters/github.test.ts`

---

### Task 8: Add `/reset-context` command (optional enhancement)

**Why**: Allow users to start fresh AI context while keeping the worktree.

**Mirror**: Existing `/reset` command pattern

**Do**:
Update `src/handlers/command-handler.ts`.

Add to deterministic commands list (around line 80 in orchestrator):
```typescript
const deterministicCommands = [
  // ... existing commands
  'reset-context',
];
```

Add handler in command-handler.ts:
```typescript
case 'reset-context': {
  // Reset AI session while keeping worktree
  const activeSession = await sessionDb.getActiveSession(conversation.id);
  if (activeSession) {
    await sessionDb.deactivateSession(activeSession.id);
    return {
      success: true,
      message: 'AI context reset. Your next message will start a fresh conversation while keeping your current working directory.',
      modified: false,
    };
  }
  return {
    success: true,
    message: 'No active session to reset.',
    modified: false,
  };
}
```

**Don't**:
- Clear the worktree_path
- Remove any code

**Verify**: `npm run type-check && npm test -- src/handlers/command-handler.test.ts`

---

### Task 9: Update tests for session deactivation on cleanup

**Why**: Ensure the bug fix is covered by tests.

**Mirror**: Existing `github.test.ts` patterns

**Do**:
Update `src/adapters/github.test.ts`, add test in the `worktree cleanup` describe block:

```typescript
test('should deactivate session when cleaning up worktree', async () => {
  const mockConversation = {
    id: 'conv-123',
    worktree_path: '/workspace/worktrees/issue-42',
  };
  const mockSession = {
    id: 'session-456',
    active: true,
  };

  // Mock getting conversation
  (db.getConversationByPlatformId as jest.Mock).mockResolvedValueOnce(mockConversation);
  // Mock getting active session
  (sessionDb.getActiveSession as jest.Mock).mockResolvedValueOnce(mockSession);
  // Mock deactivating session
  (sessionDb.deactivateSession as jest.Mock).mockResolvedValueOnce(undefined);
  // ... other mocks for codebase, removeWorktree, updateConversation

  // Trigger cleanup (by simulating close event)
  // ... test implementation depends on how adapter is tested

  expect(sessionDb.deactivateSession).toHaveBeenCalledWith('session-456');
});
```

Add mock for sessionDb at top of test file if not present.

**Verify**: `npm test -- src/adapters/github.test.ts`

---

### Task 10: Update tests for orchestrator cwd validation

**Why**: Ensure stale worktree handling is covered.

**Mirror**: Existing `orchestrator.test.ts` patterns

**Do**:
Update `src/orchestrator/orchestrator.test.ts`, add test:

```typescript
describe('stale worktree handling', () => {
  test('should deactivate session and clear worktree when cwd does not exist', async () => {
    // Setup: conversation with worktree_path that doesn't exist
    mockGetOrCreateConversation.mockResolvedValue({
      ...mockConversation,
      worktree_path: '/nonexistent/worktree/path',
      cwd: '/nonexistent/worktree/path',
    });

    // Mock fs.access to throw (path doesn't exist)
    mockAccess.mockRejectedValueOnce(new Error('ENOENT'));

    // Mock active session
    mockGetActiveSession.mockResolvedValue({
      id: 'stale-session',
      assistant_session_id: 'claude-session-xyz',
      active: true,
    });

    // ... rest of test setup

    await handleMessage(platform, 'chat-456', 'Hello');

    // Verify session was deactivated
    expect(mockDeactivateSession).toHaveBeenCalledWith('stale-session');

    // Verify worktree_path was cleared
    expect(mockUpdateConversation).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ worktree_path: null })
    );
  });
});
```

Add mock for `access` from `fs/promises` at top of test file.

**Verify**: `npm test -- src/orchestrator/orchestrator.test.ts`

---

## Validation Strategy

### Automated Checks
- [ ] `npm run type-check` - Types valid
- [ ] `npm run lint` - No lint errors
- [ ] `npm test` - All tests pass
- [ ] `npm run build` - Build succeeds

### New Tests to Write

| Test File | Test Case | What It Validates |
|-----------|-----------|-------------------|
| `github-graphql.test.ts` | Returns linked issue numbers | GraphQL parsing works |
| `github-graphql.test.ts` | Graceful degradation on error | Doesn't break if gh fails |
| `github.test.ts` | Session deactivated on cleanup | Bug fix works |
| `github.test.ts` | Worktree shared for linked PR | Sharing works |
| `orchestrator.test.ts` | Stale cwd handled gracefully | Defense in depth works |
| `command-handler.test.ts` | `/reset-context` deactivates session | Command works |

### Manual/E2E Validation

```bash
# 1. Start the application
npm run dev

# 2. Test stale worktree handling
# - Create a conversation with a worktree
# - Manually delete the worktree directory
# - Send a message to the conversation
# - Should NOT error, should create new session

# 3. Test PR-issue worktree sharing
# - Create issue #X, trigger worktree creation
# - Create PR that "Fixes #X"
# - Trigger PR event
# - Should log "sharing worktree" instead of creating new one

# 4. Test session deactivation on cleanup
# - Have active conversation with worktree
# - Close the issue/PR
# - Verify session is deactivated in database
# - Reopen and send message
# - Should create NEW session, not resume
```

### Edge Cases to Test
- [ ] PR linked to multiple issues (should use first found worktree)
- [ ] Issue with no worktree yet when PR created (should create new)
- [ ] GraphQL timeout/failure (should gracefully create new worktree)
- [ ] `/reset-context` with no active session (should be no-op)
- [ ] Cleanup when session already inactive (should be no-op)
- [ ] cwd validation when conversation has no worktree_path (should skip validation)

### Regression Check
- [ ] Normal issue workflow still works (create worktree, work, close, cleanup)
- [ ] Normal PR workflow still works
- [ ] `/reset` command still works
- [ ] Other platforms (Telegram, Discord) unaffected

## Risks

1. **GraphQL rate limits**: GitHub GraphQL has separate rate limits. Mitigated by only querying on new PR conversations.

2. **gh CLI not installed**: Some deployments may not have `gh`. Mitigated by graceful degradation (empty array returned).

3. **Shared worktree conflicts**: Two users working on issue and PR simultaneously could have conflicts. Mitigated by git's natural conflict handling.

4. **Migration not run**: Index won't exist. Mitigated by `IF NOT EXISTS` clause.

## Future Considerations (NOT in this plan)

- Explicit worktree management commands (`/worktree list`, `/worktree remove`)
- Automatic worktree garbage collection for stale worktrees
- Cross-conversation context sharing (share AI context, not just worktree)
- Worktree naming based on PR branch name instead of number
