# Plan: Skill-App Worktree Symbiosis

## Summary

Enable the worktree-manager skill (Claude Code local development) and the remote-coding-agent app (GitHub automation) to work together seamlessly while remaining independent. The key insight is using **git as the source of truth** via `git worktree list`, with a shared configurable base directory. Each system maintains its own metadata (skill: JSON registry, app: database) but can discover and adopt worktrees created by the other.

## External Research

### Git Worktree Best Practices
- [Git Worktree Documentation](https://git-scm.com/docs/git-worktree) - Official docs
- [Git Worktree Best Practices (GitHub Gist)](https://gist.github.com/ChristopherA/4643b2f5e024578606b9cd5d2e6815cc) - Community patterns
- [Using Git Worktrees with Claude Code](https://stevekinney.com/courses/ai-development/git-worktrees) - Parallel AI development

**Key findings:**
- `git worktree list` is the canonical source of truth for all worktrees
- Worktrees can be created anywhere but keeping them organized in one base directory is recommended
- Cleanup requires both `git worktree remove` and optionally `git worktree prune`
- Each worktree has independent HEAD but shares refs with main repo

### File Watching (Not Recommended)
- [Chokidar](https://github.com/paulmillr/chokidar) - Most popular Node.js file watcher
- Research conclusion: File watching adds complexity and race conditions. **Not using** - instead rely on explicit registration and git as source of truth.

## Current State Analysis

### Skill (worktree-manager)
```
Location: ~/.claude/skills/worktree-manager/
Config: ~/.claude/skills/worktree-manager/config.json
Registry: ~/.claude/worktree-registry.json
Base dir: ~/tmp/worktrees/<project>/<branch-slug>/
Naming: feature-auth, fix-login-bug (slugified branch names)
```

### App (remote-coding-agent)
```
Location: src/utils/git.ts, src/adapters/github.ts
Storage: Database (conversations.worktree_path)
Base dir: <repo>/../worktrees/<issue|pr>-<number>/
Naming: issue-42, pr-15 (issue/PR numbers)
```

### The Gap
- Different base directories (skill: `~/tmp/worktrees/`, app: `<repo>/../worktrees/`)
- Different naming conventions (skill: branch-based, app: issue/PR-based)
- No awareness of each other's worktrees
- No shared cleanup mechanism

## Patterns to Mirror

### Environment Variable Pattern
```typescript
// FROM: src/handlers/command-handler.ts:33
const workspacePath = resolve(process.env.WORKSPACE_PATH ?? '/workspace');
```

### Worktree Path Construction
```typescript
// FROM: src/utils/git.ts:36-37
const branchName = isPR ? `pr-${String(issueNumber)}` : `issue-${String(issueNumber)}`;
const worktreePath = join(repoPath, '..', 'worktrees', branchName);
```

### Codebase Path Resolution
```typescript
// FROM: src/adapters/github.ts:364-365
// Canonical path is always $WORKSPACE_PATH/{repo}
const canonicalPath = join(resolve(process.env.WORKSPACE_PATH ?? '/workspace'), repo);
```

## Files to Change

| File | Action | Justification |
|------|--------|---------------|
| `.env.example` | UPDATE | Add `WORKTREE_BASE` env var documentation |
| `src/utils/git.ts` | UPDATE | Use `WORKTREE_BASE` for worktree path construction |
| `src/adapters/github.ts` | UPDATE | Check for existing worktrees before creating, adopt skill-created worktrees |
| `src/handlers/command-handler.ts` | UPDATE | Add `/worktree adopt` command for manual adoption |
| `CLAUDE.md` | UPDATE | Document skill-app symbiosis configuration |

## NOT Building (Explicit Scope Limits)

- **NO file watching** - adds complexity, race conditions
- **NO automatic sync** between skill JSON and app DB - each manages own metadata
- **NO API between skill and app** - too tightly coupled
- **NO changes to skill itself** - skill remains independent, only app changes
- **NO unified cleanup** - each system cleans up what it created
- **NO forced naming convention** - both can coexist with different names

## Architecture Design

### Phase 1: Shared Base Directory (Minimal Viable)

```
WORKTREE_BASE (env var)
├── project-a/
│   ├── issue-42/        (created by app)
│   ├── pr-15/           (created by app)
│   └── feature-auth/    (created by skill)
└── project-b/
    └── fix-bug/         (created by skill)
```

**How it works:**
1. Both skill and app use `WORKTREE_BASE` (default: varies per system)
2. If user sets `WORKTREE_BASE=~/tmp/worktrees`, both use same directory
3. Git worktree list shows ALL worktrees regardless of creator
4. Each maintains own metadata (JSON/DB) but can discover others

### Phase 2: Worktree Adoption

When app receives GitHub event for issue/PR:
1. Check if worktree already exists at expected path
2. Check if ANY worktree exists for this repo (via `git worktree list`)
3. If skill-created worktree exists with matching branch → adopt it
4. If not → create new worktree as before

### Phase 3: Orphan Detection

Add `/worktree orphans` command that:
1. Lists worktrees in git but not in app DB
2. Lists worktrees in app DB but not on disk
3. Offers to adopt or cleanup

## Tasks

### Task 1: Add WORKTREE_BASE env var

**Why**: Enable configurable shared worktree directory between skill and app.

**Mirror**: `src/handlers/command-handler.ts:33` (WORKSPACE_PATH pattern)

**Do**:

1. Update `.env.example`:
```env
# Worktree Base Directory
# Where worktrees are created for GitHub issues/PRs
# Set to same value as skill's worktreeBase for symbiosis with worktree-manager skill
# Default: ${WORKSPACE_PATH}/../worktrees (relative to repo parent)
WORKTREE_BASE=~/tmp/worktrees
```

2. Update `src/utils/git.ts`:
```typescript
// Add at top of file, after imports
function getWorktreeBase(repoPath: string): string {
  const envBase = process.env.WORKTREE_BASE;
  if (envBase) {
    // Expand ~ to home directory
    return envBase.replace(/^~/, process.env.HOME ?? '');
  }
  // Default: sibling to repo (original behavior)
  return join(repoPath, '..', 'worktrees');
}

// Update createWorktreeForIssue to use it:
export async function createWorktreeForIssue(
  repoPath: string,
  issueNumber: number,
  isPR: boolean,
  prHeadBranch?: string
): Promise<string> {
  const branchName = isPR ? `pr-${String(issueNumber)}` : `issue-${String(issueNumber)}`;

  // Get project name from repo path for organization
  const projectName = basename(repoPath);
  const worktreeBase = getWorktreeBase(repoPath);
  const worktreePath = join(worktreeBase, projectName, branchName);

  // ... rest unchanged
}
```

**Don't**:
- Don't change default behavior if env var not set
- Don't add file watching

**Verify**: `npm run type-check && npm test`

---

### Task 2: Add worktree existence check

**Why**: Before creating a worktree, check if one already exists (possibly created by skill).

**Mirror**: `src/adapters/github.ts:293-314` (ensureRepoReady pattern - check then create)

**Do**:

1. Add helper to `src/utils/git.ts`:
```typescript
/**
 * Check if a worktree already exists at the given path
 */
export async function worktreeExists(worktreePath: string): Promise<boolean> {
  try {
    await access(worktreePath);
    const gitPath = join(worktreePath, '.git');
    await access(gitPath);
    return true;
  } catch {
    return false;
  }
}

/**
 * List all worktrees for a repository
 * Returns array of {path, branch} objects
 */
export async function listWorktrees(repoPath: string): Promise<Array<{path: string, branch: string}>> {
  try {
    const { stdout } = await execFileAsync('git', ['-C', repoPath, 'worktree', 'list', '--porcelain'], {
      timeout: 10000,
    });

    const worktrees: Array<{path: string, branch: string}> = [];
    let currentPath = '';

    for (const line of stdout.split('\n')) {
      if (line.startsWith('worktree ')) {
        currentPath = line.substring(9);
      } else if (line.startsWith('branch ')) {
        const branch = line.substring(7).replace('refs/heads/', '');
        if (currentPath) {
          worktrees.push({ path: currentPath, branch });
        }
      }
    }

    return worktrees;
  } catch {
    return [];
  }
}
```

2. Update `createWorktreeForIssue` to check first:
```typescript
export async function createWorktreeForIssue(
  repoPath: string,
  issueNumber: number,
  isPR: boolean,
  prHeadBranch?: string
): Promise<string> {
  const branchName = isPR ? `pr-${String(issueNumber)}` : `issue-${String(issueNumber)}`;
  const projectName = basename(repoPath);
  const worktreeBase = getWorktreeBase(repoPath);
  const worktreePath = join(worktreeBase, projectName, branchName);

  // Check if worktree already exists (possibly created by skill)
  if (await worktreeExists(worktreePath)) {
    console.log(`[Git] Adopting existing worktree: ${worktreePath}`);
    return worktreePath;
  }

  // ... rest of creation logic unchanged
}
```

**Don't**:
- Don't change behavior if worktree doesn't exist
- Don't validate worktree contents (trust git)

**Verify**: `npm run type-check && npm test`

---

### Task 3: Add branch-based worktree discovery

**Why**: Skill creates worktrees with branch names (e.g., `feature-auth`), not issue numbers. App should discover these.

**Do**:

1. Add to `src/utils/git.ts`:
```typescript
/**
 * Find an existing worktree by branch name pattern
 * Useful for discovering skill-created worktrees
 */
export async function findWorktreeByBranch(
  repoPath: string,
  branchPattern: string
): Promise<string | null> {
  const worktrees = await listWorktrees(repoPath);

  // Exact match first
  const exact = worktrees.find(wt => wt.branch === branchPattern);
  if (exact) return exact.path;

  // Partial match (e.g., "issue-42" matches "issue-42-fix-login")
  const partial = worktrees.find(wt =>
    wt.branch.includes(branchPattern) || branchPattern.includes(wt.branch)
  );
  if (partial) return partial.path;

  return null;
}
```

2. Update `src/adapters/github.ts` to check for existing worktrees:
```typescript
// In handleWebhook, before creating worktree (around line 549)
if (isNewConversation) {
  // First, check if worktree already exists at expected path
  const branchName = isPR ? `pr-${String(number)}` : `issue-${String(number)}`;

  // Also check for skill-created worktrees with the PR's actual branch
  let existingWorktree: string | null = null;
  if (isPR && prHeadBranch) {
    existingWorktree = await findWorktreeByBranch(repoPath, prHeadBranch);
    if (existingWorktree) {
      console.log(`[GitHub] Found existing worktree for branch ${prHeadBranch}: ${existingWorktree}`);
    }
  }

  if (existingWorktree) {
    worktreePath = existingWorktree;
    await db.updateConversation(existingConv.id, {
      codebase_id: codebase.id,
      cwd: worktreePath,
      worktree_path: worktreePath,
    });
  } else {
    // ... existing worktree creation logic
  }
}
```

**Don't**:
- Don't modify skill-created worktrees
- Don't rename or move existing worktrees

**Verify**: `npm run type-check && npm test`

---

### Task 4: Add /worktree orphans command

**Why**: Help users discover worktrees that exist but aren't tracked, or vice versa.

**Mirror**: `src/handlers/command-handler.ts:880-1020` (existing /worktree commands)

**Do**:

Add new subcommand in command-handler.ts:
```typescript
case 'orphans': {
  if (!conversation.codebase_id) {
    return { success: false, message: 'No codebase configured.' };
  }
  const codebase = await codebaseDb.getCodebase(conversation.codebase_id);
  if (!codebase) {
    return { success: false, message: 'Codebase not found.' };
  }

  // Get all worktrees from git
  const gitWorktrees = await listWorktrees(codebase.default_cwd);

  // Get all conversations with worktree_path for this codebase
  // (Would need a new DB query - or simplify to just show git worktrees)

  let msg = 'Worktrees (from git):\n\n';
  for (const wt of gitWorktrees) {
    const isMainRepo = wt.path === codebase.default_cwd;
    if (isMainRepo) continue;

    const shortPath = shortenPath(wt.path, codebase.default_cwd);
    msg += `  ${wt.branch} → ${shortPath}\n`;
  }

  if (gitWorktrees.length <= 1) {
    msg = 'No worktrees found (only main repo).';
  }

  msg += '\nUse /worktree create <branch> to create a new worktree.';

  return { success: true, message: msg };
}
```

**Don't**:
- Don't auto-cleanup orphans (too dangerous)
- Don't modify existing worktrees

**Verify**: `npm run type-check && npm test`

---

### Task 5: Update documentation

**Why**: Users need to know how to configure symbiosis.

**Do**:

1. Update `CLAUDE.md` - add new section:
```markdown
### Worktree Symbiosis (Skill + App)

The app can work alongside the worktree-manager Claude Code skill. To enable:

1. Set `WORKTREE_BASE` to match the skill's `worktreeBase` config:
   ```env
   WORKTREE_BASE=~/tmp/worktrees
   ```

2. Both systems will use the same directory:
   - Skill creates: `~/tmp/worktrees/<project>/<branch-slug>/`
   - App creates: `~/tmp/worktrees/<project>/<issue|pr>-<number>/`

3. The app will adopt skill-created worktrees when:
   - A PR is opened for a branch that already has a worktree
   - The worktree path matches what the app would create

4. Use `/worktree orphans` to see all worktrees (from git perspective)

**Note**: Each system maintains its own metadata:
- Skill: `~/.claude/worktree-registry.json`
- App: Database (`conversations.worktree_path`)

Git (`git worktree list`) is the source of truth for what actually exists.
```

2. Update `.env.example` with full documentation (see Task 1)

**Verify**: Read the docs, ensure they're clear

---

### Task 6: Add tests

**Why**: Ensure worktree discovery and adoption work correctly.

**Mirror**: `src/utils/git.test.ts` (existing git util tests)

**Do**:

Add to `src/utils/git.test.ts`:
```typescript
describe('worktreeExists', () => {
  it('returns true for existing worktree', async () => {
    // Mock fs access to succeed
    jest.spyOn(fs, 'access').mockResolvedValue(undefined);

    const result = await worktreeExists('/path/to/worktree');
    expect(result).toBe(true);
  });

  it('returns false for non-existent path', async () => {
    jest.spyOn(fs, 'access').mockRejectedValue(new Error('ENOENT'));

    const result = await worktreeExists('/nonexistent');
    expect(result).toBe(false);
  });
});

describe('listWorktrees', () => {
  it('parses git worktree list output', async () => {
    const mockOutput = `worktree /path/to/main
HEAD abc123
branch refs/heads/main

worktree /path/to/feature
HEAD def456
branch refs/heads/feature/auth
`;

    mockExecFile.mockImplementation((cmd, args, opts, callback) => {
      callback(null, { stdout: mockOutput, stderr: '' });
    });

    const result = await listWorktrees('/path/to/main');

    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({ path: '/path/to/main', branch: 'main' });
    expect(result[1]).toEqual({ path: '/path/to/feature', branch: 'feature/auth' });
  });
});

describe('findWorktreeByBranch', () => {
  it('finds exact branch match', async () => {
    // Setup mock to return worktrees
    // ... test implementation
  });

  it('returns null when no match', async () => {
    // ... test implementation
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
| `src/utils/git.test.ts` | `worktreeExists returns true for existing` | Basic existence check |
| `src/utils/git.test.ts` | `worktreeExists returns false for missing` | Handles missing path |
| `src/utils/git.test.ts` | `listWorktrees parses porcelain output` | Git output parsing |
| `src/utils/git.test.ts` | `findWorktreeByBranch exact match` | Branch discovery |
| `src/utils/git.test.ts` | `findWorktreeByBranch partial match` | Fuzzy branch matching |
| `src/utils/git.test.ts` | `getWorktreeBase uses env var` | Config override |
| `src/utils/git.test.ts` | `getWorktreeBase expands tilde` | Home dir expansion |

### Manual/E2E Validation

```bash
# 1. Set up shared directory
export WORKTREE_BASE=~/tmp/worktrees

# 2. Create worktree via skill (simulated)
mkdir -p ~/tmp/worktrees/test-repo/feature-auth
cd ~/tmp/worktrees/test-repo/feature-auth
git init  # (or proper worktree setup)

# 3. Start app
npm run dev

# 4. Trigger GitHub webhook for PR with branch 'feature-auth'
# App should adopt existing worktree instead of creating new

# 5. Verify via /worktree orphans command
curl -X POST http://localhost:3000/test/message \
  -H "Content-Type: application/json" \
  -d '{"conversationId":"test","message":"/worktree orphans"}'
```

### Edge Cases
- [ ] WORKTREE_BASE not set → uses default (backward compatible)
- [ ] WORKTREE_BASE with ~ → expands to home directory
- [ ] Worktree exists but is corrupted → git commands fail gracefully
- [ ] Multiple worktrees for same branch → uses first found
- [ ] Skill and app create worktrees simultaneously → no race condition (git handles)

### Regression Check
- [ ] Existing GitHub issue/PR workflow still works
- [ ] `/worktree create` still works
- [ ] `/worktree remove` still works
- [ ] Worktree cleanup on issue close still works

## Risks

1. **Path expansion edge cases**: `~` expansion may not work on all systems
   - Mitigation: Use `os.homedir()` from Node.js instead of string replacement

2. **Git worktree list format changes**: Porcelain format should be stable but could change
   - Mitigation: Use `--porcelain` flag which is designed for scripting

3. **Race conditions**: Skill and app creating worktrees simultaneously
   - Mitigation: Git itself handles this - second create will fail, check handles it

4. **Stale metadata**: Skill JSON and app DB can get out of sync with actual disk state
   - Mitigation: Document that git is source of truth, add `/worktree orphans` command

## Summary

This plan enables skill-app worktree symbiosis through:

1. **Shared configurable base directory** (`WORKTREE_BASE` env var)
2. **Worktree discovery** before creation (adopt existing)
3. **Branch-based lookup** for skill-created worktrees
4. **Orphan detection** command for visibility
5. **Git as source of truth** - both systems query git, not each other

The systems remain independent but can cooperate when configured to share a directory.
