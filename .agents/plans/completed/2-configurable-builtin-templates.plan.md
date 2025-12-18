# Plan: Configurable Builtin Command Templates

## Summary

Add an environment variable `LOAD_BUILTIN_COMMANDS` to control whether the repo's maintained workflow commands (plan, implement, commit, review-pr, etc.) are seeded into the database on startup. Default is `true` so new users get the commands out-of-the-box, but users can set `false` to start with a clean slate or use only their own custom templates.

### Naming Decision

**Chosen: `LOAD_BUILTIN_COMMANDS=true|false`**

Rationale:
- "builtin" is standard terminology (Python builtins, shell builtins, VS Code builtin extensions)
- Clearly conveys these ship WITH the software
- Doesn't require knowledge of "PIV" methodology for new users
- Short and memorable

Alternatives considered:
- `SEED_DEFAULT_TEMPLATES` - Too generic, doesn't convey they're maintained
- `LOAD_MAINTAINED_PIV_COMMANDS` - "PIV" not obvious to all users
- `ENABLE_WORKFLOW_TEMPLATES` - Vague about what workflows

The documentation will clarify these are "maintained by the repo maintainers and updated with new releases."

## Patterns to Mirror

### Environment Variable Pattern
```typescript
// FROM: src/index.ts:65
const maxConcurrent = parseInt(process.env.MAX_CONCURRENT_CONVERSATIONS ?? '10');
```

### Boolean Env Var Pattern
```typescript
// FROM: src/index.ts:34-36
const hasClaudeCredentials = Boolean(
  process.env.CLAUDE_API_KEY || process.env.CLAUDE_CODE_OAUTH_TOKEN
);
```

### .env.example Documentation Pattern
```bash
# FROM: .env.example:19-21
# Default AI Assistant (claude | codex)
# Used for new conversations when no codebase specified
DEFAULT_AI_ASSISTANT=claude
```

## Files to Change

| File | Action | Justification |
|------|--------|---------------|
| `src/scripts/seed-commands.ts` | UPDATE | Add env var check before seeding |
| `.env.example` | UPDATE | Document the new env var |
| `CLAUDE.md` | UPDATE | Document the feature in project docs |

## NOT Building

- ❌ `force` option to re-seed (can use `/template-add` or restart with empty DB)
- ❌ Custom path configuration (users can fork and modify SEED_COMMANDS_PATH)
- ❌ Per-command enable/disable (too complex, all-or-nothing is simpler)
- ❌ CLI flag alternative (env var is sufficient for Docker/production)

## Tasks

### Task 1: Update seed-commands.ts to check env var

**Why**: Core feature - respect user's preference for builtin commands

**Mirror**: `src/index.ts:65` (env var with default)

**Do**:
```typescript
export async function seedDefaultCommands(): Promise<void> {
  // Check if builtin commands should be loaded (default: true)
  const loadBuiltins = process.env.LOAD_BUILTIN_COMMANDS !== 'false';

  if (!loadBuiltins) {
    console.log('[Seed] Builtin commands disabled (LOAD_BUILTIN_COMMANDS=false)');
    return;
  }

  console.log('[Seed] Loading builtin command templates...');
  // ... rest of existing code
}
```

**Don't**:
- Don't use `=== 'true'` (we want true as default, only explicit 'false' disables)
- Don't add complex parsing (simple string comparison is enough)

**Verify**: `npm run type-check`

### Task 2: Update .env.example with new variable

**Why**: Users need to discover and understand the option

**Mirror**: `.env.example:19-21` (comment + variable pattern)

**Do**:
Add after the `MAX_CONCURRENT_CONVERSATIONS` line:

```bash
# Builtin Command Templates
# Set to 'false' to disable loading the maintained workflow commands
# (plan, implement, commit, review-pr, etc.) that ship with this repo.
# These are updated by the repo maintainers with each release.
LOAD_BUILTIN_COMMANDS=true  # true (default) | false
```

**Verify**: Visual inspection

### Task 3: Update CLAUDE.md documentation

**Why**: Project documentation should explain the feature

**Do**:
Add to the Configuration > Environment Variables section:

```markdown
# Builtin Commands (default: true)
LOAD_BUILTIN_COMMANDS=true  # Load maintained workflow templates on startup
```

And add a new section explaining builtin commands:

```markdown
### Builtin Command Templates

The repo ships with maintained workflow commands in `.claude/commands/exp-piv-loop/`:
- `/plan` - Deep implementation planning
- `/implement` - Execute implementation plans
- `/commit` - Quick commits with natural language targeting
- `/review-pr` - Comprehensive PR code review
- `/create-pr`, `/merge-pr` - PR lifecycle
- `/rca`, `/fix-rca` - Root cause analysis workflow
- `/prd` - Product requirements documents
- `/worktree` - Parallel branch development

These are loaded as global templates on startup (controlled by `LOAD_BUILTIN_COMMANDS`).
To disable: `LOAD_BUILTIN_COMMANDS=false`
```

**Verify**: Visual inspection

### Task 4: Update seed log messages for clarity

**Why**: Logs should clearly indicate what's happening

**Do**:
Update the log messages in seed-commands.ts:

```typescript
// When loading
console.log('[Seed] Loading builtin command templates...');
console.log(`[Seed] Loaded builtin template: ${name}`);
console.log(`[Seed] Loaded ${String(mdFiles.length)} builtin command templates`);

// When disabled
console.log('[Seed] Builtin commands disabled (LOAD_BUILTIN_COMMANDS=false)');

// When files not found (keep existing)
console.log('[Seed] No builtin commands found (this is OK for external-db deployments)');
```

**Verify**: `npm run build`

## Validation Strategy

### Automated Checks
- [ ] `npm run type-check` - Types valid
- [ ] `npm run lint` - No lint errors
- [ ] `npm run build` - Build succeeds

### Manual Validation

**Test 1: Default behavior (LOAD_BUILTIN_COMMANDS not set)**
```bash
# Remove any existing templates
docker-compose --profile with-db exec postgres psql -U postgres -d remote_coding_agent \
  -c "DELETE FROM remote_agent_command_templates"

# Restart app (without env var set)
docker-compose --profile with-db restart app-with-db

# Check logs - should see "Loading builtin command templates..."
docker-compose --profile with-db logs app-with-db | grep -i seed

# Verify templates loaded
docker-compose --profile with-db exec postgres psql -U postgres -d remote_coding_agent \
  -c "SELECT COUNT(*) FROM remote_agent_command_templates"
# Expected: 10 (or however many are in exp-piv-loop)
```

**Test 2: Explicitly disabled (LOAD_BUILTIN_COMMANDS=false)**
```bash
# Clear templates
docker-compose --profile with-db exec postgres psql -U postgres -d remote_coding_agent \
  -c "DELETE FROM remote_agent_command_templates"

# Add env var to docker-compose or .env
# LOAD_BUILTIN_COMMANDS=false

# Restart
docker-compose --profile with-db restart app-with-db

# Check logs - should see "Builtin commands disabled"
docker-compose --profile with-db logs app-with-db | grep -i seed

# Verify NO templates loaded
docker-compose --profile with-db exec postgres psql -U postgres -d remote_coding_agent \
  -c "SELECT COUNT(*) FROM remote_agent_command_templates"
# Expected: 0
```

**Test 3: Explicitly enabled (LOAD_BUILTIN_COMMANDS=true)**
```bash
# Same as Test 1 but with explicit LOAD_BUILTIN_COMMANDS=true
# Should behave identically to default
```

### Edge Cases
- [ ] Empty string `LOAD_BUILTIN_COMMANDS=` should default to true (not disabled)
- [ ] Case sensitivity: `LOAD_BUILTIN_COMMANDS=FALSE` - decide if we want case-insensitive
- [ ] Existing templates: Verify upsert doesn't duplicate (already handled by upsertTemplate)

### Regression Check
- [ ] Existing `/templates` command still works
- [ ] Existing `/template-add` command still works
- [ ] Direct template invocation (`/plan "feature"`) still works

## Risks

1. **Breaking change for existing users**: None - default is `true`, same as current behavior
2. **Docker env var propagation**: Ensure docker-compose.yml passes the env var correctly (already has `env_file: .env`)
