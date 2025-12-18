# Plan: Discord Platform Adapter

## Summary

Implement a Discord platform adapter using discord.js v14 to allow chatting with the remote coding agent through Discord. The adapter will implement `IPlatformAdapter`, use polling-based event handling (similar to Telegram), handle message content with the privileged MESSAGE_CONTENT intent, and support streaming responses. Discord has a 2000 character message limit, so messages will be split similar to the Telegram adapter pattern.

## External Research

### Documentation
- [Discord.js Guide](https://discordjs.guide/) - Official guide for discord.js
  - Key sections: Getting started, Gateway intents, Message handling
- [Discord.js Documentation](https://discord.js.org/) - API reference
- [Discord Developer Portal](https://discord.com/developers/docs) - For creating bot application and getting token
- [Gateway Intents](https://discordjs.guide/popular-topics/intents.html) - Required for message access

### Gotchas & Best Practices Found
1. **MESSAGE_CONTENT Privileged Intent Required**: As of September 2022, bots need the MESSAGE_CONTENT intent enabled in the Developer Portal AND in code to read message content. Without it, bots can only read messages where they're mentioned, DMs, and their own messages.
2. **2000 Character Limit**: Discord messages are limited to 2000 characters. Must split longer messages.
3. **Rate Limits**: 5 messages per 5 seconds per channel. Global limit of 50 requests/second.
4. **Event Names Changed in v14**: Use `messageCreate` instead of `message`.
5. **GatewayIntentBits Enum**: Use `GatewayIntentBits.Guilds`, `GatewayIntentBits.GuildMessages`, `GatewayIntentBits.MessageContent`, `GatewayIntentBits.DirectMessages`.
6. **Partials for DMs**: Need `Partials.Channel` for DM support.
7. **No Webhook Server Needed**: Unlike GitHub, Discord uses WebSocket-based event listening (polling pattern), similar to Telegram.

### Rate Limit Handling
- discord.js has built-in rate limit handling
- No need to implement manual rate limiting for MVP
- If rate limited, library queues requests automatically

## Patterns to Mirror

### From `src/adapters/telegram.ts:11-23` - Constructor Pattern
```typescript
export class TelegramAdapter implements IPlatformAdapter {
  private bot: Telegraf;
  private streamingMode: 'stream' | 'batch';

  constructor(token: string, mode: 'stream' | 'batch' = 'stream') {
    // Disable handler timeout to support long-running AI operations
    // Default is 90 seconds which is too short for complex coding tasks
    this.bot = new Telegraf(token, {
      handlerTimeout: Infinity,
    });
    this.streamingMode = mode;
    console.log(`[Telegram] Adapter initialized (mode: ${mode}, timeout: disabled)`);
  }
```

### From `src/adapters/telegram.ts:34-50` - sendMessage with Splitting
```typescript
async sendMessage(chatId: string, message: string): Promise<void> {
  const id = parseInt(chatId);
  console.log(`[Telegram] sendMessage called, length=${String(message.length)}`);

  if (message.length <= MAX_LENGTH) {
    // Short message: try MarkdownV2 formatting
    await this.sendFormattedChunk(id, message);
  } else {
    // Long message: split by paragraphs, format each chunk
    console.log(`[Telegram] Message too long (${String(message.length)}), splitting by paragraphs`);
    const chunks = this.splitIntoParagraphChunks(message, MAX_LENGTH - 200);

    for (const chunk of chunks) {
      await this.sendFormattedChunk(id, chunk);
    }
  }
}
```

### From `src/adapters/telegram.ts:132-141` - Interface Methods
```typescript
getStreamingMode(): 'stream' | 'batch' {
  return this.streamingMode;
}

getPlatformType(): string {
  return 'telegram';
}
```

### From `src/adapters/telegram.ts:156-171` - Start/Stop Pattern
```typescript
async start(): Promise<void> {
  // Drop pending updates on startup to prevent reprocessing messages after container restart
  await this.bot.launch({
    dropPendingUpdates: true,
  });
  console.log('[Telegram] Bot started (polling mode, pending updates dropped)');
}

stop(): void {
  this.bot.stop();
  console.log('[Telegram] Bot stopped');
}
```

### From `src/index.ts:191-219` - Message Handler Setup Pattern
```typescript
// Initialize platform adapter (Telegram)
const streamingMode = (process.env.TELEGRAM_STREAMING_MODE ?? 'stream') as 'stream' | 'batch';
const telegram = new TelegramAdapter(process.env.TELEGRAM_BOT_TOKEN!, streamingMode);

// Handle text messages
telegram.getBot().on('message', async ctx => {
  if (!('text' in ctx.message)) return;
  const conversationId = telegram.getConversationId(ctx);
  const message = ctx.message.text;

  if (!message) return;

  // Fire-and-forget: handler returns immediately, processing happens async
  lockManager
    .acquireLock(conversationId, async () => {
      await handleMessage(telegram, conversationId, message);
    })
    .catch(async error => {
      console.error('[Telegram] Failed to process message:', error);
      try {
        const userMessage = classifyAndFormatError(error as Error);
        await telegram.sendMessage(conversationId, userMessage);
      } catch (sendError) {
        console.error('[Telegram] Failed to send error message to user:', sendError);
      }
    });
});
```

### From `src/types/index.ts:49-74` - IPlatformAdapter Interface
```typescript
export interface IPlatformAdapter {
  sendMessage(conversationId: string, message: string): Promise<void>;
  getStreamingMode(): 'stream' | 'batch';
  getPlatformType(): string;
  start(): Promise<void>;
  stop(): void;
}
```

### From `src/adapters/telegram.test.ts:13-37` - Test Pattern
```typescript
describe('TelegramAdapter', () => {
  describe('streaming mode configuration', () => {
    test('should return batch mode when configured', () => {
      const adapter = new TelegramAdapter('fake-token-for-testing', 'batch');
      expect(adapter.getStreamingMode()).toBe('batch');
    });

    test('should default to stream mode', () => {
      const adapter = new TelegramAdapter('fake-token-for-testing');
      expect(adapter.getStreamingMode()).toBe('stream');
    });
  });
```

## Files to Change

| File | Action | Justification |
|------|--------|---------------|
| `package.json` | UPDATE | Add discord.js dependency |
| `src/adapters/discord.ts` | CREATE | New Discord adapter implementing IPlatformAdapter |
| `src/adapters/discord.test.ts` | CREATE | Unit tests for Discord adapter |
| `src/index.ts` | UPDATE | Initialize Discord adapter, register message handlers |
| `.env.example` | UPDATE | Add DISCORD_BOT_TOKEN and DISCORD_STREAMING_MODE |

## NOT Building

- ❌ Discord slash commands (Application Commands) - Not needed for MVP, can add later
- ❌ Discord bot presence/status updates - Unnecessary complexity
- ❌ Discord embed messages - Plain text is sufficient, matches other adapters
- ❌ Discord reactions - Not part of current conversation model
- ❌ Voice channel support - Out of scope
- ❌ Server management commands - Not relevant to coding agent
- ❌ Multi-guild optimization/sharding - Only needed for 2500+ servers

## Tasks

### Task 1: UPDATE package.json - Add discord.js Dependency

**Why**: Need discord.js library to interact with Discord API.

**Mirror**: Existing dependency pattern in `package.json:32-40`

**Do**:
Add to dependencies section:
```json
"discord.js": "^14.16.0"
```

**Don't**:
- Don't add dev dependencies for discord.js (types are included)
- Don't add version lower than 14.x (we need v14 for modern intents API)

**Verify**: `npm install && npm run type-check`

---

### Task 2: UPDATE .env.example - Add Discord Environment Variables

**Why**: Users need to know what environment variables to configure.

**Mirror**: Existing Telegram config pattern in `.env.example`

**Do**:
Add to .env.example after Telegram section:
```env
# Discord
DISCORD_BOT_TOKEN=<from Discord Developer Portal>
DISCORD_STREAMING_MODE=stream  # stream or batch
```

**Don't**:
- Don't add DISCORD_CLIENT_ID - not needed for bot login
- Don't add webhook-related vars - Discord uses WebSocket, not webhooks

**Verify**: Visual inspection of .env.example

---

### Task 3: CREATE src/adapters/discord.ts - Discord Adapter Implementation

**Why**: Core adapter implementing IPlatformAdapter for Discord platform.

**Mirror**: `src/adapters/telegram.ts` structure exactly

**Do**:
```typescript
/**
 * Discord platform adapter using discord.js v14
 * Handles message sending with 2000 character limit splitting
 */
import { Client, GatewayIntentBits, Partials, Message, Events } from 'discord.js';
import { IPlatformAdapter } from '../types';

const MAX_LENGTH = 2000;

export class DiscordAdapter implements IPlatformAdapter {
  private client: Client;
  private streamingMode: 'stream' | 'batch';
  private messageHandler: ((message: Message) => Promise<void>) | null = null;

  constructor(token: string, mode: 'stream' | 'batch' = 'stream') {
    this.client = new Client({
      intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
        GatewayIntentBits.DirectMessages,
      ],
      partials: [Partials.Channel], // Required for DM support
    });
    this.streamingMode = mode;
    console.log(`[Discord] Adapter initialized (mode: ${mode})`);

    // Store token for login in start()
    (this.client as unknown as { _token: string })._token = token;
  }

  /**
   * Send a message to a Discord channel
   * Automatically splits messages longer than 2000 characters
   */
  async sendMessage(channelId: string, message: string): Promise<void> {
    console.log(`[Discord] sendMessage called, length=${String(message.length)}`);

    const channel = await this.client.channels.fetch(channelId);
    if (!channel || !channel.isTextBased()) {
      console.error('[Discord] Invalid or non-text channel:', channelId);
      return;
    }

    if (message.length <= MAX_LENGTH) {
      await channel.send(message);
    } else {
      console.log(`[Discord] Message too long (${String(message.length)}), splitting by paragraphs`);
      const chunks = this.splitIntoParagraphChunks(message, MAX_LENGTH - 100);

      for (const chunk of chunks) {
        await channel.send(chunk);
      }
    }
  }

  /**
   * Split message into chunks by paragraph boundaries
   */
  private splitIntoParagraphChunks(message: string, maxLength: number): string[] {
    const paragraphs = message.split(/\n\n+/);
    const chunks: string[] = [];
    let currentChunk = '';

    for (const para of paragraphs) {
      const newLength = currentChunk.length + para.length + 2;

      if (newLength > maxLength && currentChunk) {
        chunks.push(currentChunk);
        currentChunk = para;
      } else {
        currentChunk += (currentChunk ? '\n\n' : '') + para;
      }
    }

    if (currentChunk) {
      chunks.push(currentChunk);
    }

    // If any chunk is still too long, split by lines as fallback
    const finalChunks: string[] = [];
    for (const chunk of chunks) {
      if (chunk.length <= maxLength) {
        finalChunks.push(chunk);
      } else {
        // Fallback: split by lines
        const lines = chunk.split('\n');
        let subChunk = '';
        for (const line of lines) {
          if (subChunk.length + line.length + 1 > maxLength) {
            if (subChunk) finalChunks.push(subChunk);
            subChunk = line;
          } else {
            subChunk += (subChunk ? '\n' : '') + line;
          }
        }
        if (subChunk) finalChunks.push(subChunk);
      }
    }

    console.log(`[Discord] Split into ${String(finalChunks.length)} chunks`);
    return finalChunks;
  }

  /**
   * Get the discord.js Client instance
   */
  getClient(): Client {
    return this.client;
  }

  /**
   * Get the configured streaming mode
   */
  getStreamingMode(): 'stream' | 'batch' {
    return this.streamingMode;
  }

  /**
   * Get platform type
   */
  getPlatformType(): string {
    return 'discord';
  }

  /**
   * Extract conversation ID from Discord message
   * Uses channel ID as the conversation identifier
   */
  getConversationId(message: Message): string {
    return message.channelId;
  }

  /**
   * Register a message handler for incoming messages
   * Must be called before start()
   */
  onMessage(handler: (message: Message) => Promise<void>): void {
    this.messageHandler = handler;
  }

  /**
   * Start the bot (logs in and starts listening)
   */
  async start(): Promise<void> {
    // Register message handler before login
    this.client.on(Events.MessageCreate, async (message: Message) => {
      // Ignore bot messages to prevent loops
      if (message.author.bot) return;

      if (this.messageHandler) {
        await this.messageHandler(message);
      }
    });

    // Log when ready
    this.client.once(Events.ClientReady, (readyClient) => {
      console.log(`[Discord] Bot logged in as ${readyClient.user.tag}`);
    });

    // Login with stored token
    const token = (this.client as unknown as { _token: string })._token;
    await this.client.login(token);
    console.log('[Discord] Bot started (WebSocket connection established)');
  }

  /**
   * Stop the bot gracefully
   */
  stop(): void {
    this.client.destroy();
    console.log('[Discord] Bot stopped');
  }
}
```

**Don't**:
- Don't add Discord-specific markdown conversion yet - plain text is fine for MVP
- Don't add typing indicators - can add as enhancement later
- Don't store the token directly on the instance for security (use the _token pattern to keep it private)

**Verify**: `npm run type-check`

---

### Task 4: CREATE src/adapters/discord.test.ts - Unit Tests

**Why**: Ensure adapter works correctly and matches interface contract.

**Mirror**: `src/adapters/telegram.test.ts` structure

**Do**:
```typescript
/**
 * Unit tests for Discord adapter
 */
import { DiscordAdapter } from './discord';

// Mock discord.js
jest.mock('discord.js', () => {
  const mockChannel = {
    isTextBased: () => true,
    send: jest.fn().mockResolvedValue(undefined),
  };

  const mockClient = {
    channels: {
      fetch: jest.fn().mockResolvedValue(mockChannel),
    },
    on: jest.fn(),
    once: jest.fn(),
    login: jest.fn().mockResolvedValue('token'),
    destroy: jest.fn(),
  };

  return {
    Client: jest.fn(() => mockClient),
    GatewayIntentBits: {
      Guilds: 1,
      GuildMessages: 2,
      MessageContent: 4,
      DirectMessages: 8,
    },
    Partials: {
      Channel: 0,
    },
    Events: {
      MessageCreate: 'messageCreate',
      ClientReady: 'ready',
    },
  };
});

describe('DiscordAdapter', () => {
  describe('streaming mode configuration', () => {
    test('should return batch mode when configured', () => {
      const adapter = new DiscordAdapter('fake-token-for-testing', 'batch');
      expect(adapter.getStreamingMode()).toBe('batch');
    });

    test('should default to stream mode', () => {
      const adapter = new DiscordAdapter('fake-token-for-testing');
      expect(adapter.getStreamingMode()).toBe('stream');
    });

    test('should return stream mode when explicitly configured', () => {
      const adapter = new DiscordAdapter('fake-token-for-testing', 'stream');
      expect(adapter.getStreamingMode()).toBe('stream');
    });
  });

  describe('platform type', () => {
    test('should return discord as platform type', () => {
      const adapter = new DiscordAdapter('fake-token-for-testing');
      expect(adapter.getPlatformType()).toBe('discord');
    });
  });

  describe('client instance', () => {
    test('should provide access to client instance', () => {
      const adapter = new DiscordAdapter('fake-token-for-testing');
      const client = adapter.getClient();
      expect(client).toBeDefined();
    });
  });

  describe('conversation ID extraction', () => {
    test('should extract channel ID from message', () => {
      const adapter = new DiscordAdapter('fake-token-for-testing');
      const mockMessage = {
        channelId: '1234567890',
      } as unknown as import('discord.js').Message;

      expect(adapter.getConversationId(mockMessage)).toBe('1234567890');
    });
  });

  describe('message sending', () => {
    test('should send short messages directly', async () => {
      const adapter = new DiscordAdapter('fake-token-for-testing');
      const client = adapter.getClient();
      const mockChannel = await client.channels.fetch('123');

      await adapter.sendMessage('123', 'Hello, World!');

      expect(client.channels.fetch).toHaveBeenCalledWith('123');
      expect(mockChannel?.send).toHaveBeenCalledWith('Hello, World!');
    });

    test('should split long messages into chunks', async () => {
      const adapter = new DiscordAdapter('fake-token-for-testing');
      const client = adapter.getClient();
      const mockChannel = await client.channels.fetch('123');

      // Create a message longer than 2000 chars with paragraph breaks
      const para1 = 'a'.repeat(1500);
      const para2 = 'b'.repeat(1500);
      const longMessage = `${para1}\n\n${para2}`;

      await adapter.sendMessage('123', longMessage);

      // Should have been split and sent as multiple messages
      expect((mockChannel?.send as jest.Mock).mock.calls.length).toBeGreaterThan(1);
    });
  });

  describe('lifecycle', () => {
    test('should login on start', async () => {
      const adapter = new DiscordAdapter('fake-token-for-testing');
      const client = adapter.getClient();

      await adapter.start();

      expect(client.login).toHaveBeenCalledWith('fake-token-for-testing');
    });

    test('should destroy client on stop', () => {
      const adapter = new DiscordAdapter('fake-token-for-testing');
      const client = adapter.getClient();

      adapter.stop();

      expect(client.destroy).toHaveBeenCalled();
    });
  });
});
```

**Don't**:
- Don't add integration tests - those would require a real Discord bot token

**Verify**: `npm test -- src/adapters/discord.test.ts`

---

### Task 5: UPDATE src/index.ts - Initialize Discord Adapter

**Why**: Register Discord adapter and wire up message handling like Telegram.

**Mirror**: `src/index.ts:191-219` (Telegram initialization pattern)

**Do**:
1. Add import at top:
```typescript
import { DiscordAdapter } from './adapters/discord';
```

2. Add Discord adapter initialization after GitHub adapter section (around line 75), before Express setup:
```typescript
// Initialize Discord adapter (conditional)
let discord: DiscordAdapter | null = null;
if (process.env.DISCORD_BOT_TOKEN) {
  const discordStreamingMode = (process.env.DISCORD_STREAMING_MODE ?? 'stream') as 'stream' | 'batch';
  discord = new DiscordAdapter(process.env.DISCORD_BOT_TOKEN, discordStreamingMode);

  // Register message handler
  discord.onMessage(async (message) => {
    const conversationId = discord!.getConversationId(message);
    const content = message.content;

    if (!content) return;

    // Fire-and-forget: handler returns immediately, processing happens async
    lockManager
      .acquireLock(conversationId, async () => {
        await handleMessage(discord!, conversationId, content);
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

  await discord.start();
} else {
  console.log('[Discord] Adapter not initialized (missing DISCORD_BOT_TOKEN)');
}
```

3. Update graceful shutdown to include Discord:
```typescript
const shutdown = (): void => {
  console.log('[App] Shutting down gracefully...');
  telegram.stop();
  discord?.stop();  // Add this line
  void pool.end().then(() => {
    console.log('[Database] Connection pool closed');
    process.exit(0);
  });
};
```

4. Update the "ready" log message to mention Discord:
```typescript
console.log('[App] Remote Coding Agent is ready!');
console.log('[App] Send messages to your Telegram bot to get started');
if (discord) {
  console.log('[App] Discord bot is also running');
}
console.log('[App] Test endpoint available: POST http://localhost:' + String(port) + '/test/message');
```

**Don't**:
- Don't make Discord required - keep it optional like GitHub
- Don't add Discord-specific Express endpoints - not needed (uses WebSocket)
- Don't modify required env vars array - Discord is optional

**Verify**: `npm run type-check && npm run build`

---

## Validation Strategy

### Automated Checks
- [ ] `npm install` - Dependencies install successfully
- [ ] `npm run type-check` - Types valid
- [ ] `npm run lint` - No lint errors
- [ ] `npm run format:check` - Formatting correct
- [ ] `npm test` - All tests pass (including new discord.test.ts)
- [ ] `npm run build` - Build succeeds

### New Tests to Write

| Test File | Test Case | What It Validates |
|-----------|-----------|-------------------|
| `src/adapters/discord.test.ts` | streaming mode configuration | Adapter respects stream/batch mode |
| `src/adapters/discord.test.ts` | platform type | Returns 'discord' |
| `src/adapters/discord.test.ts` | client instance | getClient() works |
| `src/adapters/discord.test.ts` | conversation ID extraction | Extracts channel ID from message |
| `src/adapters/discord.test.ts` | message sending | Sends to correct channel |
| `src/adapters/discord.test.ts` | long message splitting | Splits messages over 2000 chars |
| `src/adapters/discord.test.ts` | lifecycle - start | Calls client.login |
| `src/adapters/discord.test.ts` | lifecycle - stop | Calls client.destroy |

### Manual/E2E Validation

**Prerequisites:**
1. Create a Discord Application in [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a Bot for the application
3. Enable "MESSAGE CONTENT INTENT" in Bot settings (Privileged Gateway Intents section)
4. Copy the bot token
5. Generate an invite URL with `applications.commands` and `bot` scopes, `Send Messages` and `Read Message History` permissions
6. Invite bot to a test server

**Test Steps:**
```bash
# 1. Add token to .env
echo "DISCORD_BOT_TOKEN=your-bot-token-here" >> .env

# 2. Start application
npm run dev

# 3. Verify startup logs show:
# [Discord] Adapter initialized (mode: stream)
# [Discord] Bot logged in as YourBotName#1234
# [Discord] Bot started (WebSocket connection established)

# 4. In Discord test server, send message to channel where bot can see:
# "/help"
# Should receive help message response

# 5. Test slash command:
# "/status"
# Should show current conversation status

# 6. Test long message handling:
# Send a message that will generate >2000 char response
# Verify it splits correctly without errors
```

### Edge Cases to Test
- [ ] Empty message content - Should be ignored
- [ ] Bot's own messages - Should be ignored (no infinite loops)
- [ ] Message in channel bot can't respond to - Should log error, not crash
- [ ] Very long messages (>4000 chars) - Should split into multiple chunks
- [ ] DM to bot - Should work with Partials.Channel enabled
- [ ] Application restart - Should reconnect without issues

### Regression Check
- [ ] Telegram adapter still works: Send message via Telegram, verify response
- [ ] GitHub adapter still works (if configured): Create issue with @mention
- [ ] Test adapter still works: `curl -X POST http://localhost:3000/test/message -H "Content-Type: application/json" -d '{"conversationId":"test","message":"/help"}'`
- [ ] All existing tests pass: `npm test`

## Risks

1. **MESSAGE_CONTENT Intent Not Enabled**: If user forgets to enable in Developer Portal, bot won't receive message content. Mitigation: Clear documentation in .env.example and error message if content is empty.

2. **Rate Limiting**: High message volume could trigger rate limits. Mitigation: discord.js handles this automatically with built-in queue.

3. **Token Exposure**: Bot token is sensitive. Mitigation: Only loaded from env var, never logged.

4. **Large Guild Issues**: If bot joins large servers, may hit gateway limits. Mitigation: Out of scope for MVP - sharding can be added later if needed.
