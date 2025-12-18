# Plan: Workflow Router (Natural Language Intent Detection)

## Summary

Add a workflow router that enables users to interact with `@remote-agent` using natural language instead of requiring specific slash commands. When a user mentions the bot without a slash command (e.g., "fix this bug", "review this PR", "why is this happening?"), the router template instructs the existing AI assistant (Claude/Codex/etc.) to analyze the request and execute the appropriate workflow. This uses the existing SDK infrastructure - no additional AI layer needed.

## The Problem

Currently, GitHub users must:
1. Know the exact slash command (`/fix-issue`, `/rca`, `/review-pr`, etc.)
2. Remember which command to use for which situation
3. Type commands correctly (no autocomplete in GitHub)

This creates friction and confusion, especially for new users.

## The Solution

When `@remote-agent` is mentioned without a slash command:
1. Load a `router` template (stored in database like other templates)
2. Send the user's natural language request to the AI with routing instructions
3. AI analyzes intent and executes the appropriate workflow

```
User: @remote-agent the login form isn't redirecting properly

         ↓ (no slash command detected)

Load `router` template with:
- List of available workflows and when to use each
- User's request embedded
- Instruction to analyze and execute

         ↓

AI (existing SDK) decides: "This is a bug report → execute rca workflow"
```

## External Research

### Existing Pattern in Codebase
The codebase already has a template system:
- Templates stored in `remote_agent_command_templates` table
- Seeded from `.claude/commands/exp-piv-loop/*.md` on startup
- Loaded via `templateDb.getTemplate(name)` in orchestrator
- Variable substitution with `$ARGUMENTS`, `$1`, `$2`, etc.

The router is simply a new template that gets used when no command is specified.

## Patterns to Mirror

### Template Loading Pattern (from orchestrator.ts:152-173)
```typescript
// FROM: src/orchestrator/orchestrator.ts:152-173
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
}
```

### Template Seeding Pattern (from seed-commands.ts)
```typescript
// FROM: src/scripts/seed-commands.ts:38-44
await upsertTemplate({
  name,
  description: description ?? `From ${SEED_COMMANDS_PATH}`,
  content,
});
console.log(`[Seed] Loaded template: ${name}`);
```

### GitHub Adapter Non-Slash Message Handling (from github.ts:612-623)
```typescript
// FROM: src/adapters/github.ts:612-623
// For non-command messages, add issue/PR context directly
if (eventType === 'issue' && issue) {
  finalMessage = this.buildIssueContext(issue, strippedComment);
} else if (eventType === 'issue_comment' && issue) {
  finalMessage = this.buildIssueContext(issue, strippedComment);
} else if (eventType === 'pull_request' && pullRequest) {
  finalMessage = this.buildPRContext(pullRequest, strippedComment);
}
```

## Files to Change

| File | Action | Justification |
|------|--------|---------------|
| `.claude/commands/exp-piv-loop/router.md` | CREATE | New router template with workflow routing instructions |
| `src/orchestrator/orchestrator.ts` | UPDATE | Route non-slash messages through router template |
| `src/adapters/github.ts` | UPDATE | Pass full context for router (not just for new conversations) |

## NOT Building

- **No new AI client/layer** - Uses existing SDK (Claude/Codex/etc.)
- **No YAML workflow engine yet** - Router just dispatches to existing templates
- **No complex intent classification** - AI handles the routing decision
- **No caching of routing decisions** - Each request is independent
- **No multi-step chaining yet** - Router picks ONE workflow (chaining comes with workflow engine)

## Tasks

### Task 1: Create router template

**Why**: The router template instructs the AI how to analyze user intent and execute the appropriate workflow.

**Do**: Create `.claude/commands/exp-piv-loop/router.md`:

```markdown
---
description: Route natural language requests to the appropriate workflow
---

# Workflow Router

You are a workflow router for a remote coding agent. A user has mentioned @remote-agent with a natural language request. Your job is to:

1. **Analyze** the user's intent from their message
2. **Select** the most appropriate workflow
3. **Execute** that workflow immediately

## User's Request

$ARGUMENTS

## Available Workflows

### Investigation & Debugging
- **rca** - Root cause analysis. Use when:
  - User reports something "not working", "broken", "failing"
  - User asks "why is X happening?"
  - User describes unexpected behavior
  - Error messages or stack traces are provided

### Bug Fixes
- **fix-issue** - Fix a bug end-to-end. Use when:
  - User explicitly asks to "fix" something
  - After RCA, user wants the fix implemented
  - Bug is clearly described with reproduction steps
  - Issue is a straightforward fix (not a feature)

### Code Review
- **review-pr** - Review a pull request. Use when:
  - User asks to "review" code/PR/changes
  - User mentions a PR number
  - Event is on a pull request (not issue)
  - User asks for feedback on implementation

### Feature Development
- **plan** - Create an implementation plan. Use when:
  - User requests a new feature
  - User asks "how should we implement X?"
  - Change requires architectural decisions
  - Scope is unclear and needs planning

### Pull Request Creation
- **create-pr** - Create a PR from current changes. Use when:
  - User says "create PR", "open PR", "submit PR"
  - Work is complete and ready for review
  - User wants to propose changes

## Decision Process

1. Read the user's request carefully
2. Consider the context (is this an issue or PR? what's the title?)
3. Match to the most appropriate workflow above
4. If unclear between RCA and fix-issue, prefer RCA first (investigate before fixing)
5. If the request doesn't match any workflow, ask for clarification

## Execution

Once you've determined the workflow, execute it as if the user had typed that command directly. For example:
- If the intent is RCA → behave as if user typed `/rca`
- If the intent is fix-issue → behave as if user typed `/fix-issue`

Do NOT explain your routing decision to the user. Just execute the appropriate workflow silently.

---

Now analyze the request and execute the appropriate workflow:
```

**Verify**: File exists and follows template format with frontmatter

---

### Task 2: Update orchestrator to use router for non-slash messages

**Why**: Currently non-slash messages require a codebase but don't route through any template. We need to route them through the router template.

**Mirror**: Template loading pattern at `src/orchestrator/orchestrator.ts:152-173`

**Do**: Update `src/orchestrator/orchestrator.ts`:

1. Find the block that handles regular messages (around line 175-181):
```typescript
} else {
  // Regular message - require codebase
  if (!conversation.codebase_id) {
    await platform.sendMessage(conversationId, 'No codebase configured. Use /clone first.');
    return;
  }
}
```

2. Replace with router template loading:
```typescript
} else {
  // Regular message - route through router template
  if (!conversation.codebase_id) {
    await platform.sendMessage(conversationId, 'No codebase configured. Use /clone first.');
    return;
  }

  // Load router template for natural language routing
  const routerTemplate = await templateDb.getTemplate('router');
  if (routerTemplate) {
    console.log('[Orchestrator] Routing through router template');
    commandName = 'router';
    // Pass the entire message as $ARGUMENTS for the router
    promptToSend = substituteVariables(routerTemplate.content, [message]);
  }
  // If no router template, message passes through as-is (backward compatible)
}
```

**Don't**:
- Don't change the existing slash command handling
- Don't add issueContext here (GitHub adapter already appends it)

**Verify**: `npm run type-check`

---

### Task 3: Update GitHub adapter to always append context

**Why**: Currently issue/PR context is only added for new conversations OR slash commands. For the router to work well, it needs the context to understand what the user is asking about.

**Mirror**: Existing context building at `src/adapters/github.ts:612-623`

**Do**: Update `src/adapters/github.ts` around line 612:

Change from:
```typescript
} else if (isNewConversation) {
  // For non-command messages, add issue/PR context directly
```

To:
```typescript
} else {
  // For non-command messages, always add issue/PR context
  // Router needs this context to understand what the user is asking about
```

This removes the `isNewConversation` check so context is always added for non-slash messages.

**Don't**:
- Don't change the slash command handling
- Don't change worktree context (that's separate)

**Verify**: `npm run type-check`

---

### Task 4: Add router template to seed

**Why**: The router template should be seeded on startup like other templates.

**Mirror**: Existing seed pattern - templates in `.claude/commands/exp-piv-loop/` are automatically seeded.

**Do**: The router.md file created in Task 1 will be automatically seeded by the existing `seedDefaultCommands()` function since it's in the `.claude/commands/exp-piv-loop/` directory.

**Verify**:
1. Restart the app
2. Check logs for `[Seed] Loaded template: router`

---

### Task 5: Add unit test for router template loading

**Why**: Ensure the orchestrator correctly routes non-slash messages through the router template.

**Mirror**: Test patterns in `src/orchestrator/orchestrator.test.ts`

**Do**: Add test to `src/orchestrator/orchestrator.test.ts`:

```typescript
describe('router template', () => {
  it('should route non-slash messages through router template when available', async () => {
    // Setup: Mock router template exists
    mockTemplateDb.getTemplate.mockImplementation(async (name: string) => {
      if (name === 'router') {
        return {
          id: 'router-id',
          name: 'router',
          description: 'Route requests',
          content: 'Router prompt with $ARGUMENTS',
          created_at: new Date(),
          updated_at: new Date(),
        };
      }
      return null;
    });

    // Setup: Conversation with codebase
    mockDb.getOrCreateConversation.mockResolvedValue({
      id: 'conv-123',
      platform_type: 'github',
      platform_conversation_id: 'owner/repo#1',
      codebase_id: 'codebase-123',
      cwd: '/workspace/repo',
      worktree_path: null,
      ai_assistant_type: 'claude',
      created_at: new Date(),
      updated_at: new Date(),
    });

    mockCodebaseDb.getCodebase.mockResolvedValue({
      id: 'codebase-123',
      name: 'repo',
      repository_url: 'https://github.com/owner/repo',
      default_cwd: '/workspace/repo',
      ai_assistant_type: 'claude',
      commands: {},
      created_at: new Date(),
      updated_at: new Date(),
    });

    // Act: Send non-slash message
    await handleMessage(
      mockPlatform,
      'owner/repo#1',
      'fix the login bug' // Natural language, no slash
    );

    // Assert: Router template was loaded
    expect(mockTemplateDb.getTemplate).toHaveBeenCalledWith('router');

    // Assert: AI was called with router prompt containing the user's message
    expect(mockClaudeClient.sendQuery).toHaveBeenCalledWith(
      expect.stringContaining('fix the login bug'),
      expect.any(String),
      undefined
    );
  });

  it('should pass message directly if router template not available', async () => {
    // Setup: No router template
    mockTemplateDb.getTemplate.mockResolvedValue(null);

    // Setup: Conversation with codebase
    mockDb.getOrCreateConversation.mockResolvedValue({
      id: 'conv-123',
      platform_type: 'github',
      platform_conversation_id: 'owner/repo#1',
      codebase_id: 'codebase-123',
      cwd: '/workspace/repo',
      worktree_path: null,
      ai_assistant_type: 'claude',
      created_at: new Date(),
      updated_at: new Date(),
    });

    mockCodebaseDb.getCodebase.mockResolvedValue({
      id: 'codebase-123',
      name: 'repo',
      repository_url: 'https://github.com/owner/repo',
      default_cwd: '/workspace/repo',
      ai_assistant_type: 'claude',
      commands: {},
      created_at: new Date(),
      updated_at: new Date(),
    });

    // Act: Send non-slash message
    await handleMessage(
      mockPlatform,
      'owner/repo#1',
      'fix the login bug'
    );

    // Assert: Message passed directly to AI (backward compatible)
    expect(mockClaudeClient.sendQuery).toHaveBeenCalledWith(
      'fix the login bug',
      expect.any(String),
      undefined
    );
  });
});
```

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
| `orchestrator.test.ts` | Route non-slash through router | Router template is loaded for natural language |
| `orchestrator.test.ts` | Backward compatible without router | Works if router template missing |

### Manual/E2E Validation

```bash
# 1. Start the app
npm run dev

# 2. Verify router template is seeded
# Check logs for: [Seed] Loaded template: router

# 3. Test via GitHub (requires webhook setup)
# Create a test issue and comment:
# "@remote-agent why isn't the login working?"
# Expected: Bot routes to RCA workflow

# 4. Test via Test Adapter
curl -X POST http://localhost:3090/test/message \
  -H "Content-Type: application/json" \
  -d '{"conversationId":"test-router","message":"fix the authentication bug"}'

# Check response - should show RCA/fix-issue behavior, not ask for a command
curl http://localhost:3090/test/messages/test-router
```

### Edge Cases to Test
- [ ] User says just "@remote-agent" with no message → Should ask what they need
- [ ] User says "@remote-agent help" → Should route appropriately (or show help)
- [ ] User says "@remote-agent /fix-issue" → Should use slash command, not router
- [ ] Router template missing → Falls back to direct message (backward compatible)
- [ ] Ambiguous request → AI should pick best match or ask for clarification

### Regression Check
- [ ] Existing slash commands still work (`/rca`, `/fix-issue`, etc.)
- [ ] `/command-invoke` still works for codebase-specific commands
- [ ] Deterministic commands still work (`/status`, `/help`, etc.)
- [ ] GitHub issues with slash commands work as before

## Risks

1. **AI Misrouting**: The AI might pick the wrong workflow for ambiguous requests. Mitigated by:
   - Clear workflow descriptions in router template
   - Defaulting to RCA for "something is broken" requests
   - AI can ask for clarification if truly ambiguous

2. **Performance**: Extra template lookup for every non-slash message. Mitigated by:
   - Template lookup is a simple DB query (fast)
   - Only happens for non-slash messages

3. **Context Loss**: Router might not have enough context to make good decisions. Mitigated by:
   - Always appending issue/PR context (Task 3)
   - Router template includes context description

4. **Backward Compatibility**: Old behavior should still work. Mitigated by:
   - If router template doesn't exist, message passes through as-is
   - Slash commands bypass router entirely
