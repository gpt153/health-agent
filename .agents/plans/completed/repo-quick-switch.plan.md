# Plan: Repo Quick Switch Command

## Summary

Add a `/repo` command for quick repository switching with numbered IDs. This improves UX by reducing the current 3-step flow (`/clone` → `/load-commands` → `/command-invoke`) to a single command. The `/repos` command will show numbered IDs, and `/repo <id|name> [pull]` will switch context, link codebase, and auto-load commands.

## External Research

Not needed - this is internal command handler logic using existing patterns.

## Patterns to Mirror

### Command Handler Pattern
From `src/handlers/command-handler.ts:470-498`:
```typescript
case 'repos': {
  const workspacePath = process.env.WORKSPACE_PATH ?? '/workspace';

  try {
    const entries = await readdir(workspacePath, { withFileTypes: true });
    const folders = entries.filter(entry => entry.isDirectory()).map(entry => entry.name);

    if (!folders.length) {
      return {
        success: true,
        message: 'No repositories found in /workspace',
      };
    }

    const currentCwd = conversation.cwd ?? '';
    let msg = 'Workspace Repositories:\n\n';

    folders.forEach(folder => {
      const folderPath = join(workspacePath, folder);
      const isActive = currentCwd.startsWith(folderPath);
      msg += `${folderPath}${isActive ? ' [active]' : ''}\n`;
    });

    return { success: true, message: msg };
  } catch (error) {
    // ...
  }
}
```

### Codebase Linking Pattern
From `src/handlers/command-handler.ts:210-245` (existing codebase link on `/clone`):
```typescript
if (existingCodebase) {
  // Link conversation to existing codebase
  await db.updateConversation(conversation.id, {
    codebase_id: existingCodebase.id,
    cwd: targetPath,
  });

  // Reset session when switching codebases
  const session = await sessionDb.getActiveSession(conversation.id);
  if (session) {
    await sessionDb.deactivateSession(session.id);
  }

  // Check for command folders
  let commandFolder: string | null = null;
  for (const folder of ['.claude/commands', '.agents/commands']) {
    try {
      await access(join(targetPath, folder));
      commandFolder = folder;
      break;
    } catch {
      /* ignore */
    }
  }
  // ...
}
```

### Database Query for Codebases by Path
From `src/db/codebases.ts:57-63`:
```typescript
export async function findCodebaseByRepoUrl(repoUrl: string): Promise<Codebase | null> {
  const result = await pool.query<Codebase>(
    'SELECT * FROM remote_agent_codebases WHERE repository_url = $1',
    [repoUrl]
  );
  return result.rows[0] || null;
}
```

### Auto-Load Commands Pattern
From `src/handlers/command-handler.ts:414-439`:
```typescript
const markdownFiles = await findMarkdownFilesRecursive(fullPath);

if (!markdownFiles.length) {
  return {
    success: false,
    message: `No .md files found in ${folderPath} (searched recursively)`,
  };
}

const commands = await codebaseDb.getCodebaseCommands(conversation.codebase_id);

markdownFiles.forEach(({ commandName, relativePath }) => {
  commands[commandName] = {
    path: join(folderPath, relativePath),
    description: `From ${folderPath}`,
  };
});

await codebaseDb.updateCodebaseCommands(conversation.codebase_id, commands);
```

### Test Pattern
From `src/handlers/command-handler.test.ts:112-116`:
```typescript
test('should parse /repos', () => {
  const result = parseCommand('/repos');
  expect(result.command).toBe('repos');
  expect(result.args).toEqual([]);
});
```

## Files to Change

| File | Action | Justification |
|------|--------|---------------|
| `src/db/codebases.ts` | UPDATE | Add `findCodebaseByDefaultCwd()` function |
| `src/handlers/command-handler.ts` | UPDATE | Modify `/repos`, add `/repo` command |
| `src/handlers/command-handler.test.ts` | UPDATE | Add tests for new functionality |
| `src/db/codebases.test.ts` | UPDATE | Add test for new db function |

## NOT Building

- ❌ No persistent repo numbering (IDs are assigned at runtime based on directory order)
- ❌ No git pull authentication handling (uses existing git config)
- ❌ No caching of repo list (re-scanned each time)
- ❌ No branch switching (just pull on current branch)

## Tasks

### Task 1: Add `findCodebaseByDefaultCwd()` to codebases.ts

**Why**: Need to find existing codebase by path, not just URL

**Mirror**: `src/db/codebases.ts:57-63`

**Do**:
Add after `findCodebaseByRepoUrl`:
```typescript
export async function findCodebaseByDefaultCwd(defaultCwd: string): Promise<Codebase | null> {
  const result = await pool.query<Codebase>(
    'SELECT * FROM remote_agent_codebases WHERE default_cwd = $1 ORDER BY created_at DESC LIMIT 1',
    [defaultCwd]
  );
  return result.rows[0] || null;
}
```

**Don't**:
- Don't match partial paths
- Don't return multiple codebases (just the most recent one)

**Verify**: `npm run type-check`

### Task 2: Update `/repos` command to show numbered IDs

**Why**: Users need to see the IDs to use with `/repo` command

**Mirror**: `src/handlers/command-handler.ts:470-498`

**Do**:
Modify the `repos` case to number each repo:
```typescript
case 'repos': {
  const workspacePath = process.env.WORKSPACE_PATH ?? '/workspace';

  try {
    const entries = await readdir(workspacePath, { withFileTypes: true });
    const folders = entries
      .filter(entry => entry.isDirectory())
      .map(entry => entry.name)
      .sort(); // Consistent ordering

    if (!folders.length) {
      return {
        success: true,
        message: 'No repositories found in /workspace\n\nUse /clone <repo-url> to add one.',
      };
    }

    const currentCwd = conversation.cwd ?? '';
    let msg = 'Repositories:\n\n';

    for (let i = 0; i < folders.length; i++) {
      const folder = folders[i];
      const folderPath = join(workspacePath, folder);
      const isActive = currentCwd.startsWith(folderPath);
      const marker = isActive ? ' ← active' : '';
      msg += `${String(i + 1)}. ${folder}${marker}\n`;
    }

    msg += '\nUse /repo <number|name> to switch';

    return { success: true, message: msg };
  } catch (error) {
    const err = error as Error;
    console.error('[Command] repos failed:', err);
    return { success: false, message: `Failed to list repositories: ${err.message}` };
  }
}
```

**Don't**:
- Don't show full paths (clutters output)
- Don't show codebase details (keep it simple)

**Verify**: `npm run type-check`

### Task 3: Add `/repo` command

**Why**: Quick switch between repos with auto-setup

**Mirror**: Clone logic at `src/handlers/command-handler.ts:210-245`

**Do**:
Add new case before `default`:
```typescript
case 'repo': {
  if (args.length === 0) {
    return { success: false, message: 'Usage: /repo <number|name> [pull]' };
  }

  const workspacePath = process.env.WORKSPACE_PATH ?? '/workspace';
  const identifier = args[0];
  const shouldPull = args[1]?.toLowerCase() === 'pull';

  try {
    // Get sorted list of repos (same as /repos)
    const entries = await readdir(workspacePath, { withFileTypes: true });
    const folders = entries
      .filter(entry => entry.isDirectory())
      .map(entry => entry.name)
      .sort();

    if (!folders.length) {
      return {
        success: false,
        message: 'No repositories found. Use /clone <repo-url> first.',
      };
    }

    // Find the target folder by number or name
    let targetFolder: string | undefined;
    const num = parseInt(identifier, 10);
    if (!isNaN(num) && num >= 1 && num <= folders.length) {
      targetFolder = folders[num - 1];
    } else {
      // Try exact match first, then prefix match
      targetFolder = folders.find(f => f === identifier) ?? folders.find(f => f.startsWith(identifier));
    }

    if (!targetFolder) {
      return {
        success: false,
        message: `Repository not found: ${identifier}\n\nUse /repos to see available repositories.`,
      };
    }

    const targetPath = join(workspacePath, targetFolder);

    // Git pull if requested
    if (shouldPull) {
      try {
        await execFileAsync('git', ['-C', targetPath, 'pull']);
        console.log(`[Command] Pulled latest for ${targetFolder}`);
      } catch (pullError) {
        const err = pullError as Error;
        console.error('[Command] git pull failed:', err);
        return {
          success: false,
          message: `Failed to pull: ${err.message}`,
        };
      }
    }

    // Find or create codebase for this path
    let codebase = await codebaseDb.findCodebaseByDefaultCwd(targetPath);

    if (!codebase) {
      // Create new codebase for this directory
      // Auto-detect assistant type
      let suggestedAssistant = 'claude';
      try {
        await access(join(targetPath, '.codex'));
        suggestedAssistant = 'codex';
      } catch {
        // Default to claude
      }

      codebase = await codebaseDb.createCodebase({
        name: targetFolder,
        default_cwd: targetPath,
        ai_assistant_type: suggestedAssistant,
      });
      console.log(`[Command] Created codebase for ${targetFolder}`);
    }

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

    // Auto-load commands if found
    let commandsLoaded = 0;
    for (const folder of ['.claude/commands', '.agents/commands']) {
      try {
        const commandPath = join(targetPath, folder);
        await access(commandPath);

        const markdownFiles = await findMarkdownFilesRecursive(commandPath);
        if (markdownFiles.length > 0) {
          const commands = await codebaseDb.getCodebaseCommands(codebase.id);
          markdownFiles.forEach(({ commandName, relativePath }) => {
            commands[commandName] = {
              path: join(folder, relativePath),
              description: `From ${folder}`,
            };
          });
          await codebaseDb.updateCodebaseCommands(codebase.id, commands);
          commandsLoaded = markdownFiles.length;
          break;
        }
      } catch {
        // Folder doesn't exist, try next
      }
    }

    let msg = `Switched to: ${targetFolder}`;
    if (shouldPull) {
      msg += '\n✓ Pulled latest changes';
    }
    if (commandsLoaded > 0) {
      msg += `\n✓ Loaded ${commandsLoaded} commands`;
    }
    msg += '\n\nReady to work!';

    return { success: true, message: msg, modified: true };
  } catch (error) {
    const err = error as Error;
    console.error('[Command] repo switch failed:', err);
    return { success: false, message: `Failed: ${err.message}` };
  }
}
```

**Don't**:
- Don't validate path with `isPathWithinWorkspace` (we're constructing from workspace already)
- Don't add complex branch handling

**Verify**: `npm run type-check`

### Task 4: Update help text

**Why**: Users need to know about the new command

**Mirror**: `src/handlers/command-handler.ts:78-100`

**Do**:
Update the help case:
```typescript
case 'help':
  return {
    success: true,
    message: `Available Commands:

Command Management:
  /command-set <name> <path> [text] - Register command
  /load-commands <folder> - Bulk load (recursive)
  /command-invoke <name> [args] - Execute
  /commands - List registered
  Note: Commands use relative paths (e.g., .claude/commands)

Codebase:
  /clone <repo-url> - Clone repository
  /repos - List repositories (numbered)
  /repo <#|name> [pull] - Switch repo (auto-loads commands)
  /getcwd - Show working directory
  /setcwd <path> - Set directory
  Note: Use /repo for quick switching, /setcwd for manual paths

Session:
  /status - Show state
  /reset - Clear session
  /help - Show help`,
  };
```

**Verify**: `npm run type-check`

### Task 5: Add unit tests

**Why**: Validate the new functionality

**Mirror**: `src/handlers/command-handler.test.ts`, `src/db/codebases.test.ts`

**Do**:

In `src/handlers/command-handler.test.ts`, add:
```typescript
test('should parse /repo with number', () => {
  const result = parseCommand('/repo 1');
  expect(result.command).toBe('repo');
  expect(result.args).toEqual(['1']);
});

test('should parse /repo with name', () => {
  const result = parseCommand('/repo dylan');
  expect(result.command).toBe('repo');
  expect(result.args).toEqual(['dylan']);
});

test('should parse /repo with pull', () => {
  const result = parseCommand('/repo 1 pull');
  expect(result.command).toBe('repo');
  expect(result.args).toEqual(['1', 'pull']);
});
```

In `src/db/codebases.test.ts`, add:
```typescript
describe('findCodebaseByDefaultCwd', () => {
  test('should find codebase by default_cwd', async () => {
    mockQuery.mockResolvedValueOnce(createQueryResult([{
      id: 'cb-123',
      name: 'test-repo',
      default_cwd: '/workspace/test-repo',
      ai_assistant_type: 'claude',
    }]));

    const result = await findCodebaseByDefaultCwd('/workspace/test-repo');
    expect(result).toBeDefined();
    expect(result?.name).toBe('test-repo');
    expect(mockQuery).toHaveBeenCalledWith(
      'SELECT * FROM remote_agent_codebases WHERE default_cwd = $1 ORDER BY created_at DESC LIMIT 1',
      ['/workspace/test-repo']
    );
  });

  test('should return null when codebase not found', async () => {
    mockQuery.mockResolvedValueOnce(createQueryResult([]));

    const result = await findCodebaseByDefaultCwd('/workspace/nonexistent');
    expect(result).toBeNull();
  });
});
```

**Verify**: `npm test`

## Validation Strategy

### Automated Checks
- [ ] `npm run type-check` - Types valid
- [ ] `npm run lint` - No lint errors
- [ ] `npm run test` - All tests pass
- [ ] `npm run build` - Build succeeds

### New Tests to Write
| Test File | Test Case | What It Validates |
|-----------|-----------|-------------------|
| `command-handler.test.ts` | parse /repo with number | Arg parsing |
| `command-handler.test.ts` | parse /repo with name | Arg parsing |
| `command-handler.test.ts` | parse /repo with pull | Arg parsing |
| `codebases.test.ts` | findCodebaseByDefaultCwd found | DB query works |
| `codebases.test.ts` | findCodebaseByDefaultCwd not found | Null handling |

### Manual/E2E Validation
```bash
# Start app in Docker
docker-compose --profile with-db up -d

# In Telegram/Discord:
/repos                    # Should show numbered list
/repo 1                   # Should switch and auto-load commands
/commands                 # Should show loaded commands
/command-invoke context-prime  # Should work immediately
/repo dylan pull          # Should pull and switch
```

### Edge Cases
- [ ] `/repo 0` - Should fail (1-indexed)
- [ ] `/repo 999` - Should fail (out of range)
- [ ] `/repo nonexistent` - Should fail with helpful message
- [ ] `/repo dyl` - Should match `dylan` via prefix
- [ ] `/repo 1 pull` with no network - Should fail gracefully
- [ ] Empty workspace - Should fail with "use /clone" message

### Regression Check
- [ ] `/repos` still works (now with numbers)
- [ ] `/clone` still works
- [ ] `/setcwd` still works
- [ ] `/status` shows correct codebase after `/repo` switch

## Risks

1. **Duplicate codebases**: If same path has multiple codebases, we pick most recent. Could cause confusion.
2. **Git pull failures**: Network issues, merge conflicts, auth problems. Mitigated by clear error messages.
3. **Command folder not found**: If repo has commands elsewhere, they won't auto-load. User can still use `/load-commands`.
