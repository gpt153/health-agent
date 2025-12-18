# Plan: GitHub Worktree Isolation

## Summary

Automatically create a worktree for each GitHub issue/PR when `@remote-agent` is mentioned. This provides isolation between conversations (issue-42 doesn't conflict with pr-15), prevents stale worktree paths from polluting the database, and enables clean PR workflows. When an issue is closed or PR is merged, the worktree is automatically cleaned up.

## The Problem

1. **Stale codebase paths**: When an issue is created from within a Claude Code worktree session, the codebase gets registered with the worktree path (e.g., `/worktrees/feature-x/workspace/repo`) instead of the canonical path (`/workspace/repo`). This causes future conversations to use a path that may not exist.

2. **No isolation between issues/PRs**: Currently all GitHub conversations work on the same clone. Work on issue #42 can conflict with work on PR #15.

3. **Manual cleanup burden**: When worktrees become orphaned, users must manually fix database entries.

## The Solution

1. **Canonical codebase registration**: Always register codebases with the canonical `$WORKSPACE_PATH/{repo}` path, never worktree paths.

2. **Auto-worktree on @mention**: When `@remote-agent` is mentioned in a new issue/PR, automatically create a git worktree branch (e.g., `issue-42` or `pr-15`) before the agent starts working.

3. **Worktree awareness**: The agent is informed it's working in a worktree, can reference the branch name, and guides users on creating PRs.

4. **Auto-cleanup on close/merge**: When GitHub sends issue.closed or PR.merged webhook events, automatically remove the worktree.

## External Research

### Git Worktree Commands
```bash
# Create worktree with new branch
git worktree add ../worktrees/issue-42 -b issue-42

# List worktrees
git worktree list

# Remove worktree
git worktree remove ../worktrees/issue-42

# Check if path is a worktree (exit 0 if true)
git rev-parse --is-inside-work-tree
# Check for .git file (worktrees have .git file, not directory)
test -f .git  # true for worktree, false for main repo
```

### Gotchas
- Worktrees share the same `.git` objects, so they're lightweight
- Can't have two worktrees on the same branch
- Worktree removal fails if there are uncommitted changes (git's natural guardrail)
- Need to handle case where issue-42 branch already exists from a previous conversation

## Patterns to Mirror

### Codebase lookup pattern (src/adapters/github.ts:323-350)
```typescript
private async getOrCreateCodebaseForRepo(
  owner: string,
  repo: string
): Promise<{ codebase: { id: string; name: string }; repoPath: string; isNew: boolean }> {
  const repoUrlNoGit = `https://github.com/${owner}/${repo}`;
  const repoUrlWithGit = `${repoUrlNoGit}.git`;

  let existing = await codebaseDb.findCodebaseByRepoUrl(repoUrlNoGit);
  existing ??= await codebaseDb.findCodebaseByRepoUrl(repoUrlWithGit);

  if (existing) {
    console.log(`[GitHub] Using existing codebase: ${existing.name} at ${existing.default_cwd}`);
    return { codebase: existing, repoPath: existing.default_cwd, isNew: false };
  }

  const repoPath = join(resolve(process.env.WORKSPACE_PATH ?? '/workspace'), repo);
  const codebase = await codebaseDb.createCodebase({
    name: repo,
    repository_url: repoUrlNoGit,
    default_cwd: repoPath,
  });

  console.log(`[GitHub] Created new codebase: ${codebase.name} at ${repoPath}`);
  return { codebase, repoPath, isNew: true };
}
```

### Existing worktree support (migrations/003_add_worktree.sql)
```sql
-- Already exists on conversations table
ALTER TABLE remote_agent_conversations
ADD COLUMN worktree_path VARCHAR(500);
```

We'll use this existing `worktree_path` column instead of a separate worktrees table - simpler for GitHub's needs.

### Webhook event parsing (src/adapters/github.ts:165-217)
```typescript
private parseEvent(event: WebhookEvent): {
  owner: string;
  repo: string;
  number: number;
  comment: string;
  eventType: 'issue' | 'issue_comment' | 'pull_request';
  // ...
} | null
```

## Files to Change

| File | Action | Justification |
|------|--------|---------------|
| `src/adapters/github.ts` | UPDATE | Add worktree creation on first @mention, handle close/merge cleanup |
| `src/db/codebases.ts` | UPDATE | Add `isWorktreePath()` helper to detect worktree paths |
| `src/utils/git.ts` | CREATE | Git utilities for worktree operations (create, remove, detect) |

## NOT Building

- Port allocation for worktrees (GitHub doesn't need ports, that's for local dev)
- Thread creation (GitHub issues ARE the threads)
- Cross-platform worktree abstraction (this is GitHub-specific)
- Manual `/worktree` commands for GitHub (auto-creation handles it)

## Tasks

### Task 1: Create git utilities

**Why**: Centralize git worktree operations for reuse and testability.

**File**: `src/utils/git.ts` (NEW)

**Do**:
```typescript
import { promisify } from 'util';
import { exec } from 'child_process';
import { access, readFile } from 'fs/promises';
import { join } from 'path';

const execAsync = promisify(exec);

/**
 * Check if a path is inside a git worktree (vs main repo)
 * Worktrees have a .git FILE, main repos have a .git DIRECTORY
 */
export async function isWorktreePath(path: string): Promise<boolean> {
  try {
    const gitPath = join(path, '.git');
    const content = await readFile(gitPath, 'utf-8');
    // Worktree .git file contains "gitdir: /path/to/main/.git/worktrees/..."
    return content.startsWith('gitdir:');
  } catch {
    return false;
  }
}

/**
 * Create a git worktree for an issue or PR
 * Returns the worktree path
 */
export async function createWorktreeForIssue(
  repoPath: string,
  issueNumber: number,
  isPR: boolean
): Promise<string> {
  const branchName = isPR ? `pr-${issueNumber}` : `issue-${issueNumber}`;
  const worktreePath = join(repoPath, '..', 'worktrees', branchName);

  try {
    // Try to create with new branch
    await execAsync(
      `git -C "${repoPath}" worktree add "${worktreePath}" -b "${branchName}"`,
      { timeout: 30000 }
    );
  } catch (error) {
    const err = error as Error & { stderr?: string };
    // Branch already exists - use existing branch
    if (err.stderr?.includes('already exists')) {
      await execAsync(
        `git -C "${repoPath}" worktree add "${worktreePath}" "${branchName}"`,
        { timeout: 30000 }
      );
    } else {
      throw error;
    }
  }

  return worktreePath;
}

/**
 * Remove a git worktree
 * Throws if uncommitted changes exist (git's natural guardrail)
 */
export async function removeWorktree(repoPath: string, worktreePath: string): Promise<void> {
  await execAsync(
    `git -C "${repoPath}" worktree remove "${worktreePath}"`,
    { timeout: 30000 }
  );
}

/**
 * Get canonical repo path from a worktree path
 * If already canonical, returns the same path
 */
export async function getCanonicalRepoPath(path: string): Promise<string> {
  if (await isWorktreePath(path)) {
    // Read .git file to find main repo
    const gitPath = join(path, '.git');
    const content = await readFile(gitPath, 'utf-8');
    // gitdir: /path/to/repo/.git/worktrees/branch-name
    const match = /gitdir: (.+)\/\.git\/worktrees\//.exec(content);
    if (match) {
      return match[1];
    }
  }
  return path;
}
```

**Verify**: `npm run type-check`

---

### Task 2: Update codebase registration to reject worktree paths

**Why**: Prevent stale worktree paths from being registered as codebases.

**File**: `src/adapters/github.ts`

**Mirror**: Existing `getOrCreateCodebaseForRepo` method at line 323

**Do**:

Update the method to:
1. If an existing codebase is found with a worktree path, update it to the canonical path
2. Always create new codebases with canonical path

```typescript
// Add import at top
import { isWorktreePath, getCanonicalRepoPath } from '../utils/git';

// Update getOrCreateCodebaseForRepo method
private async getOrCreateCodebaseForRepo(
  owner: string,
  repo: string
): Promise<{ codebase: { id: string; name: string }; repoPath: string; isNew: boolean }> {
  const repoUrlNoGit = `https://github.com/${owner}/${repo}`;
  const repoUrlWithGit = `${repoUrlNoGit}.git`;

  let existing = await codebaseDb.findCodebaseByRepoUrl(repoUrlNoGit);
  existing ??= await codebaseDb.findCodebaseByRepoUrl(repoUrlWithGit);

  // Canonical path is always $WORKSPACE_PATH/{repo}
  const canonicalPath = join(resolve(process.env.WORKSPACE_PATH ?? '/workspace'), repo);

  if (existing) {
    // Check if existing codebase points to a worktree path
    if (await isWorktreePath(existing.default_cwd)) {
      console.log(`[GitHub] Fixing stale worktree path for codebase: ${existing.name}`);
      await codebaseDb.updateCodebase(existing.id, { default_cwd: canonicalPath });
      existing.default_cwd = canonicalPath;
    }

    console.log(`[GitHub] Using existing codebase: ${existing.name} at ${existing.default_cwd}`);
    return { codebase: existing, repoPath: existing.default_cwd, isNew: false };
  }

  const codebase = await codebaseDb.createCodebase({
    name: repo,
    repository_url: repoUrlNoGit,
    default_cwd: canonicalPath,
  });

  console.log(`[GitHub] Created new codebase: ${codebase.name} at ${canonicalPath}`);
  return { codebase, repoPath: canonicalPath, isNew: true };
}
```

**Don't**:
- Don't change the conversation's `cwd` here - that's set to the worktree path separately

**Verify**: `npm run type-check && npm test`

---

### Task 3: Add worktree creation on first @mention

**Why**: Each issue/PR gets automatic isolation before the agent starts working.

**File**: `src/adapters/github.ts`

**Mirror**: Existing `handleWebhook` method flow at line 401

**Do**:

Add worktree creation after repo is ready, before routing to orchestrator:

```typescript
// Add import
import { createWorktreeForIssue } from '../utils/git';

// In handleWebhook, after step 8 (ensureRepoReady) and before step 10 (update conversation):

// 9. Create worktree for this issue/PR (if new conversation)
let worktreePath: string | null = null;
if (isNewConversation) {
  const isPR = eventType === 'pull_request' || (eventType === 'issue_comment' && pullRequest);
  try {
    worktreePath = await createWorktreeForIssue(repoPath, number, isPR);
    console.log(`[GitHub] Created worktree: ${worktreePath}`);

    // Update conversation with worktree path
    await db.updateConversation(existingConv.id, {
      codebase_id: codebase.id,
      cwd: worktreePath,
      worktree_path: worktreePath,
    });
  } catch (error) {
    console.error('[GitHub] Failed to create worktree:', error);
    // Fall back to main repo path
    await db.updateConversation(existingConv.id, {
      codebase_id: codebase.id,
      cwd: repoPath,
    });
  }
} else {
  // For existing conversations, just ensure cwd is set
  if (!existingConv.cwd) {
    await db.updateConversation(existingConv.id, { cwd: repoPath });
  }
}

// Remove the old step 10 that updated conversation (now handled above)
```

**Don't**:
- Don't fail the whole request if worktree creation fails - fall back to main repo
- Don't create worktree for existing conversations

**Verify**: `npm run type-check`

---

### Task 4: Add context message about worktree

**Why**: Agent should know it's in a worktree and can inform the user.

**File**: `src/adapters/github.ts`

**Do**:

Add to the context that gets passed to the AI when in a worktree:

```typescript
// After creating the worktree, add to contextToAppend
if (worktreePath) {
  const branchName = isPR ? `pr-${number}` : `issue-${number}`;
  const worktreeContext = `\n\n[Working in isolated branch: ${branchName}. When done, changes can be committed and pushed, then a PR can be created from this branch.]`;
  contextToAppend = contextToAppend ? contextToAppend + worktreeContext : worktreeContext;
}
```

**Verify**: Manual test - create an issue, @mention the agent, check if it mentions the branch

---

### Task 5: Handle issue close / PR merge for cleanup

**Why**: Automatically clean up worktrees when they're no longer needed.

**File**: `src/adapters/github.ts`

**Mirror**: Existing `parseEvent` method at line 165

**Do**:

1. Update `parseEvent` to detect close/merge events:

```typescript
// Add new return type option
private parseEvent(event: WebhookEvent): {
  // ... existing fields
  isCloseEvent?: boolean;
} | null {
  // ... existing parsing logic

  // Detect issue closed
  if (event.issue && event.action === 'closed') {
    return {
      owner,
      repo,
      number: event.issue.number,
      comment: '',
      eventType: 'issue',
      issue: event.issue,
      isCloseEvent: true,
    };
  }

  // Detect PR merged/closed
  if (event.pull_request && (event.action === 'closed')) {
    return {
      owner,
      repo,
      number: event.pull_request.number,
      comment: '',
      eventType: 'pull_request',
      pullRequest: event.pull_request,
      isCloseEvent: true,
    };
  }

  // ... rest of existing logic
}
```

2. Handle cleanup in `handleWebhook`:

```typescript
// Add import
import { removeWorktree } from '../utils/git';

// In handleWebhook, after parsing event
if (parsed.isCloseEvent) {
  console.log(`[GitHub] Handling close event for ${conversationId}`);
  await this.cleanupWorktree(owner, repo, number);
  return; // Don't process as a message
}

// Add new method
private async cleanupWorktree(owner: string, repo: string, number: number): Promise<void> {
  const conversationId = this.buildConversationId(owner, repo, number);
  const conversation = await db.getConversation('github', conversationId);

  if (!conversation?.worktree_path) {
    console.log(`[GitHub] No worktree to cleanup for ${conversationId}`);
    return;
  }

  const { codebase } = await this.getOrCreateCodebaseForRepo(owner, repo);

  try {
    await removeWorktree(codebase.default_cwd, conversation.worktree_path);
    console.log(`[GitHub] Removed worktree: ${conversation.worktree_path}`);
  } catch (error) {
    console.error(`[GitHub] Failed to remove worktree:`, error);
    // Continue with database cleanup anyway
  }

  // Clear worktree path from conversation, reset cwd to main repo
  await db.updateConversation(conversation.id, {
    worktree_path: null,
    cwd: codebase.default_cwd
  });

  console.log(`[GitHub] Cleanup complete for ${conversationId}`);
}
```

**Don't**:
- Don't fail silently - log errors but continue cleanup
- Don't delete the git branch automatically (user might want it)

**Verify**: Manual test - close an issue that has a worktree, check if worktree is removed

---

### Task 6: Add unit tests for git utilities

**Why**: Ensure git operations work correctly.

**File**: `src/utils/git.test.ts` (NEW)

**Mirror**: Test patterns from `src/db/codebases.test.ts`

**Do**:
```typescript
import { isWorktreePath, getCanonicalRepoPath } from './git';
import { writeFile, mkdir, rm } from 'fs/promises';
import { join } from 'path';
import { tmpdir } from 'os';

describe('git utilities', () => {
  const testDir = join(tmpdir(), 'git-utils-test');

  beforeEach(async () => {
    await mkdir(testDir, { recursive: true });
  });

  afterEach(async () => {
    await rm(testDir, { recursive: true, force: true });
  });

  describe('isWorktreePath', () => {
    it('returns false for directory without .git', async () => {
      const result = await isWorktreePath(testDir);
      expect(result).toBe(false);
    });

    it('returns false for main repo (.git directory)', async () => {
      await mkdir(join(testDir, '.git'));
      const result = await isWorktreePath(testDir);
      expect(result).toBe(false);
    });

    it('returns true for worktree (.git file with gitdir)', async () => {
      await writeFile(
        join(testDir, '.git'),
        'gitdir: /some/repo/.git/worktrees/branch-name'
      );
      const result = await isWorktreePath(testDir);
      expect(result).toBe(true);
    });
  });

  describe('getCanonicalRepoPath', () => {
    it('returns same path for non-worktree', async () => {
      const result = await getCanonicalRepoPath(testDir);
      expect(result).toBe(testDir);
    });

    it('extracts main repo path from worktree', async () => {
      await writeFile(
        join(testDir, '.git'),
        'gitdir: /workspace/my-repo/.git/worktrees/issue-42'
      );
      const result = await getCanonicalRepoPath(testDir);
      expect(result).toBe('/workspace/my-repo');
    });
  });
});
```

**Verify**: `npm test -- src/utils/git.test.ts`

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
| `src/utils/git.test.ts` | isWorktreePath returns false for main repo | Detection logic works |
| `src/utils/git.test.ts` | isWorktreePath returns true for worktree | Detection logic works |
| `src/utils/git.test.ts` | getCanonicalRepoPath extracts main repo | Path resolution works |

### Manual/E2E Validation

```bash
# Start the app
npm run dev

# Ensure ngrok is running
ngrok http 3090
```

1. Create a new test issue on the repo
2. Comment `@remote-agent hello`
3. Check logs for:
   - `[GitHub] Created worktree: /workspace/repo/../worktrees/issue-XX`
   - Agent responds mentioning the branch
4. Close the issue
5. Check logs for:
   - `[GitHub] Handling close event for ...`
   - `[GitHub] Removed worktree: ...`
   - `[GitHub] Cleanup complete`

### Edge Cases
- [ ] Issue created from within a Claude Code worktree session - should still use canonical path
- [ ] Multiple @mentions in same issue - should reuse existing worktree
- [ ] Worktree creation fails (e.g., branch exists with conflicts) - should fall back gracefully
- [ ] Close event before any @mention - should not error (no worktree to clean)
- [ ] PR merged (not just closed) - should trigger cleanup

### Regression Check
- [ ] Telegram adapter still works (doesn't use worktrees)
- [ ] Discord adapter still works
- [ ] Existing /clone command still works
- [ ] Existing conversations without worktrees still work

## Risks

1. **Git worktree command failures**: Mitigated by falling back to main repo
2. **Orphaned worktrees if cleanup fails**: Mitigated by logging errors and continuing DB cleanup
3. **Branch name conflicts**: Handled by reusing existing branch if it exists
4. **Performance**: Worktree creation adds ~1-2s to first response - acceptable tradeoff

## Dependencies

This plan uses the existing `worktree_path` column on conversations (from `migrations/003_add_worktree.sql`).

No new database schema needed - simpler than the full worktree-parallel-execution plan.
