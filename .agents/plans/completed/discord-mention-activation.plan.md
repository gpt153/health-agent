# Plan: Discord Mention-Based Activation with Thread Context

## Summary

Enhance the Discord adapter to only respond when explicitly mentioned (`@BotName`), and when mentioned in a thread, read all previous thread messages to provide full conversation context to the AI. This makes the bot team-friendly (doesn't interrupt conversations) and context-aware (understands the full discussion before responding).

**Key features:**
1. Bot ignores messages unless mentioned
2. When mentioned in a thread, fetches all previous messages as context
3. Thread context is prepended to the user's request
4. Parent channel context inheritance (codebase/cwd) for new thread conversations

---

## External Research

### Documentation
- [Discord.js Guide - Threads](https://discordjs.guide/popular-topics/threads.html)
- [Stack Overflow - Bot mention detection](https://stackoverflow.com/questions/74334905/mention-bot-for-respond-discord-js-v14)
- [Stack Overflow - Fetch thread messages](https://stackoverflow.com/questions/55153125/fetch-more-than-100-messages)
- [Discord.js GitHub - fetchStarterMessage](https://github.com/discordjs/discord.js/pull/6488)

### Key API Patterns

**Mention detection:**
```typescript
// Check if bot was mentioned
message.mentions.has(client.user)
```

**Thread detection:**
```typescript
// Check if channel is a thread
message.channel.isThread()
// Get parent channel ID
message.channel.parentId
```

**Fetch thread messages:**
```typescript
// Fetch up to 100 messages (API limit)
const messages = await channel.messages.fetch({ limit: 100 });
// For more, paginate using 'before' parameter
```

**Fetch thread starter message:**
```typescript
// Get the message that started the thread
const starterMessage = await thread.fetchStarterMessage().catch(() => null);
```

### Gotchas & Best Practices
- Discord API limits message fetch to 100 per request - need pagination for more
- `fetchStarterMessage()` can fail if parent message was deleted - always catch
- Rate limit: ~5 messages per 5 seconds per channel
- Thread messages should be sorted chronologically (oldest first) for context
- Bot should strip its own mention from the message before processing

---

## Patterns to Mirror

### Discord adapter structure (from `src/adapters/discord.ts:10-29`)
```typescript
export class DiscordAdapter implements IPlatformAdapter {
  private client: Client;
  private streamingMode: 'stream' | 'batch';
  private token: string;
  private messageHandler: ((message: Message) => Promise<void>) | null = null;

  constructor(token: string, mode: 'stream' | 'batch' = 'stream') {
    this.client = new Client({
      intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
        GatewayIntentBits.DirectMessages,
      ],
      partials: [Partials.Channel],
    });
    // ...
  }
}
```

### Message handler pattern (from `src/index.ts:91-111`)
```typescript
discord.onMessage(async message => {
  const conversationId = discord!.getConversationId(message);
  const content = message.content;

  if (!content) return;

  lockManager
    .acquireLock(conversationId, async () => {
      await handleMessage(discord!, conversationId, content);
    })
    .catch(async error => {
      // error handling
    });
});
```

### Test mock pattern (from `src/adapters/discord.test.ts:7-39`)
```typescript
jest.mock('discord.js', () => {
  const mockChannel = {
    isSendable: () => true,
    send: jest.fn().mockResolvedValue(undefined),
  };

  const mockClient = {
    channels: { fetch: jest.fn().mockResolvedValue(mockChannel) },
    on: jest.fn(),
    once: jest.fn(),
    login: jest.fn().mockResolvedValue('token'),
    destroy: jest.fn(),
    user: { id: 'bot-user-id' }, // Add for mention detection
  };
  // ...
});
```

---

## Files to Change

| File | Action | Justification |
|------|--------|---------------|
| `src/adapters/discord.ts` | UPDATE | Add mention detection, thread history fetching methods |
| `src/adapters/discord.test.ts` | UPDATE | Add tests for new methods |
| `src/index.ts` | UPDATE | Update Discord handler to check mentions and fetch thread context |
| `src/orchestrator/orchestrator.ts` | UPDATE | Accept thread context parameter, inherit parent codebase for threads |
| `src/db/conversations.ts` | UPDATE | Add function to get conversation by platform ID for parent lookup |

---

## NOT Building

- ❌ Fetching more than 100 messages (pagination) - keep it simple for v1
- ❌ Caching thread history - fetch fresh each time
- ❌ Configurable mention requirement (always require mention for now)
- ❌ DM handling changes - mentions already not needed in DMs
- ❌ Slash command detection without mention - commands should still require mention

---

## Tasks

### Task 1: UPDATE `src/adapters/discord.ts` - Add mention detection method

**Why**: Need to check if the bot was mentioned in a message

**Mirror**: Existing method pattern in `src/adapters/discord.ts:131-137`

**Do**:
```typescript
/**
 * Check if the bot was mentioned in a message
 */
isBotMentioned(message: Message): boolean {
  const botUser = this.client.user;
  if (!botUser) return false;
  return message.mentions.has(botUser);
}
```

**Don't**:
- Don't check for role mentions, only direct user mentions
- Don't make this async - it's a sync check

**Verify**: `npm run type-check`

---

### Task 2: UPDATE `src/adapters/discord.ts` - Add thread detection methods

**Why**: Need to identify threads and get parent channel ID

**Mirror**: Existing method pattern in `src/adapters/discord.ts:131-137`

**Do**:
```typescript
/**
 * Check if a message is in a thread
 */
isThread(message: Message): boolean {
  return message.channel.isThread();
}

/**
 * Get parent channel ID for a thread message
 * Returns null if not in a thread
 */
getParentChannelId(message: Message): string | null {
  if (message.channel.isThread()) {
    return message.channel.parentId;
  }
  return null;
}
```

**Don't**:
- Don't throw errors, return null for non-threads

**Verify**: `npm run type-check`

---

### Task 3: UPDATE `src/adapters/discord.ts` - Add thread history fetching

**Why**: Need to fetch previous messages in thread for context

**Mirror**: Async method pattern in `src/adapters/discord.ts:35-56`

**Do**:
```typescript
/**
 * Fetch message history from a thread (up to 100 messages)
 * Returns messages in chronological order (oldest first)
 */
async fetchThreadHistory(message: Message): Promise<string[]> {
  if (!message.channel.isThread()) {
    return [];
  }

  try {
    // Fetch up to 100 messages (Discord API limit)
    const messages = await message.channel.messages.fetch({ limit: 100 });

    // Sort chronologically (oldest first) and format
    const sorted = [...messages.values()].reverse();

    return sorted.map(msg => {
      const author = msg.author.bot ? '[Bot]' : msg.author.displayName ?? msg.author.username;
      return `${author}: ${msg.content}`;
    });
  } catch (error) {
    console.error('[Discord] Failed to fetch thread history:', error);
    return [];
  }
}
```

**Don't**:
- Don't paginate beyond 100 messages (keep simple for v1)
- Don't throw on error, return empty array

**Verify**: `npm run type-check`

---

### Task 4: UPDATE `src/adapters/discord.ts` - Add method to strip bot mention

**Why**: The user's message should not include the @mention when sent to AI

**Mirror**: String manipulation pattern

**Do**:
```typescript
/**
 * Remove bot mention from message content
 */
stripBotMention(message: Message): string {
  const botUser = this.client.user;
  if (!botUser) return message.content;

  // Remove <@BOT_ID> or <@!BOT_ID> (with nickname)
  const mentionRegex = new RegExp(`<@!?${botUser.id}>\\s*`, 'g');
  return message.content.replace(mentionRegex, '').trim();
}
```

**Don't**:
- Don't remove other mentions, only the bot mention

**Verify**: `npm run type-check`

---

### Task 5: UPDATE `src/db/conversations.ts` - Add getConversationByPlatformId

**Why**: Need to look up parent channel conversation for thread context inheritance

**Mirror**: Existing query pattern in `src/db/conversations.ts:12-19`

**Do**:
```typescript
/**
 * Get a conversation by platform type and platform ID
 * Returns null if not found (unlike getOrCreate which creates)
 */
export async function getConversationByPlatformId(
  platformType: string,
  platformId: string
): Promise<Conversation | null> {
  const result = await pool.query<Conversation>(
    'SELECT * FROM remote_agent_conversations WHERE platform_type = $1 AND platform_conversation_id = $2',
    [platformType, platformId]
  );
  return result.rows[0] ?? null;
}
```

**Don't**:
- Don't create if not found - that's what getOrCreate is for

**Verify**: `npm run type-check`

---

### Task 6: UPDATE `src/orchestrator/orchestrator.ts` - Accept thread context and parent ID

**Why**: Orchestrator needs thread context and parent conversation ID for inheritance

**Mirror**: Existing issueContext parameter in `src/orchestrator/orchestrator.ts:22`

**Do**:
Update the function signature:
```typescript
export async function handleMessage(
  platform: IPlatformAdapter,
  conversationId: string,
  message: string,
  issueContext?: string,
  threadContext?: string,        // NEW: Thread message history
  parentConversationId?: string  // NEW: Parent channel ID for thread inheritance
): Promise<void> {
```

After line 28, add parent inheritance logic:
```typescript
// Get or create conversation
let conversation = await db.getOrCreateConversation(platform.getPlatformType(), conversationId);

// If new thread conversation, inherit context from parent
if (parentConversationId && !conversation.codebase_id) {
  const parentConversation = await db.getConversationByPlatformId(
    platform.getPlatformType(),
    parentConversationId
  );
  if (parentConversation?.codebase_id) {
    await db.updateConversation(conversation.id, {
      codebase_id: parentConversation.codebase_id,
      cwd: parentConversation.cwd,
    });
    // Reload conversation with inherited values
    conversation = await db.getOrCreateConversation(platform.getPlatformType(), conversationId);
    console.log('[Orchestrator] Thread inherited context from parent channel');
  }
}
```

Before sending to AI (around line 158), prepend thread context:
```typescript
// Prepend thread context if provided
if (threadContext) {
  promptToSend = `## Thread Context (previous messages)\n\n${threadContext}\n\n---\n\n## Current Request\n\n${promptToSend}`;
  console.log('[Orchestrator] Prepended thread context to prompt');
}
```

**Don't**:
- Don't override if conversation already has codebase_id (user manually configured)
- Don't fail if parent conversation doesn't exist

**Verify**: `npm run type-check`

---

### Task 7: UPDATE `src/index.ts` - Update Discord handler for mention activation

**Why**: Main handler needs to check mention, fetch context, and pass to orchestrator

**Mirror**: Existing handler in `src/index.ts:91-111`

**Do**:
Replace the Discord message handler (lines 91-111) with:
```typescript
// Register message handler
discord.onMessage(async message => {
  const conversationId = discord!.getConversationId(message);

  // Skip if no content
  if (!message.content) return;

  // Check if bot was mentioned (required for activation)
  // Exception: DMs don't require mention
  const isDM = !message.guild;
  if (!isDM && !discord!.isBotMentioned(message)) {
    return; // Ignore messages that don't mention the bot
  }

  // Strip the bot mention from the message
  const content = discord!.stripBotMention(message);
  if (!content) return; // Message was only a mention with no content

  // Check for thread context
  let threadContext: string | undefined;
  let parentConversationId: string | undefined;

  if (discord!.isThread(message)) {
    // Fetch thread history for context
    const history = await discord!.fetchThreadHistory(message);
    if (history.length > 0) {
      // Exclude the current message from history (it's included in fetch)
      const historyWithoutCurrent = history.slice(0, -1);
      if (historyWithoutCurrent.length > 0) {
        threadContext = historyWithoutCurrent.join('\n');
      }
    }

    // Get parent channel ID for context inheritance
    parentConversationId = discord!.getParentChannelId(message) ?? undefined;
  }

  // Fire-and-forget: handler returns immediately, processing happens async
  lockManager
    .acquireLock(conversationId, async () => {
      await handleMessage(discord!, conversationId, content, undefined, threadContext, parentConversationId);
    })
    .catch(async error => {
      console.error('[Discord] Failed to process message:', error);
      try {
        const userMessage = classifyAndFormatError(error as Error);
        await discord!.sendMessage(conversationId, userMessage);
      } catch (sendError) {
        console.error('[Discord] Failed to send error message to user:', sendError);
      }
    });
});
```

**Don't**:
- Don't require mention for DMs (no guild = DM)
- Don't block on thread history fetch errors

**Verify**: `npm run type-check && npm run build`

---

### Task 8: UPDATE `src/adapters/discord.test.ts` - Add tests for new methods

**Why**: New methods need test coverage

**Mirror**: Existing test pattern in `src/adapters/discord.test.ts:74-83`

**Do**:
Add to the mock at the top:
```typescript
const mockClient = {
  // ... existing mocks
  user: { id: '123456789' }, // Add bot user for mention detection
};
```

Add new test describes:
```typescript
describe('mention detection', () => {
  test('should detect when bot is mentioned', () => {
    const adapter = new DiscordAdapter('fake-token-for-testing');
    const mockMessage = {
      mentions: {
        has: jest.fn().mockReturnValue(true),
      },
    } as unknown as import('discord.js').Message;

    expect(adapter.isBotMentioned(mockMessage)).toBe(true);
  });

  test('should return false when bot is not mentioned', () => {
    const adapter = new DiscordAdapter('fake-token-for-testing');
    const mockMessage = {
      mentions: {
        has: jest.fn().mockReturnValue(false),
      },
    } as unknown as import('discord.js').Message;

    expect(adapter.isBotMentioned(mockMessage)).toBe(false);
  });
});

describe('thread detection', () => {
  test('should detect thread channel', () => {
    const adapter = new DiscordAdapter('fake-token-for-testing');
    const mockMessage = {
      channel: {
        isThread: () => true,
        parentId: '987654321',
      },
    } as unknown as import('discord.js').Message;

    expect(adapter.isThread(mockMessage)).toBe(true);
    expect(adapter.getParentChannelId(mockMessage)).toBe('987654321');
  });

  test('should return null for non-thread channel', () => {
    const adapter = new DiscordAdapter('fake-token-for-testing');
    const mockMessage = {
      channel: {
        isThread: () => false,
      },
    } as unknown as import('discord.js').Message;

    expect(adapter.isThread(mockMessage)).toBe(false);
    expect(adapter.getParentChannelId(mockMessage)).toBeNull();
  });
});

describe('mention stripping', () => {
  test('should strip bot mention from message', () => {
    const adapter = new DiscordAdapter('fake-token-for-testing');
    const mockMessage = {
      content: '<@123456789> hello world',
    } as unknown as import('discord.js').Message;

    expect(adapter.stripBotMention(mockMessage)).toBe('hello world');
  });

  test('should strip bot mention with nickname format', () => {
    const adapter = new DiscordAdapter('fake-token-for-testing');
    const mockMessage = {
      content: '<@!123456789> hello world',
    } as unknown as import('discord.js').Message;

    expect(adapter.stripBotMention(mockMessage)).toBe('hello world');
  });
});
```

**Don't**:
- Don't test actual Discord API calls
- Keep mocks simple

**Verify**: `npm test -- src/adapters/discord.test.ts`

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
| `discord.test.ts` | `isBotMentioned` returns true when mentioned | Mention detection works |
| `discord.test.ts` | `isBotMentioned` returns false when not mentioned | Non-mentions ignored |
| `discord.test.ts` | `isThread` detects thread channels | Thread detection works |
| `discord.test.ts` | `getParentChannelId` returns parent ID | Parent lookup works |
| `discord.test.ts` | `stripBotMention` removes mention | Clean message for AI |

### Manual/E2E Validation

**Prerequisites:**
1. Discord bot with `DISCORD_BOT_TOKEN` in `.env`
2. Bot invited to a server with appropriate permissions

**Test Steps:**

```bash
# Terminal 1: Start app
npm run dev
```

**In Discord:**

1. **Test mention requirement (main channel):**
   - Send "hello" without mention → Bot should NOT respond
   - Send "@BotName hello" → Bot SHOULD respond

2. **Test DM behavior:**
   - Send DM to bot without mention → Bot SHOULD respond (DMs don't require mention)

3. **Test thread with context:**
   - Create a thread
   - Have conversation in thread (multiple messages)
   - Mention bot with "@BotName summarize this thread"
   - Verify: Bot reads thread context and responds appropriately

4. **Test thread context inheritance:**
   - In main channel: `/repo remote-coding-agent` (set up codebase)
   - Create thread from a message
   - In thread: `/status`
   - Verify: Thread shows same codebase as parent channel

5. **Test mention stripping:**
   - Send "@BotName /status"
   - Verify: Command works (mention stripped before processing)

### Edge Cases to Test

- [ ] Message with only bot mention (no content) - should be ignored
- [ ] Multiple mentions of bot in same message - should work, mention stripped once
- [ ] Thread with no history (new thread) - should work without context
- [ ] Thread in channel with no codebase - should start fresh
- [ ] Very long thread history (100+ messages) - should fetch up to 100
- [ ] Bot mentioned in middle of message - mention should be stripped correctly

### Regression Check

- [ ] Existing Telegram functionality unaffected
- [ ] Existing GitHub webhook functionality unaffected
- [ ] DMs still work (no mention required)
- [ ] All existing slash commands work when mentioned

---

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Thread history fetch fails | Low | Catch error, proceed without context |
| Bot user is null on startup | Low | Check before accessing, return safe default |
| Rate limiting on history fetch | Medium | Limit to 100 messages, single fetch |
| Parent channel deleted before thread | Low | Null check on parentId |
