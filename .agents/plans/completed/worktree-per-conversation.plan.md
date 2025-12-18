# Plan: Worktree Per Conversation

## Summary

Add git worktree support so each conversation can work in an isolated worktree. This enables parallel development: multiple Slack threads, Telegram chats, or Discord channels can each have their own branch and working directory, with AI agents working simultaneously without conflicts.

**Approach**: Minimal KISS/YAGNI implementation:
1. Add `worktree_path` column to conversations table
2. Add `/worktree` command with create/list/remove subcommands
3. Orchestrator uses `worktree_path` if set, else falls back to existing `cwd` behavior

No new abstractions, no new tables, no architectural changes.

---

## External Research

### Git Worktree Commands
Sources: [Git Documentation](https://git-scm.com/docs/git-worktree), [GitKraken Tutorial](https://www.gitkraken.com/learn/git/git-worktree)

**Key commands:**
```bash
# Create worktree with new branch
git worktree add <path> -b <branch-name>

# Create worktree on existing branch
git worktree add <path> <branch>

# List all worktrees
git worktree list

# Remove worktree (clean only)
git worktree remove <path>

# Force remove (uncommitted changes)
git worktree remove --force <path>
```

**Important behaviors:**
- If branch omitted from `git worktree add`, creates branch named after directory basename
- Same branch cannot be checked out in multiple worktrees
- `git worktree list --porcelain` gives machine-readable output
- Main worktree cannot be removed

### Best Practices for Parallel AI Development
Sources: [incident.io Blog](https://incident.io/blog/shipping-faster-with-claude-code-and-git-worktrees), [Steve Kinney Course](https://stevekinney.com/courses/ai-development/git-worktrees)

- Each worktree needs its own `npm install` / dependency setup
- Use consistent directory structure: `worktrees/<branch-name>`
- Clean up worktrees when done to avoid clutter
- Commit frequently within each worktree

---

## Patterns to Mirror

### Command Pattern (from command-handler.ts:526-658)

The `/repo` command is the closest analog - it switches context and resets sessions:

```typescript
// FROM: src/handlers/command-handler.ts:526-658
case 'repo': {
  if (args.length === 0) {
    return { success: false, message: 'Usage: /repo <number|name> [pull]' };
  }

  const workspacePath = process.env.WORKSPACE_PATH ?? '/workspace';
  const identifier = args[0];

  // ... find target folder ...

  // Link conversation to codebase
  await db.updateConversation(conversation.id, {
    codebase_id: codebase.id,
    cwd: targetPath,
  });

  // Reset session when switching
  const session = await sessionDb.getActiveSession(conversation.id);
  if (session) {
    await sessionDb.deactivateSession(session.id);
  }

  return { success: true, message: msg, modified: true };
}
```

### execFileAsync Pattern (from command-handler.ts:5-15,278-283)

```typescript
// FROM: src/handlers/command-handler.ts:5-15
import { execFile } from 'child_process';
import { promisify } from 'util';
const execFileAsync = promisify(execFile);

// FROM: src/handlers/command-handler.ts:278-283
await execFileAsync('git', ['clone', cloneUrl, targetPath]);
await execFileAsync('git', ['config', '--global', '--add', 'safe.directory', targetPath]);
```

### Database Update Pattern (from db/conversations.ts:41-69)

```typescript
// FROM: src/db/conversations.ts:41-69
export async function updateConversation(
  id: string,
  updates: Partial<Pick<Conversation, 'codebase_id' | 'cwd'>>
): Promise<void> {
  const fields: string[] = [];
  const values: (string | null)[] = [];
  let i = 1;

  if (updates.codebase_id !== undefined) {
    fields.push(`codebase_id = $${String(i++)}`);
    values.push(updates.codebase_id);
  }
  if (updates.cwd !== undefined) {
    fields.push(`cwd = $${String(i++)}`);
    values.push(updates.cwd);
  }
  // ... execute query
}
```

### Test Pattern (from command-handler.test.ts:1-37)

```typescript
// FROM: src/handlers/command-handler.test.ts:1-37
jest.mock('../db/conversations');
jest.mock('../db/codebases');
jest.mock('../db/sessions');
jest.mock('child_process', () => ({
  exec: jest.fn(),
  execFile: jest.fn(),
}));

const mockExecFile = execFile as unknown as jest.Mock;

describe('CommandHandler', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });
  // ...
});
```

---

## Files to Change

| File | Action | Justification |
|------|--------|---------------|
| `migrations/002_add_worktree.sql` | CREATE | Add worktree_path column |
| `src/types/index.ts` | UPDATE | Add worktree_path to Conversation interface |
| `src/db/conversations.ts` | UPDATE | Support worktree_path in updateConversation |
| `src/handlers/command-handler.ts` | UPDATE | Add /worktree command, update /status |
| `src/orchestrator/orchestrator.ts` | UPDATE | Use worktree_path in cwd resolution |
| `src/handlers/command-handler.test.ts` | UPDATE | Add tests for /worktree command |

---

## NOT Building

- **Worktree pool management** - No separate table, no automatic allocation
- **Auto-cleanup** - User manually removes worktrees
- **npm install automation** - User runs setup commands via AI or manually
- **Status dashboard** - `/worktree list` is sufficient
- **Branch strategy enforcement** - User picks branch names
- **Merge workflow** - Existing git commands work fine
- **Multi-repo worktrees** - One repo per codebase, worktrees within that

---

## Tasks

### Task 1: CREATE migration file

**Why**: Need to store worktree_path per conversation

**Mirror**: `migrations/001_initial_schema.sql`

**Do**:
Create `migrations/002_add_worktree.sql`:
```sql
-- Add worktree support to conversations
-- Version: 2.0
-- Description: Allow each conversation to work in an isolated git worktree

ALTER TABLE remote_agent_conversations
ADD COLUMN worktree_path VARCHAR(500);

-- Add comment for documentation
COMMENT ON COLUMN remote_agent_conversations.worktree_path IS
  'Path to git worktree for this conversation. If set, AI works here instead of cwd.';
```

**Don't**:
- Create a separate worktrees table
- Add foreign keys or constraints

**Verify**: `cat migrations/002_add_worktree.sql`

---

### Task 2: UPDATE types/index.ts

**Why**: TypeScript needs to know about worktree_path

**Mirror**: `src/types/index.ts:5-14` (Conversation interface)

**Do**:
Add `worktree_path` to Conversation interface after `cwd`:

```typescript
export interface Conversation {
  id: string;
  platform_type: string;
  platform_conversation_id: string;
  codebase_id: string | null;
  cwd: string | null;
  worktree_path: string | null;  // ADD THIS LINE
  ai_assistant_type: string;
  created_at: Date;
  updated_at: Date;
}
```

**Don't**:
- Add any other types
- Create a Worktree interface

**Verify**: `npm run type-check`

---

### Task 3: UPDATE db/conversations.ts

**Why**: updateConversation needs to handle worktree_path

**Mirror**: `src/db/conversations.ts:41-69`

**Do**:
Add worktree_path handling to updateConversation. Update the function signature and add a new condition:

1. Update the type signature to include worktree_path:
```typescript
export async function updateConversation(
  id: string,
  updates: Partial<Pick<Conversation, 'codebase_id' | 'cwd' | 'worktree_path'>>
): Promise<void> {
```

2. Add handling after the cwd check (around line 56):
```typescript
  if (updates.worktree_path !== undefined) {
    fields.push(`worktree_path = $${String(i++)}`);
    values.push(updates.worktree_path);
  }
```

**Don't**:
- Create new functions
- Change the query structure

**Verify**: `npm run type-check`

---

### Task 4: UPDATE orchestrator.ts - cwd resolution

**Why**: Orchestrator needs to use worktree_path when set

**Mirror**: `src/orchestrator/orchestrator.ts:125`

**Do**:
Change line 125 from:
```typescript
const cwd = conversation.cwd ?? codebase?.default_cwd ?? '/workspace';
```
To:
```typescript
const cwd = conversation.worktree_path ?? conversation.cwd ?? codebase?.default_cwd ?? '/workspace';
```

Also update line 87 (command file path resolution) the same way:
```typescript
const cwd = conversation.worktree_path ?? conversation.cwd ?? codebase.default_cwd;
```

**Don't**:
- Add logging
- Add any other logic

**Verify**: `npm run type-check`

---

### Task 5: UPDATE command-handler.ts - add /worktree command

**Why**: Users need commands to create/list/remove worktrees

**Mirror**: `src/handlers/command-handler.ts:526-658` (the /repo command pattern)

**Do**:

1. Add to help text (around line 97):
```typescript
Worktrees:
  /worktree create <branch> - Create isolated worktree
  /worktree list - Show worktrees for this repo
  /worktree remove - Remove current worktree
```

2. Add to /status output (around line 120, after cwd):
```typescript
if (conversation.worktree_path) {
  msg += `\nWorktree: ${conversation.worktree_path}`;
}
```

3. Add new case before the `default:` case (around line 740):

```typescript
case 'worktree': {
  const subcommand = args[0];

  if (!conversation.codebase_id) {
    return { success: false, message: 'No codebase configured. Use /clone first.' };
  }

  const codebase = await codebaseDb.getCodebase(conversation.codebase_id);
  if (!codebase) {
    return { success: false, message: 'Codebase not found.' };
  }

  const mainPath = codebase.default_cwd;
  const worktreesDir = join(mainPath, 'worktrees');

  switch (subcommand) {
    case 'create': {
      const branchName = args[1];
      if (!branchName) {
        return { success: false, message: 'Usage: /worktree create <branch-name>' };
      }

      // Validate branch name (alphanumeric, dash, underscore only)
      if (!/^[a-zA-Z0-9_-]+$/.test(branchName)) {
        return {
          success: false,
          message: 'Branch name must contain only letters, numbers, dashes, and underscores.'
        };
      }

      const worktreePath = join(worktreesDir, branchName);

      try {
        // Create worktree with new branch
        await execFileAsync('git', ['-C', mainPath, 'worktree', 'add', worktreePath, '-b', branchName]);

        // Add to git safe.directory
        await execFileAsync('git', ['config', '--global', '--add', 'safe.directory', worktreePath]);

        // Update conversation to use this worktree
        await db.updateConversation(conversation.id, { worktree_path: worktreePath });

        // Reset session for fresh start
        const session = await sessionDb.getActiveSession(conversation.id);
        if (session) {
          await sessionDb.deactivateSession(session.id);
        }

        return {
          success: true,
          message: `Worktree created!\n\nBranch: ${branchName}\nPath: ${worktreePath}\n\nThis conversation now works in isolation.\nRun dependency install if needed (e.g., npm install).`,
          modified: true,
        };
      } catch (error) {
        const err = error as Error;
        console.error('[Worktree] Create failed:', err);

        // Check for common errors
        if (err.message.includes('already exists')) {
          return { success: false, message: `Branch '${branchName}' already exists. Use a different name.` };
        }
        return { success: false, message: `Failed to create worktree: ${err.message}` };
      }
    }

    case 'list': {
      try {
        const { stdout } = await execFileAsync('git', ['-C', mainPath, 'worktree', 'list']);

        // Parse output and mark current
        const lines = stdout.trim().split('\n');
        let msg = 'Worktrees:\n\n';

        for (const line of lines) {
          const isActive = conversation.worktree_path && line.startsWith(conversation.worktree_path);
          const marker = isActive ? ' <- active' : '';
          msg += `${line}${marker}\n`;
        }

        return { success: true, message: msg };
      } catch (error) {
        const err = error as Error;
        return { success: false, message: `Failed to list worktrees: ${err.message}` };
      }
    }

    case 'remove': {
      if (!conversation.worktree_path) {
        return { success: false, message: 'This conversation is not using a worktree.' };
      }

      const worktreePath = conversation.worktree_path;

      try {
        // Remove worktree (--force to handle uncommitted changes)
        await execFileAsync('git', ['-C', mainPath, 'worktree', 'remove', '--force', worktreePath]);

        // Clear worktree_path, keep cwd pointing to main repo
        await db.updateConversation(conversation.id, {
          worktree_path: null,
          cwd: mainPath
        });

        // Reset session
        const session = await sessionDb.getActiveSession(conversation.id);
        if (session) {
          await sessionDb.deactivateSession(session.id);
        }

        return {
          success: true,
          message: `Worktree removed: ${worktreePath}\n\nSwitched back to main repo: ${mainPath}`,
          modified: true,
        };
      } catch (error) {
        const err = error as Error;
        console.error('[Worktree] Remove failed:', err);
        return { success: false, message: `Failed to remove worktree: ${err.message}` };
      }
    }

    default:
      return {
        success: false,
        message: 'Usage:\n  /worktree create <branch>\n  /worktree list\n  /worktree remove',
      };
  }
}
```

**Don't**:
- Add path validation (worktrees are always in repo/worktrees/)
- Add npm install automation
- Add merge commands

**Verify**: `npm run type-check && npm run lint`

---

### Task 6: UPDATE command-handler.test.ts - add tests

**Why**: New command needs test coverage

**Mirror**: `src/handlers/command-handler.test.ts:219-261` (setcwd tests)

**Do**:

Add new describe block for worktree tests. Insert after the existing test blocks (around line 470 or where appropriate):

```typescript
describe('/worktree', () => {
  const conversationWithCodebase = {
    ...baseConversation,
    codebase_id: 'codebase-123',
    cwd: '/workspace/my-repo',
  };

  beforeEach(() => {
    mockCodebaseDb.getCodebase.mockResolvedValue({
      id: 'codebase-123',
      name: 'my-repo',
      repository_url: 'https://github.com/user/my-repo',
      default_cwd: '/workspace/my-repo',
      ai_assistant_type: 'claude',
      commands: {},
      created_at: new Date(),
      updated_at: new Date(),
    });
  });

  describe('create', () => {
    test('should require codebase', async () => {
      const result = await handleCommand(baseConversation, '/worktree create feat-x');
      expect(result.success).toBe(false);
      expect(result.message).toContain('No codebase');
    });

    test('should require branch name', async () => {
      const result = await handleCommand(conversationWithCodebase, '/worktree create');
      expect(result.success).toBe(false);
      expect(result.message).toContain('Usage');
    });

    test('should validate branch name format', async () => {
      const result = await handleCommand(conversationWithCodebase, '/worktree create "bad name"');
      expect(result.success).toBe(false);
      expect(result.message).toContain('letters, numbers');
    });

    test('should create worktree with valid name', async () => {
      mockExecFile.mockImplementation((_cmd: string, _args: string[], callback: Function) => {
        callback(null, { stdout: '', stderr: '' });
      });
      mockSessionDb.getActiveSession.mockResolvedValue(null);

      const result = await handleCommand(conversationWithCodebase, '/worktree create feat-auth');

      expect(result.success).toBe(true);
      expect(result.message).toContain('Worktree created');
      expect(result.message).toContain('feat-auth');
      expect(mockDb.updateConversation).toHaveBeenCalledWith(
        conversationWithCodebase.id,
        expect.objectContaining({ worktree_path: '/workspace/my-repo/worktrees/feat-auth' })
      );
    });
  });

  describe('list', () => {
    test('should list worktrees', async () => {
      mockExecFile.mockImplementation((_cmd: string, _args: string[], callback: Function) => {
        callback(null, {
          stdout: '/workspace/my-repo  abc1234 [main]\n/workspace/my-repo/worktrees/feat-x  def5678 [feat-x]\n',
          stderr: ''
        });
      });

      const result = await handleCommand(conversationWithCodebase, '/worktree list');

      expect(result.success).toBe(true);
      expect(result.message).toContain('Worktrees:');
      expect(result.message).toContain('main');
    });
  });

  describe('remove', () => {
    test('should require active worktree', async () => {
      const result = await handleCommand(conversationWithCodebase, '/worktree remove');
      expect(result.success).toBe(false);
      expect(result.message).toContain('not using a worktree');
    });

    test('should remove worktree and switch to main', async () => {
      const convWithWorktree = {
        ...conversationWithCodebase,
        worktree_path: '/workspace/my-repo/worktrees/feat-x',
      };

      mockExecFile.mockImplementation((_cmd: string, _args: string[], callback: Function) => {
        callback(null, { stdout: '', stderr: '' });
      });
      mockSessionDb.getActiveSession.mockResolvedValue(null);

      const result = await handleCommand(convWithWorktree, '/worktree remove');

      expect(result.success).toBe(true);
      expect(result.message).toContain('removed');
      expect(mockDb.updateConversation).toHaveBeenCalledWith(
        convWithWorktree.id,
        expect.objectContaining({ worktree_path: null, cwd: '/workspace/my-repo' })
      );
    });
  });

  describe('default', () => {
    test('should show usage for unknown subcommand', async () => {
      const result = await handleCommand(conversationWithCodebase, '/worktree foo');
      expect(result.success).toBe(false);
      expect(result.message).toContain('Usage');
    });
  });
});
```

**Don't**:
- Test git internals
- Mock filesystem operations

**Verify**: `npm test -- --testPathPattern=command-handler`

---

## Validation Strategy

### Automated Checks

- [ ] `npm run type-check` - Types valid
- [ ] `npm run lint` - No lint errors
- [ ] `npm run test` - All tests pass (including new worktree tests)
- [ ] `npm run build` - Build succeeds

### New Tests to Write

| Test File | Test Case | What It Validates |
|-----------|-----------|-------------------|
| `command-handler.test.ts` | /worktree create requires codebase | Guard clause works |
| `command-handler.test.ts` | /worktree create requires branch name | Input validation |
| `command-handler.test.ts` | /worktree create validates branch format | Security/sanity |
| `command-handler.test.ts` | /worktree create success path | Full flow works |
| `command-handler.test.ts` | /worktree list shows worktrees | List command works |
| `command-handler.test.ts` | /worktree remove requires active worktree | Guard clause |
| `command-handler.test.ts` | /worktree remove success path | Cleanup works |

### Manual/E2E Validation

**Setup:**
```bash
# Terminal 1: Start postgres
docker-compose --profile with-db up -d postgres

# Terminal 2: Run migrations
psql $DATABASE_URL < migrations/001_initial_schema.sql
psql $DATABASE_URL < migrations/002_add_worktree.sql

# Terminal 2: Start app
npm run dev
```

**Test via Test Adapter:**
```bash
# 1. Clone a repo first
curl -X POST http://localhost:3000/test/message \
  -H "Content-Type: application/json" \
  -d '{"conversationId":"test-wt","message":"/clone https://github.com/user/some-repo"}'

# 2. Check status (no worktree yet)
curl -X POST http://localhost:3000/test/message \
  -H "Content-Type: application/json" \
  -d '{"conversationId":"test-wt","message":"/status"}'

# 3. Create worktree
curl -X POST http://localhost:3000/test/message \
  -H "Content-Type: application/json" \
  -d '{"conversationId":"test-wt","message":"/worktree create feat-test"}'

# 4. Check status (should show worktree)
curl -X POST http://localhost:3000/test/message \
  -H "Content-Type: application/json" \
  -d '{"conversationId":"test-wt","message":"/status"}'

# 5. List worktrees
curl -X POST http://localhost:3000/test/message \
  -H "Content-Type: application/json" \
  -d '{"conversationId":"test-wt","message":"/worktree list"}'

# 6. Verify AI works in worktree (send a simple prompt)
curl -X POST http://localhost:3000/test/message \
  -H "Content-Type: application/json" \
  -d '{"conversationId":"test-wt","message":"What branch am I on? Run git branch."}'

# 7. Get responses
curl http://localhost:3000/test/messages/test-wt | jq

# 8. Remove worktree
curl -X POST http://localhost:3000/test/message \
  -H "Content-Type: application/json" \
  -d '{"conversationId":"test-wt","message":"/worktree remove"}'

# 9. Cleanup
curl -X DELETE http://localhost:3000/test/messages/test-wt
```

### Edge Cases to Test

- [ ] Create worktree with branch name that already exists (should error)
- [ ] Create worktree when already in a worktree (should work - creates nested-ish structure)
- [ ] Remove worktree with uncommitted changes (--force handles this)
- [ ] List worktrees when none exist except main (should show just main)
- [ ] Branch name with special characters (should reject)
- [ ] Very long branch name (git will handle limits)

### Regression Check

- [ ] `/clone` still works (no worktree set)
- [ ] `/repo` switching still works
- [ ] `/status` shows correct info without worktree
- [ ] AI queries work when no worktree is set (uses cwd)
- [ ] Existing conversations without worktree_path still work

---

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Migration fails on existing DB | Low | Column is nullable, no constraint violations |
| Branch name conflicts | Medium | Validate format, let git error on duplicates |
| Worktree directory already exists | Low | Git will error, we report it |
| User forgets to install deps | Medium | Message reminds them after create |
| Orphaned worktrees after conversation delete | Low | User can manually prune with `git worktree prune` |

---

## Summary

This is a ~150-line change that enables parallel development across conversations:

1. **1 migration file** (5 lines) - adds `worktree_path` column
2. **1 type change** (1 line) - adds field to interface
3. **1 DB function update** (5 lines) - handles new field
4. **1 orchestrator change** (2 lines) - priority: worktree_path > cwd > default_cwd
5. **1 command addition** (~120 lines) - /worktree create|list|remove
6. **Tests** (~80 lines) - cover the new command

After this, each Slack thread / Telegram chat / Discord channel can run `/worktree create <branch>` and get their own isolated environment.
