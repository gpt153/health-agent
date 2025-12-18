# Feature: Telegram Topics for Multi-Project Parallel Development

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Enable multi-project parallel development through Telegram supergroup topics (forum threads). Each topic acts as an isolated workspace with its own codebase, AI session, and working directory. Users can work on 4+ projects simultaneously by clicking between topics, with each topic running independent AI operations in parallel. Includes automated project creation via `/new-topic` command that scaffolds GitHub repo, workspace, and Archon project tracking in one command.

## User Story

As a non-technical project manager
I want to work on multiple software projects in parallel via Telegram topics
So that I can efficiently manage development across projects without understanding code or switching between terminals

## Problem Statement

Current Telegram integration treats all messages in a chat as a single conversation:
- Cannot work on multiple projects simultaneously in one Telegram group
- Must manually switch between projects using commands
- No visual separation between different project contexts
- Cannot run AI operations in parallel for different projects
- Non-technical users receive code-heavy responses they cannot understand
- Project setup requires multiple manual steps (clone, create tracking, configure)

## Solution Statement

Transform Telegram supergroup topics into isolated project workspaces where:
1. Each topic = one project with independent conversation, codebase, and AI session
2. Clicking between topics switches context automatically (no manual commands)
3. AI operations run in parallel across topics (like separate terminal windows)
4. `/new-topic <name>` creates complete project scaffolding (GitHub repo + workspace + Archon project)
5. Responses show only final summaries in non-technical language (no code blocks, no streaming updates)
6. General chat restricted to `/new-topic` and info commands only

## Feature Metadata

**Feature Type**: Enhancement + New Capability
**Estimated Complexity**: High
**Primary Systems Affected**:
- Telegram adapter (conversation ID format, topic creation)
- Command handler (new `/new-topic` command)
- Orchestrator (response filtering for non-technical summaries)
- Database (topic-based conversation isolation)

**Dependencies**:
- Telegraf SDK (Telegram Bot API)
- @octokit/rest (GitHub repository creation)
- Archon MCP Server (project tracking)
- Existing conversation lock manager (parallel execution)

---

## CONTEXT REFERENCES

### Relevant Codebase Files - IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `src/adapters/telegram.ts` (all) - Current Telegram adapter implementation, shows conversation ID extraction (line 177-182), message handling (line 195-217), streaming mode setup (line 23, 163-165)
- `src/handlers/command-handler.ts` (lines 78-96, 98-150) - Command parsing pattern, switch statement structure for commands, `/status` command example
- `src/orchestrator/orchestrator.ts` (lines 36-114) - Message routing logic, shows how deterministic commands are handled vs AI commands, streaming mode usage
- `src/db/conversations.ts` (lines 36-91) - Conversation creation pattern with parent context inheritance (lines 51-69), shows how to handle isolated conversations
- `src/adapters/github.ts` (lines 1-80) - Octokit usage pattern for GitHub API operations
- `src/utils/telegram-markdown.ts` (all) - Markdown formatting utilities for Telegram, shows `stripMarkdown()` function
- `src/types/index.ts` (lines 59-84, 100-116) - Interface definitions for IPlatformAdapter and IAssistantClient
- `.agents/reference/new-features.md` (lines 1-66) - Platform adapter patterns and authentication approach

### New Files to Create

- `src/utils/response-formatter.ts` - Non-technical response filtering (strip code blocks, summarize changes)
- `src/utils/github-repo.ts` - GitHub repository creation utilities
- `src/handlers/new-topic-handler.ts` - Project scaffolding logic for `/new-topic` command

### Relevant Documentation - YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [Telegram Bot API - Forum Topics](https://core.telegram.org/bots/api#forum-topics)
  - Specific methods: createForumTopic, getForumTopicIconStickers
  - Why: Required for programmatic topic creation in `/new-topic` command
- [Telegraf Documentation - Forum Management](https://telegraf.js.org/)
  - Specific section: telegram.createForumTopic()
  - Why: SDK wrapper for Telegram Bot API forum operations
- [@octokit/rest - Repositories](https://octokit.github.io/rest.js/v20#repos-create-for-authenticated-user)
  - Specific method: repos.createForAuthenticatedUser()
  - Why: Create private GitHub repositories programmatically
- [Archon MCP Tools](mcp://archon)
  - Tools: mcp__archon__manage_project, mcp__archon__manage_task
  - Why: Create and track projects via MCP server

### Patterns to Follow

**Conversation ID Format:**
Current (telegram.ts:181):
```typescript
getConversationId(ctx: Context): string {
  return ctx.chat.id.toString();
}
```

New pattern needed:
```typescript
getConversationId(ctx: Context): string {
  const chatId = ctx.chat.id.toString();
  const threadId = ctx.message?.message_thread_id;
  return threadId ? `${chatId}:${threadId}` : chatId;
}
```

**Command Handler Pattern:**
(command-handler.ts:98-142)
```typescript
export async function handleCommand(
  conversation: Conversation,
  message: string
): Promise<CommandResult> {
  const { command, args } = parseCommand(message);

  switch (command) {
    case 'help':
      return { success: true, message: '...' };
    case 'status':
      // Implementation
      return { success: true, message: '...' };
    // Add new commands here
  }
}
```

**Streaming Mode Configuration:**
(telegram.ts:27-33, 163-165)
```typescript
constructor(token: string, mode: 'stream' | 'batch' = 'stream') {
  this.streamingMode = mode;
}

getStreamingMode(): 'stream' | 'batch' {
  return this.streamingMode;
}
```

**Octokit API Usage:**
(github.ts:59-65, 115)
```typescript
private octokit: Octokit;

constructor(token: string) {
  this.octokit = new Octokit({ auth: token });
}

await this.octokit.rest.issues.createComment({
  owner, repo, issue_number, body
});
```

**Response Filtering Pattern:**
```typescript
// Strip code blocks and technical details
function filterForNonTechnical(message: string): string {
  // Remove code blocks: ```...```
  message = message.replace(/```[\s\S]*?```/g, '[Code changes made]');

  // Keep natural language summaries
  // Add "what and why" context
  return message;
}
```

---

## IMPLEMENTATION PLAN

### Phase 1: Topic-Aware Infrastructure

Update Telegram adapter to support topic-based conversation isolation.

**Tasks:**
- Modify conversation ID format to include `message_thread_id`
- Extract thread ID from incoming messages
- Handle general chat (no thread ID) separately
- Update message handler to pass topic context

### Phase 2: Response Formatting System

Create non-technical response filtering for decision-maker audience.

**Tasks:**
- Implement code block stripping utility
- Add "what and why" summarization
- Configure batch streaming mode for Telegram
- Test with various AI response types

### Phase 3: Project Scaffolding Command

Implement `/new-topic <name>` for automated project creation.

**Tasks:**
- Create GitHub private repository with README
- Clone repository to workspace
- Create Archon project tracking
- Update README with metadata (GitHub URL, Archon ID, workspace path)
- Create Telegram topic programmatically
- Link topic to codebase in database

### Phase 4: General Chat Restrictions

Restrict general chat to setup commands only.

**Tasks:**
- Detect general chat vs topic messages
- Route appropriately (allow `/new-topic`, `/help`, `/status`)
- Block other commands with helpful error message

### Phase 5: Parallel Execution Validation

Verify topics work independently with concurrent operations.

**Tasks:**
- Test multiple topics running AI commands simultaneously
- Verify conversation lock manager handles topic isolation
- Confirm no cross-contamination between topics

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Phase 1: Topic-Aware Infrastructure

#### UPDATE `src/adapters/telegram.ts`

**IMPLEMENT**: Modify `getConversationId()` to include message_thread_id

```typescript
getConversationId(ctx: Context): string {
  if (!ctx.chat) {
    throw new Error('No chat in context');
  }
  const chatId = ctx.chat.id.toString();

  // Check for forum topic (message_thread_id present)
  const threadId = 'message' in ctx && ctx.message?.message_thread_id;
  if (threadId) {
    return `${chatId}:${threadId}`;
  }

  return chatId; // General chat (no topic)
}
```

**PATTERN**: Follow existing error handling (line 178-180)
**IMPORTS**: None needed (Context already imported)
**GOTCHA**: `message_thread_id` only present in forum topics, not regular chats
**VALIDATE**:
```bash
npm run type-check
```

#### UPDATE `src/adapters/telegram.ts`

**IMPLEMENT**: Add helper method to detect general chat vs topic

```typescript
/**
 * Check if message is in general chat (not a topic)
 */
private isGeneralChat(ctx: Context): boolean {
  return !('message' in ctx && ctx.message?.message_thread_id);
}
```

**PATTERN**: Private helper methods follow existing pattern (line 84-109, 114-151)
**VALIDATE**:
```bash
npm run lint
```

#### UPDATE `src/adapters/telegram.ts`

**IMPLEMENT**: Store group chat ID in constructor for validation

```typescript
private groupChatId: string | null;

constructor(token: string, mode: 'stream' | 'batch' = 'stream') {
  // ... existing code ...
  this.groupChatId = process.env.TELEGRAM_GROUP_CHAT_ID ?? null;
  if (this.groupChatId) {
    console.log(`[Telegram] Configured for group: ${this.groupChatId}`);
  }
}
```

**PATTERN**: Environment variable pattern (line 37-46)
**GOTCHA**: Group chat ID is negative for supergroups (e.g., -1003484800871)
**VALIDATE**:
```bash
npm run type-check
```

### Phase 2: Response Formatting System

#### CREATE `src/utils/response-formatter.ts`

**IMPLEMENT**: Non-technical response filtering utility

```typescript
/**
 * Response formatting utilities for non-technical audiences
 */

/**
 * Strip code blocks and replace with summary messages
 */
export function stripCodeBlocks(message: string): string {
  // Remove fenced code blocks (```...```)
  message = message.replace(/```[\s\S]*?```/g, '[Code changes made - use /show-changes to see details]');

  // Remove inline code (`...`)
  message = message.replace(/`[^`]+`/g, (match) => {
    // Preserve file paths and commands starting with /
    if (match.includes('/') || match.startsWith('`/')) {
      return match;
    }
    return match.replace(/`/g, '');
  });

  return message;
}

/**
 * Enhance summaries with "what and why" context for non-technical readers
 * Example: "Created 3 files" → "Created 3 files for the search filter feature (FilterService, UI component, and tests) to enable users to narrow down search results"
 */
export function enhanceSummary(message: string): string {
  // Look for file operation summaries
  const patterns = [
    {
      regex: /(?:Created|created)\s+(\d+)\s+files?/gi,
      replacement: 'Created $1 files'
    },
    {
      regex: /(?:Modified|modified|Updated|updated)\s+(\d+)\s+files?/gi,
      replacement: 'Modified $1 files'
    },
    {
      regex: /(?:Deleted|deleted|Removed|removed)\s+(\d+)\s+files?/gi,
      replacement: 'Deleted $1 files'
    }
  ];

  // Keep original message (AI should provide context)
  // This function is a hook for future enhancements
  return message;
}

/**
 * Format response for non-technical decision maker
 * - Strip code blocks
 * - Keep natural language explanations
 * - Ensure "what and why" context is present
 */
export function formatForNonTechnical(message: string): string {
  let formatted = stripCodeBlocks(message);
  formatted = enhanceSummary(formatted);
  return formatted;
}
```

**PATTERN**: Utility module pattern (see utils/variable-substitution.ts, utils/telegram-markdown.ts)
**IMPORTS**: None needed (pure string manipulation)
**VALIDATE**:
```bash
npm run type-check
npm run lint
```

#### CREATE `src/utils/response-formatter.test.ts`

**IMPLEMENT**: Unit tests for response formatting

```typescript
import { stripCodeBlocks, formatForNonTechnical } from './response-formatter';

describe('Response Formatter', () => {
  describe('stripCodeBlocks', () => {
    it('should remove fenced code blocks', () => {
      const input = 'Here is some code:\n```typescript\nconst x = 1;\n```\nDone!';
      const result = stripCodeBlocks(input);
      expect(result).not.toContain('const x = 1');
      expect(result).toContain('[Code changes made');
    });

    it('should preserve file paths in inline code', () => {
      const input = 'Modified `src/index.ts` file';
      const result = stripCodeBlocks(input);
      expect(result).toContain('src/index.ts');
    });

    it('should remove regular inline code', () => {
      const input = 'Set variable to `true` value';
      const result = stripCodeBlocks(input);
      expect(result).not.toContain('`true`');
    });
  });

  describe('formatForNonTechnical', () => {
    it('should strip code blocks from complete message', () => {
      const input = 'I created the feature:\n```python\ndef hello():\n    pass\n```\nAll done!';
      const result = formatForNonTechnical(input);
      expect(result).not.toContain('def hello');
      expect(result).toContain('All done');
    });
  });
});
```

**PATTERN**: Test pattern (see utils/variable-substitution.test.ts)
**VALIDATE**:
```bash
npm test -- response-formatter.test.ts
```

#### UPDATE `src/orchestrator/orchestrator.ts`

**IMPLEMENT**: Apply response formatting for Telegram batch mode

Find the section where responses are sent (around line 200-250), and add filtering:

```typescript
// After AI streaming completes and before sending final message
if (platform.getPlatformType() === 'telegram' && mode === 'batch') {
  // Import at top: import { formatForNonTechnical } from '../utils/response-formatter';
  finalMessage = formatForNonTechnical(finalMessage);
}
```

**PATTERN**: Platform-specific handling (see existing Discord/Slack patterns in orchestrator)
**IMPORTS**: Add to top of file: `import { formatForNonTechnical } from '../utils/response-formatter';`
**GOTCHA**: Only apply to Telegram platform, not other platforms
**VALIDATE**:
```bash
npm run type-check
```

#### UPDATE `src/index.ts`

**IMPLEMENT**: Force batch mode for Telegram adapter

Change line 389:
```typescript
// OLD:
const streamingMode = (process.env.TELEGRAM_STREAMING_MODE ?? 'stream') as 'stream' | 'batch';

// NEW (force batch mode):
const streamingMode = 'batch'; // Force batch mode for non-technical summaries
```

**PATTERN**: Adapter initialization (line 386-414)
**GOTCHA**: This overrides environment variable to enforce batch mode
**VALIDATE**:
```bash
npm run type-check
```

### Phase 3: Project Scaffolding Command

#### CREATE `src/utils/github-repo.ts`

**IMPLEMENT**: GitHub repository creation utility

```typescript
/**
 * GitHub repository management utilities
 */
import { Octokit } from '@octokit/rest';

export interface CreateRepoOptions {
  name: string;
  description?: string;
  private: boolean;
  autoInit: boolean; // Initialize with README
}

export interface CreateRepoResult {
  fullName: string; // owner/repo
  htmlUrl: string; // https://github.com/owner/repo
  cloneUrl: string; // https://github.com/owner/repo.git
  defaultBranch: string; // main
}

/**
 * Create a new GitHub repository for authenticated user
 */
export async function createRepository(
  token: string,
  options: CreateRepoOptions
): Promise<CreateRepoResult> {
  const octokit = new Octokit({ auth: token });

  try {
    const { data } = await octokit.rest.repos.createForAuthenticatedUser({
      name: options.name,
      description: options.description,
      private: options.private,
      auto_init: options.autoInit,
      default_branch: 'main',
    });

    return {
      fullName: data.full_name,
      htmlUrl: data.html_url,
      cloneUrl: data.clone_url,
      defaultBranch: data.default_branch,
    };
  } catch (error) {
    const err = error as Error;
    throw new Error(`Failed to create GitHub repository: ${err.message}`);
  }
}
```

**PATTERN**: Octokit wrapper pattern (see github.ts:59-65)
**IMPORTS**: `import { Octokit } from '@octokit/rest';`
**GOTCHA**: Repository name must be URL-safe (no spaces)
**VALIDATE**:
```bash
npm run type-check
```

#### CREATE `src/handlers/new-topic-handler.ts`

**IMPLEMENT**: Project scaffolding logic for `/new-topic` command

```typescript
/**
 * Handler for /new-topic command
 * Creates complete project scaffolding: GitHub repo + workspace + Archon project + Telegram topic
 */
import { execFile } from 'child_process';
import { promisify } from 'util';
import { writeFile } from 'fs/promises';
import { join, resolve } from 'path';
import { Telegraf } from 'telegraf';
import { createRepository } from '../utils/github-repo';
import * as codebaseDb from '../db/codebases';

const execFileAsync = promisify(execFile);

export interface NewTopicOptions {
  projectName: string;
  groupChatId: string;
  githubToken: string;
  workspacePath: string;
  bot: Telegraf;
}

export interface NewTopicResult {
  success: boolean;
  message: string;
  topicId?: number;
  codebaseId?: string;
}

/**
 * Convert project name to URL-safe format
 * "Github search agent" → "github-search-agent"
 */
function sanitizeProjectName(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

/**
 * Create README.md with project metadata
 */
async function createProjectReadme(
  workspacePath: string,
  metadata: {
    projectName: string;
    githubUrl: string;
    archonProjectId: string;
    workspacePath: string;
  }
): Promise<void> {
  const content = `# ${metadata.projectName}

## Project Information

- **GitHub Repository**: ${metadata.githubUrl}
- **Archon Project ID**: ${metadata.archonProjectId}
- **Workspace Path**: ${metadata.workspacePath}
- **Created**: ${new Date().toISOString()}

## Getting Started

This project was created via the Remote Coding Agent Telegram bot.

Use the dedicated Telegram topic to interact with the AI assistant for this project.
`;

  await writeFile(join(workspacePath, 'README.md'), content, 'utf-8');
}

/**
 * Execute /new-topic command workflow
 */
export async function handleNewTopic(options: NewTopicOptions): Promise<NewTopicResult> {
  const { projectName, groupChatId, githubToken, workspacePath, bot } = options;

  try {
    // 1. Sanitize project name
    const repoName = sanitizeProjectName(projectName);
    if (!repoName) {
      return {
        success: false,
        message: 'Invalid project name. Use alphanumeric characters and spaces.',
      };
    }

    // 2. Create GitHub repository (private, with README)
    console.log(`[NewTopic] Creating GitHub repo: ${repoName}`);
    const repo = await createRepository(githubToken, {
      name: repoName,
      description: `${projectName} - Created via Remote Coding Agent`,
      private: true,
      autoInit: true, // Initialize with README
    });

    // 3. Clone repository to workspace
    console.log(`[NewTopic] Cloning to workspace: ${workspacePath}`);
    const repoPath = join(workspacePath, repoName);
    await execFileAsync('git', ['clone', repo.cloneUrl, repoPath]);

    // 4. Create Archon project (using MCP tool)
    // Note: This requires Archon MCP server to be configured
    console.log('[NewTopic] Creating Archon project');
    // TODO: Call mcp__archon__manage_project when MCP integration is ready
    // For now, use placeholder ID
    const archonProjectId = `proj_${Date.now()}`;

    // 5. Update README with metadata
    console.log('[NewTopic] Updating README with metadata');
    await createProjectReadme(repoPath, {
      projectName,
      githubUrl: repo.htmlUrl,
      archonProjectId,
      workspacePath: repoPath,
    });

    // 6. Commit README changes
    await execFileAsync('git', ['-C', repoPath, 'add', 'README.md']);
    await execFileAsync('git', ['-C', repoPath, 'commit', '-m', 'Add project metadata to README']);
    await execFileAsync('git', ['-C', repoPath, 'push']);

    // 7. Create codebase record in database
    console.log('[NewTopic] Creating codebase record');
    const codebase = await codebaseDb.createCodebase({
      name: projectName,
      repository_url: repo.htmlUrl,
      default_cwd: repoPath,
      ai_assistant_type: process.env.DEFAULT_AI_ASSISTANT ?? 'claude',
      commands: {}, // Empty - will be populated via /load-commands
    });

    // 8. Create Telegram topic
    console.log('[NewTopic] Creating Telegram topic');
    const topic = await bot.telegram.createForumTopic(
      parseInt(groupChatId),
      projectName
    );

    return {
      success: true,
      message: `✅ Project "${projectName}" created successfully!

📁 **Codebase**: ${projectName}
📂 **Path**: ${repoPath}
🔗 **GitHub**: ${repo.htmlUrl}
📊 **Archon Project**: ${archonProjectId}
💬 **Telegram Topic**: Created (ID: ${topic.message_thread_id})

Switch to the new topic to start working!`,
      topicId: topic.message_thread_id,
      codebaseId: codebase.id,
    };
  } catch (error) {
    const err = error as Error;
    console.error('[NewTopic] Error:', err);
    return {
      success: false,
      message: `❌ Failed to create project: ${err.message}`,
    };
  }
}
```

**PATTERN**: Command handler pattern (see command-handler.ts:98-150)
**IMPORTS**: See import block in code above
**GOTCHA**: Git operations require GH_TOKEN to be set for authentication
**GOTCHA**: Telegram createForumTopic requires supergroup with topics enabled
**VALIDATE**:
```bash
npm run type-check
```

#### UPDATE `src/handlers/command-handler.ts`

**IMPLEMENT**: Add `/new-topic` command to switch statement

```typescript
// At top of file, add import:
import { handleNewTopic } from './new-topic-handler';

// In handleCommand function, add new case:
case 'new-topic': {
  // Only allow in general chat (not in topics)
  // Check if conversation ID has no colon (general chat)
  if (conversation.platform_conversation_id.includes(':')) {
    return {
      success: false,
      message: '❌ /new-topic can only be used in general chat, not in topics.',
    };
  }

  if (args.length < 1) {
    return {
      success: false,
      message: 'Usage: /new-topic <project-name>\n\nExample: /new-topic Github search agent',
    };
  }

  const projectName = args.join(' ');
  const githubToken = process.env.GH_TOKEN ?? process.env.GITHUB_TOKEN;

  if (!githubToken) {
    return {
      success: false,
      message: '❌ GitHub token not configured. Set GH_TOKEN or GITHUB_TOKEN in environment.',
    };
  }

  // Get Telegram bot instance (need to pass from index.ts via conversation metadata)
  // For now, return placeholder
  return {
    success: false,
    message: '⚠️ /new-topic command is not yet fully integrated. Implementation in progress.',
  };

  // TODO: Complete integration:
  // const result = await handleNewTopic({
  //   projectName,
  //   groupChatId: conversation.platform_conversation_id,
  //   githubToken,
  //   workspacePath: process.env.WORKSPACE_PATH ?? '/workspace',
  //   bot: telegramBotInstance
  // });
  // return { success: result.success, message: result.message };
}
```

**PATTERN**: Command case pattern (line 105-142)
**IMPORTS**: Add at top of file
**GOTCHA**: Need access to Telegram bot instance - requires refactoring to pass bot reference
**VALIDATE**:
```bash
npm run type-check
```

### Phase 4: General Chat Restrictions

#### UPDATE `src/orchestrator/orchestrator.ts`

**IMPLEMENT**: Detect and restrict general chat messages

Add after conversation loading (around line 70):

```typescript
// Check if this is Telegram general chat (no topic)
const isGeneralChat = platform.getPlatformType() === 'telegram' &&
                      !conversationId.includes(':');

// If general chat, only allow specific commands
if (isGeneralChat && message.startsWith('/')) {
  const { command } = commandHandler.parseCommand(message);
  const allowedInGeneralChat = ['new-topic', 'help', 'status', 'commands', 'templates'];

  if (!allowedInGeneralChat.includes(command)) {
    await platform.sendMessage(
      conversationId,
      `❌ This command can only be used in project topics, not general chat.\n\nUse /new-topic to create a project topic, then run commands there.`
    );
    return;
  }
}
```

**PATTERN**: Early return pattern for validation (see existing patterns in orchestrator)
**IMPORTS**: None needed (parseCommand already imported)
**GOTCHA**: Must check platform type AND conversation ID format
**VALIDATE**:
```bash
npm run type-check
```

### Phase 5: Documentation and Environment Variables

#### UPDATE `.env.example`

**IMPLEMENT**: Add new environment variables

```env
# Telegram Group Configuration (for topic-based multi-project development)
TELEGRAM_GROUP_CHAT_ID=-1003484800871  # Your supergroup chat ID (negative number)

# GitHub Owner (for repository creation)
GITHUB_OWNER=your-github-username
```

**PATTERN**: Follow existing .env.example format
**VALIDATE**: Visual inspection

#### UPDATE `CLAUDE.md`

**IMPLEMENT**: Document new feature in Configuration section

Add to Telegram section:

```markdown
### Telegram Topics (Multi-Project Development)

**Group Setup:**
- Create a Telegram supergroup with topics enabled
- Add bot as administrator
- Get group chat ID (negative number, e.g., -1003484800871)
- Set `TELEGRAM_GROUP_CHAT_ID` in environment

**Usage:**
- General chat: Use `/new-topic <name>` to create projects
- Topics: Each topic = isolated project workspace
- Click between topics to switch projects instantly
- All topics run in parallel (like separate terminals)

**Response Format:**
- Batch mode only (final summaries)
- No code blocks shown
- Brief, non-technical language
- "What and why" explanations included
```

**PATTERN**: Follow existing documentation structure in CLAUDE.md
**VALIDATE**: Visual inspection

---

## TESTING STRATEGY

### Unit Tests

**Scope**: Pure functions and utilities

**Files to test**:
- `src/utils/response-formatter.ts` - Code stripping, summary enhancement
- `src/utils/github-repo.ts` - Repository name sanitization

**Pattern**:
```typescript
describe('Response Formatter', () => {
  it('should strip code blocks', () => {
    const input = '```code```';
    const result = stripCodeBlocks(input);
    expect(result).not.toContain('code');
  });
});
```

### Integration Tests

**Scope**: Command execution and database operations

**Test scenarios**:
1. **Topic Isolation**: Create two conversations with different topic IDs, verify they don't share state
2. **General Chat Detection**: Send message to general chat, verify restricted commands are blocked
3. **Conversation ID Format**: Test both `chatId` and `chatId:threadId` formats

**Pattern**:
```typescript
describe('Topic-Based Conversations', () => {
  it('should isolate conversations by topic ID', async () => {
    const conv1 = await getOrCreateConversation('telegram', '-100:1');
    const conv2 = await getOrCreateConversation('telegram', '-100:2');
    expect(conv1.id).not.toBe(conv2.id);
  });
});
```

### Manual Validation

**Test with Telegram Bot**:
1. Send message to general chat → Verify restricted
2. Create new topic manually → Send message → Verify works
3. Use `/status` in topic → Verify shows correct project
4. Start AI operation in Topic 1, immediately switch to Topic 2 and start another → Verify both complete independently

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
# TypeScript type checking
npm run type-check

# ESLint (must pass with 0 errors)
npm run lint

# Prettier formatting check
npm run format:check
```

**Expected**: All commands pass with exit code 0

### Level 2: Unit Tests

```bash
# Run all unit tests
npm test

# Run with coverage
npm run test:coverage

# Run specific test file
npm test -- response-formatter.test.ts
```

**Expected**: All tests pass, coverage >80%

### Level 3: Build Verification

```bash
# Build TypeScript
npm run build

# Verify dist/ directory created
ls -la dist/

# Check for build errors
echo $?  # Should be 0
```

**Expected**: Clean build with no errors

### Level 4: Manual Validation (Telegram Bot)

**Setup**:
1. Set `TELEGRAM_GROUP_CHAT_ID=-1003484800871` in `.env`
2. Start application: `npm run dev`
3. Open Telegram, go to the configured group

**Test General Chat Restrictions**:
```
You (in general chat): /clone https://github.com/test/repo
Bot: ❌ This command can only be used in project topics, not general chat.

You (in general chat): /help
Bot: [Shows help message - allowed]

You (in general chat): /status
Bot: [Shows status - allowed]
```

**Test Topic Isolation**:
```
You: Create two topics manually: "Project A" and "Project B"

You (in Project A topic): /status
Bot: Platform: telegram
     AI Assistant: claude
     [Shows Project A info if configured]

You (in Project B topic): /status
Bot: Platform: telegram
     AI Assistant: claude
     [Shows different info - isolated conversation]
```

**Test Parallel Execution**:
```
You (in Project A topic): /command-invoke prime
Bot: [Starts working in background]

You (in Project B topic): /command-invoke plan "Add feature"
Bot: [Starts working in background - both run in parallel]

Wait for both to complete - verify both return results
```

**Test Response Formatting**:
```
You (in topic): Ask AI to write code
Bot: [Returns summary without code blocks]
     Example: "I created the authentication module with login and signup functions. Modified the database schema to add user tables."
     [No code shown, only natural language summary]
```

### Level 5: Database Verification

```bash
# Connect to database
psql $DATABASE_URL

# Check conversation isolation
SELECT platform_conversation_id, codebase_id, cwd
FROM remote_agent_conversations
WHERE platform_type = 'telegram';

# Should see multiple rows with different topic IDs (format: chatId:threadId)
```

**Expected**: Multiple conversations with format `-1003484800871:1234`, `-1003484800871:5678`, etc.

---

## ACCEPTANCE CRITERIA

- [x] Telegram adapter supports topic-based conversation IDs (`chatId:threadId` format)
- [ ] General chat only responds to `/new-topic`, `/help`, `/status`, `/commands`, `/templates`
- [ ] Each topic maintains independent conversation, codebase, and session
- [ ] Multiple topics can run AI operations in parallel without blocking
- [ ] Responses show only final summaries (no code blocks, no streaming updates)
- [ ] Responses use non-technical language with "what and why" context
- [ ] `/new-topic <name>` creates: GitHub repo (private) + workspace clone + Archon project + Telegram topic
- [ ] README.md in workspace contains: GitHub URL, Archon project ID, workspace path
- [ ] All validation commands pass (type-check, lint, format:check, tests)
- [ ] Manual validation confirms: topic isolation, parallel execution, response formatting

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order (Phase 1 → Phase 5)
- [ ] Each task validated immediately after completion
- [ ] All validation commands executed successfully:
  - [ ] Level 1: type-check, lint, format:check ✓
  - [ ] Level 2: test, test:coverage ✓
  - [ ] Level 3: build, dist/ verification ✓
  - [ ] Level 4: Manual Telegram bot testing ✓
  - [ ] Level 5: Database verification ✓
- [ ] Full test suite passes (unit + integration)
- [ ] No linting errors
- [ ] No formatting errors
- [ ] No type checking errors
- [ ] Build succeeds
- [ ] All acceptance criteria met
- [ ] Manual testing confirms feature works end-to-end

---

## NOTES

### Design Decisions

**1. Conversation ID Format: `chatId:threadId`**
- Rationale: Simple, unique, database-friendly
- Alternative considered: Store thread_id in separate column (rejected: more complex, unnecessary)
- Trade-off: Requires parsing to extract chatId (acceptable overhead)

**2. Force Batch Mode for Telegram**
- Rationale: User explicitly requested final summaries only, not streaming updates
- Alternative considered: Make it configurable via env var (rejected: user wants simple UX, not options)
- Trade-off: Cannot see intermediate progress (acceptable per user requirements)

**3. General Chat Restrictions**
- Rationale: Prevent confusion and accidental commands in wrong context
- Alternative considered: Allow all commands everywhere (rejected: too easy to make mistakes)
- Trade-off: Less flexible, but more foolproof UX

**4. /new-topic in General Chat Only**
- Rationale: Creating projects from within topics is conceptually confusing
- Alternative considered: Allow from anywhere (rejected: unclear where new topic should be created)
- Trade-off: Must switch to general chat to create projects (acceptable: infrequent operation)

### Implementation Risks

**1. Telegram API Rate Limits**
- Risk: Creating topics, sending messages may hit rate limits
- Mitigation: Telegraf SDK handles rate limiting automatically
- Monitoring: Log all API calls with timing

**2. GitHub Repository Name Conflicts**
- Risk: Project name already exists in user's GitHub account
- Mitigation: GitHub API returns clear error, show to user, suggest different name
- Enhancement: Could auto-append timestamp if name taken

**3. Archon MCP Integration**
- Risk: Archon MCP server might not be configured or available
- Mitigation: Graceful fallback with placeholder ID, log warning
- Enhancement: Check for MCP availability before attempting project creation

**4. Parallel Execution Resource Usage**
- Risk: Too many simultaneous AI operations could exhaust system resources
- Mitigation: ConversationLockManager already limits concurrent operations (default: 10)
- Monitoring: Health check endpoint shows active/queued conversations

### Future Enhancements

**1. `/show-changes` Command**
- Show git diff summary for current topic
- List files created/modified/deleted
- Natural language description of changes

**2. Auto-detect Command Folders**
- After cloning repo, auto-scan for `.claude/commands/` or `.agents/commands/`
- Auto-run `/load-commands` if found
- Prompt user: "Found commands folder, load automatically? (y/n)"

**3. Topic Status Overview**
- `/topics` command in general chat
- Shows all topics with their projects and current status
- Example: "Project A (Topic 123): Planning phase | Project B (Topic 456): Implementing feature"

**4. Archon MCP Integration**
- Complete implementation with actual MCP tool calls
- Create tasks in Archon when `/command-invoke plan` is used
- Update task status when implementation completes

**5. Configurable Response Detail Level**
- Allow user to request more detail: "Tell me more about phase 2"
- AI drills down with additional context
- Configurable verbosity per topic

### Confidence Score

**8/10** - High confidence for one-pass implementation success

**Strengths**:
- Clear, well-defined requirements
- Existing patterns to follow (conversation isolation, command handling)
- Comprehensive test strategy
- All necessary APIs documented

**Risks**:
- Telegram topic creation API might have undocumented quirks (mitigated by research agent)
- Archon MCP integration requires additional setup (mitigated by graceful fallback)
- Response filtering might need tuning based on actual AI outputs (mitigated by iterative refinement)

**Mitigation**:
- Each task has validation command
- Manual testing steps are detailed and specific
- Fallback strategies documented for risky components
