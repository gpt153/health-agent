# Plan: Global Command Templates

## Summary

Add a `remote_agent_command_templates` database table to store reusable command prompts that work across all projects. Users can load any markdown file into this table with a custom name, invoke commands with simpler syntax (`/plan "feature"` instead of `/command-invoke plan "feature"`), and the existing `$ARGUMENTS`, `$1`, `$2` variable substitution works unchanged. The `exp-piv-loop` commands are seeded as defaults on app startup.

## External Research

### Documentation
- PostgreSQL TEXT type - ideal for storing markdown content (no length limit)
- Node.js `pg` library patterns - already used in codebase

### Gotchas & Best Practices
- Use TEXT not VARCHAR for command content (markdown can be large)
- Seed data should be idempotent (INSERT ... ON CONFLICT DO NOTHING)
- Command lookup priority: codebase-specific > global templates (user expectation)

## Patterns to Mirror

### Database Schema Pattern
**FROM: `migrations/001_initial_schema.sql:6-15`**
```sql
CREATE TABLE remote_agent_codebases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  repository_url VARCHAR(500),
  default_cwd VARCHAR(500) NOT NULL,
  ai_assistant_type VARCHAR(20) DEFAULT 'claude',
  commands JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### Database Operations Pattern
**FROM: `src/db/codebases.ts:7-19`**
```typescript
export async function createCodebase(data: {
  name: string;
  repository_url?: string;
  default_cwd: string;
  ai_assistant_type?: string;
}): Promise<Codebase> {
  const assistantType = data.ai_assistant_type ?? 'claude';
  const result = await pool.query<Codebase>(
    'INSERT INTO remote_agent_codebases (name, repository_url, default_cwd, ai_assistant_type) VALUES ($1, $2, $3, $4) RETURNING *',
    [data.name, data.repository_url ?? null, data.default_cwd, assistantType]
  );
  return result.rows[0];
}
```

### Command Handler Pattern
**FROM: `src/handlers/command-handler.ts:77-101`**
```typescript
switch (command) {
  case 'help':
    return {
      success: true,
      message: `Available Commands:...`,
    };
  // ... more cases
}
```

### Test Pattern
**FROM: `src/db/codebases.test.ts:38-54`**
```typescript
describe('createCodebase', () => {
  test('creates codebase with all fields', async () => {
    mockQuery.mockResolvedValueOnce(createQueryResult([mockCodebase]));

    const result = await createCodebase({...});

    expect(result).toEqual(mockCodebase);
    expect(mockQuery).toHaveBeenCalledWith(
      'INSERT INTO ...',
      [...]
    );
  });
});
```

## Files to Change

| File | Action | Justification |
|------|--------|---------------|
| `migrations/002_command_templates.sql` | CREATE | New table schema |
| `src/types/index.ts` | UPDATE | Add CommandTemplate interface |
| `src/db/command-templates.ts` | CREATE | Database operations for templates |
| `src/db/command-templates.test.ts` | CREATE | Unit tests for DB operations |
| `src/handlers/command-handler.ts` | UPDATE | Add `/template-add`, `/template-list`, `/template-delete` commands |
| `src/handlers/command-handler.test.ts` | UPDATE | Tests for new commands |
| `src/orchestrator/orchestrator.ts` | UPDATE | Support direct command invocation (`/plan` → lookup template) |
| `src/orchestrator/orchestrator.test.ts` | UPDATE | Tests for template invocation |
| `src/scripts/seed-commands.ts` | CREATE | Seed exp-piv-loop commands on startup |
| `src/index.ts` | UPDATE | Call seed function on startup |

## NOT Building

- ❌ Command versioning/history (not needed for MVP)
- ❌ Command categories/tags (simple flat list is fine)
- ❌ Import/export to files (manual `/template-add` is sufficient)
- ❌ Per-user templates (single-developer tool)
- ❌ Template validation (user responsibility)

## Tasks

### Task 1: CREATE migration file `migrations/002_command_templates.sql`

**Why**: Need database table to store command templates

**Mirror**: `migrations/001_initial_schema.sql:6-15`

**Do**:
```sql
-- Remote Coding Agent - Command Templates
-- Version: 2.0
-- Description: Global command templates table

CREATE TABLE remote_agent_command_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL UNIQUE,
  description TEXT,
  content TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_remote_agent_command_templates_name ON remote_agent_command_templates(name);
```

**Don't**:
- Don't add foreign keys (templates are global, not per-codebase)
- Don't add argument_hint column (extract from frontmatter at runtime)

**Verify**: `psql $DATABASE_URL -c "\d remote_agent_command_templates"`

---

### Task 2: UPDATE `src/types/index.ts` - Add CommandTemplate interface

**Why**: Type safety for template operations

**Mirror**: `src/types/index.ts:5-14` (Conversation interface)

**Do**:
```typescript
export interface CommandTemplate {
  id: string;
  name: string;
  description: string | null;
  content: string;
  created_at: Date;
  updated_at: Date;
}
```

Add after the `Session` interface (around line 37).

**Don't**:
- Don't add optional fields that aren't in the schema

**Verify**: `npm run type-check`

---

### Task 3: CREATE `src/db/command-templates.ts`

**Why**: Database operations for command templates

**Mirror**: `src/db/codebases.ts` (entire file structure)

**Do**:
```typescript
/**
 * Database operations for command templates
 */
import { pool } from './connection';
import { CommandTemplate } from '../types';

export async function createTemplate(data: {
  name: string;
  description?: string;
  content: string;
}): Promise<CommandTemplate> {
  const result = await pool.query<CommandTemplate>(
    'INSERT INTO remote_agent_command_templates (name, description, content) VALUES ($1, $2, $3) RETURNING *',
    [data.name, data.description ?? null, data.content]
  );
  return result.rows[0];
}

export async function getTemplate(name: string): Promise<CommandTemplate | null> {
  const result = await pool.query<CommandTemplate>(
    'SELECT * FROM remote_agent_command_templates WHERE name = $1',
    [name]
  );
  return result.rows[0] || null;
}

export async function getAllTemplates(): Promise<CommandTemplate[]> {
  const result = await pool.query<CommandTemplate>(
    'SELECT * FROM remote_agent_command_templates ORDER BY name'
  );
  return result.rows;
}

export async function deleteTemplate(name: string): Promise<boolean> {
  const result = await pool.query(
    'DELETE FROM remote_agent_command_templates WHERE name = $1',
    [name]
  );
  return (result.rowCount ?? 0) > 0;
}

export async function upsertTemplate(data: {
  name: string;
  description?: string;
  content: string;
}): Promise<CommandTemplate> {
  const result = await pool.query<CommandTemplate>(
    `INSERT INTO remote_agent_command_templates (name, description, content)
     VALUES ($1, $2, $3)
     ON CONFLICT (name) DO UPDATE SET
       description = EXCLUDED.description,
       content = EXCLUDED.content,
       updated_at = NOW()
     RETURNING *`,
    [data.name, data.description ?? null, data.content]
  );
  return result.rows[0];
}
```

**Don't**:
- Don't add codebase_id - templates are global

**Verify**: `npm run type-check`

---

### Task 4: CREATE `src/db/command-templates.test.ts`

**Why**: Unit tests for template database operations

**Mirror**: `src/db/codebases.test.ts` (entire file structure)

**Do**:
```typescript
import { createQueryResult } from '../test/mocks/database';
import { CommandTemplate } from '../types';

const mockQuery = jest.fn();

jest.mock('./connection', () => ({
  pool: {
    query: mockQuery,
  },
}));

import {
  createTemplate,
  getTemplate,
  getAllTemplates,
  deleteTemplate,
  upsertTemplate,
} from './command-templates';

describe('command-templates', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const mockTemplate: CommandTemplate = {
    id: 'template-123',
    name: 'plan',
    description: 'Create implementation plan',
    content: '# Plan\n\n**Input**: $ARGUMENTS',
    created_at: new Date(),
    updated_at: new Date(),
  };

  describe('createTemplate', () => {
    test('creates template with all fields', async () => {
      mockQuery.mockResolvedValueOnce(createQueryResult([mockTemplate]));

      const result = await createTemplate({
        name: 'plan',
        description: 'Create implementation plan',
        content: '# Plan\n\n**Input**: $ARGUMENTS',
      });

      expect(result).toEqual(mockTemplate);
      expect(mockQuery).toHaveBeenCalledWith(
        'INSERT INTO remote_agent_command_templates (name, description, content) VALUES ($1, $2, $3) RETURNING *',
        ['plan', 'Create implementation plan', '# Plan\n\n**Input**: $ARGUMENTS']
      );
    });

    test('creates template without description', async () => {
      const templateWithoutDesc = { ...mockTemplate, description: null };
      mockQuery.mockResolvedValueOnce(createQueryResult([templateWithoutDesc]));

      await createTemplate({
        name: 'plan',
        content: '# Plan',
      });

      expect(mockQuery).toHaveBeenCalledWith(
        expect.any(String),
        ['plan', null, '# Plan']
      );
    });
  });

  describe('getTemplate', () => {
    test('returns existing template', async () => {
      mockQuery.mockResolvedValueOnce(createQueryResult([mockTemplate]));

      const result = await getTemplate('plan');

      expect(result).toEqual(mockTemplate);
      expect(mockQuery).toHaveBeenCalledWith(
        'SELECT * FROM remote_agent_command_templates WHERE name = $1',
        ['plan']
      );
    });

    test('returns null for non-existent template', async () => {
      mockQuery.mockResolvedValueOnce(createQueryResult([]));

      const result = await getTemplate('non-existent');

      expect(result).toBeNull();
    });
  });

  describe('getAllTemplates', () => {
    test('returns all templates ordered by name', async () => {
      const templates = [mockTemplate, { ...mockTemplate, id: 'template-456', name: 'commit' }];
      mockQuery.mockResolvedValueOnce(createQueryResult(templates));

      const result = await getAllTemplates();

      expect(result).toEqual(templates);
      expect(mockQuery).toHaveBeenCalledWith(
        'SELECT * FROM remote_agent_command_templates ORDER BY name'
      );
    });

    test('returns empty array when no templates', async () => {
      mockQuery.mockResolvedValueOnce(createQueryResult([]));

      const result = await getAllTemplates();

      expect(result).toEqual([]);
    });
  });

  describe('deleteTemplate', () => {
    test('returns true when template deleted', async () => {
      mockQuery.mockResolvedValueOnce(createQueryResult([], 1));

      const result = await deleteTemplate('plan');

      expect(result).toBe(true);
      expect(mockQuery).toHaveBeenCalledWith(
        'DELETE FROM remote_agent_command_templates WHERE name = $1',
        ['plan']
      );
    });

    test('returns false when template not found', async () => {
      mockQuery.mockResolvedValueOnce(createQueryResult([], 0));

      const result = await deleteTemplate('non-existent');

      expect(result).toBe(false);
    });
  });

  describe('upsertTemplate', () => {
    test('inserts new template', async () => {
      mockQuery.mockResolvedValueOnce(createQueryResult([mockTemplate]));

      const result = await upsertTemplate({
        name: 'plan',
        description: 'Create implementation plan',
        content: '# Plan',
      });

      expect(result).toEqual(mockTemplate);
      expect(mockQuery).toHaveBeenCalledWith(
        expect.stringContaining('ON CONFLICT'),
        ['plan', 'Create implementation plan', '# Plan']
      );
    });
  });
});
```

**Verify**: `npm test -- src/db/command-templates.test.ts`

---

### Task 5: CREATE `src/scripts/seed-commands.ts`

**Why**: Seed exp-piv-loop commands as defaults on startup

**Mirror**: N/A (new pattern, but uses existing db operations)

**Do**:
```typescript
/**
 * Seed default command templates from .claude/commands/exp-piv-loop
 */
import { readFile, readdir } from 'fs/promises';
import { join, basename } from 'path';
import { upsertTemplate } from '../db/command-templates';

const SEED_COMMANDS_PATH = '.claude/commands/exp-piv-loop';

/**
 * Extract description from markdown frontmatter
 * ---
 * description: Some description
 * ---
 */
function extractDescription(content: string): string | undefined {
  const frontmatterMatch = content.match(/^---\n([\s\S]*?)\n---/);
  if (!frontmatterMatch) return undefined;

  const frontmatter = frontmatterMatch[1];
  const descMatch = frontmatter.match(/description:\s*(.+)/);
  return descMatch?.[1]?.trim();
}

export async function seedDefaultCommands(): Promise<void> {
  console.log('[Seed] Checking for default command templates...');

  try {
    const files = await readdir(SEED_COMMANDS_PATH);
    const mdFiles = files.filter(f => f.endsWith('.md'));

    for (const file of mdFiles) {
      const name = basename(file, '.md');
      const filePath = join(SEED_COMMANDS_PATH, file);
      const content = await readFile(filePath, 'utf-8');
      const description = extractDescription(content);

      await upsertTemplate({
        name,
        description: description ?? `From ${SEED_COMMANDS_PATH}`,
        content,
      });

      console.log(`[Seed] Loaded template: ${name}`);
    }

    console.log(`[Seed] Seeded ${String(mdFiles.length)} default command templates`);
  } catch (error) {
    // Don't fail startup if seed commands don't exist
    console.log('[Seed] No default commands to seed (this is OK)');
  }
}
```

**Don't**:
- Don't fail app startup if seed files don't exist
- Don't overwrite user modifications (upsert handles this gracefully)

**Verify**: `npm run type-check`

---

### Task 6: UPDATE `src/handlers/command-handler.ts` - Add template commands

**Why**: Users need to manage templates via slash commands

**Mirror**: `src/handlers/command-handler.ts:77-101` (switch cases)

**Do**:

Add imports at top:
```typescript
import * as templateDb from '../db/command-templates';
```

Add new cases in the switch statement (before `default:`):

```typescript
    case 'template-add': {
      if (args.length < 2) {
        return { success: false, message: 'Usage: /template-add <name> <file-path>' };
      }
      if (!conversation.cwd) {
        return { success: false, message: 'No working directory set. Use /clone or /setcwd first.' };
      }

      const [templateName, ...pathParts] = args;
      const filePath = pathParts.join(' ');
      const fullPath = resolve(conversation.cwd, filePath);

      try {
        const content = await readFile(fullPath, 'utf-8');

        // Extract description from frontmatter if present
        const frontmatterMatch = content.match(/^---\n([\s\S]*?)\n---/);
        let description: string | undefined;
        if (frontmatterMatch) {
          const descMatch = frontmatterMatch[1].match(/description:\s*(.+)/);
          description = descMatch?.[1]?.trim();
        }

        await templateDb.upsertTemplate({
          name: templateName,
          description: description ?? `From ${filePath}`,
          content,
        });

        return {
          success: true,
          message: `Template '${templateName}' saved!\n\nUse it with: /${templateName} [args]`,
        };
      } catch (error) {
        const err = error as Error;
        return { success: false, message: `Failed to read file: ${err.message}` };
      }
    }

    case 'template-list':
    case 'templates': {
      const templates = await templateDb.getAllTemplates();

      if (templates.length === 0) {
        return {
          success: true,
          message: 'No command templates registered.\n\nUse /template-add <name> <file-path> to add one.',
        };
      }

      let msg = 'Command Templates:\n\n';
      for (const t of templates) {
        msg += `/${t.name}`;
        if (t.description) {
          msg += ` - ${t.description}`;
        }
        msg += '\n';
      }
      msg += '\nUse /<name> [args] to invoke any template.';
      return { success: true, message: msg };
    }

    case 'template-delete': {
      if (args.length < 1) {
        return { success: false, message: 'Usage: /template-delete <name>' };
      }

      const deleted = await templateDb.deleteTemplate(args[0]);
      if (deleted) {
        return { success: true, message: `Template '${args[0]}' deleted.` };
      }
      return { success: false, message: `Template '${args[0]}' not found.` };
    }
```

Update the `/help` message to include template commands:
```typescript
    case 'help':
      return {
        success: true,
        message: `Available Commands:

Command Templates:
  /<name> [args] - Invoke a template directly
  /templates - List all templates
  /template-add <name> <path> - Add template from file
  /template-delete <name> - Remove a template

Command Management:
  /command-set <name> <path> [text] - Register codebase command
  /load-commands <folder> - Bulk load (recursive)
  /command-invoke <name> [args] - Execute codebase command
  /commands - List codebase commands

Codebase:
  /clone <repo-url> - Clone repository
  /repos - List workspace repositories
  /getcwd - Show working directory
  /setcwd <path> - Set directory

Session:
  /status - Show state
  /reset - Clear session
  /help - Show help`,
      };
```

**Don't**:
- Don't require codebase for template commands (templates are global)

**Verify**: `npm run type-check && npm test -- src/handlers/command-handler.test.ts`

---

### Task 7: UPDATE `src/orchestrator/orchestrator.ts` - Support direct template invocation

**Why**: Allow `/plan "feature"` instead of `/command-invoke plan "feature"`

**Mirror**: `src/orchestrator/orchestrator.ts:29-46` (slash command routing)

**Do**:

Add import at top:
```typescript
import * as templateDb from '../db/command-templates';
```

Modify the slash command routing section (after line 29, before the `/command-invoke` check):

```typescript
    // Handle slash commands (except /command-invoke which needs AI)
    if (message.startsWith('/')) {
      const { command, args } = commandHandler.parseCommand(message);

      // Check if this is a known deterministic command
      const deterministicCommands = [
        'help', 'status', 'getcwd', 'setcwd', 'clone', 'repos', 'reset',
        'command-set', 'load-commands', 'commands',
        'template-add', 'template-list', 'templates', 'template-delete'
      ];

      if (deterministicCommands.includes(command)) {
        console.log(`[Orchestrator] Processing slash command: ${message}`);
        const result = await commandHandler.handleCommand(conversation, message);
        await platform.sendMessage(conversationId, result.message);

        if (result.modified) {
          conversation = await db.getOrCreateConversation(
            platform.getPlatformType(),
            conversationId
          );
        }
        return;
      }

      // Check if it's /command-invoke (codebase-specific)
      if (command === 'command-invoke') {
        // ... existing command-invoke logic (keep as-is)
      }

      // Check if it's a global template command
      const template = await templateDb.getTemplate(command);
      if (template) {
        console.log(`[Orchestrator] Found template: ${command}`);
        commandName = command;
        promptToSend = substituteVariables(template.content, args);

        if (issueContext) {
          promptToSend = promptToSend + '\n\n---\n\n' + issueContext;
          console.log('[Orchestrator] Appended issue/PR context to template prompt');
        }

        console.log(`[Orchestrator] Executing template '${command}' with ${String(args.length)} args`);
        // Fall through to AI handling below
      } else {
        // Unknown command
        await platform.sendMessage(
          conversationId,
          `Unknown command: /${command}\n\nType /help for available commands or /templates for command templates.`
        );
        return;
      }
    }
```

**Important**: The template invocation path needs to skip the codebase requirement check since templates are global. The AI conversation section should work since it only needs `conversation.cwd` which can default to workspace.

Also update the "no codebase" check to allow template commands:
```typescript
    // Regular message - require codebase (but templates don't need it)
    if (!conversation.codebase_id && !commandName) {
      await platform.sendMessage(conversationId, 'No codebase configured. Use /clone first.');
      return;
    }
```

**Don't**:
- Don't break existing `/command-invoke` flow
- Don't require codebase for template commands

**Verify**: `npm run type-check`

---

### Task 8: UPDATE `src/index.ts` - Call seed on startup

**Why**: Seed default templates when app starts

**Mirror**: `src/index.ts:51-57` (database connection check pattern)

**Do**:

Add import at top:
```typescript
import { seedDefaultCommands } from './scripts/seed-commands';
```

Add after database connection check (around line 57):
```typescript
  // Seed default command templates
  await seedDefaultCommands();
```

**Don't**:
- Don't block startup if seeding fails

**Verify**: `npm run dev` - should see seed logs

---

### Task 9: Run migration

**Why**: Create the new table in the database

**Do**:
```bash
psql $DATABASE_URL < migrations/002_command_templates.sql
```

**Verify**: `psql $DATABASE_URL -c "SELECT COUNT(*) FROM remote_agent_command_templates"`

---

## Validation Strategy

### Automated Checks
- [ ] `npm run type-check` - Types valid
- [ ] `npm run lint` - No lint errors
- [ ] `npm run test` - All tests pass
- [ ] `npm run build` - Build succeeds

### New Tests to Write
| Test File | Test Case | What It Validates |
|-----------|-----------|-------------------|
| `src/db/command-templates.test.ts` | All CRUD operations | Database layer works |
| `src/handlers/command-handler.test.ts` | `/template-add`, `/template-list`, `/template-delete` | Command handler works |
| `src/orchestrator/orchestrator.test.ts` | Direct template invocation (`/plan "feature"`) | Template routing works |

### Manual/E2E Validation

```bash
# 1. Start the app
npm run dev

# 2. In Telegram, test template commands:
/templates                    # Should show seeded exp-piv-loop commands
/template-add myplan .claude/commands/exp-piv-loop/plan.md
/templates                    # Should show myplan

# 3. Test direct invocation (the key feature!)
/plan "Add user authentication"   # Should work without /command-invoke

# 4. Test template deletion
/template-delete myplan
/templates                    # Should not show myplan
```

### Edge Cases
- [ ] `/plan` with no arguments (should still work, $ARGUMENTS = "")
- [ ] Template with same name as built-in command (built-in should win)
- [ ] Template content with complex markdown and `$1`, `$2`, `$ARGUMENTS`
- [ ] Invoking template without codebase set (should work - templates are global)

### Regression Check
- [ ] `/command-invoke plan "feature"` still works (codebase-specific)
- [ ] `/load-commands` still works
- [ ] `/clone` still works
- [ ] Regular messages still work

## Risks

1. **Template name conflicts**: If user creates template named `help`, it would shadow built-in. Mitigation: Check deterministicCommands list first.

2. **Large templates**: No size limit on content TEXT. Mitigation: Not a real risk for single-developer tool.

3. **Migration on existing DB**: Need to run migration manually. Mitigation: Clear instructions in Task 9.
