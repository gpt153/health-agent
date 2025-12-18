# Plan: Slack Platform Adapter

## Summary

Add a Slack platform adapter to the remote coding agent that mirrors Discord's functionality. The adapter will use Slack's Bolt SDK with Socket Mode (no public HTTP endpoints needed), support @mention activation, and handle thread conversations identically to Discord - where each thread becomes its own conversation context. User flow: @mention-agent in main channel to `/clone`, then @mention in threads to work on the cloned repo, with `/worktree` for parallel work.

## External Research

### Documentation
- [Slack Bolt for JavaScript - Socket Mode](https://tools.slack.dev/bolt-js/concepts/socket-mode/) - Primary SDK reference
- [Slack Permission Scopes](https://api.slack.com/scopes) - Bot token scopes reference
- [Slack Events API](https://docs.slack.dev/apis/events-api/) - Event types and subscriptions
- [Slack Thread Handling](https://api.slack.com/methods/conversations.replies) - `thread_ts` for threading

### Gotchas & Best Practices Found
- **Socket Mode requires App Token**: Need `xapp-` token with `connections:write` scope in addition to bot token
- **Thread handling**: Use `thread_ts || ts` pattern - if `thread_ts` exists, we're in a thread; use `ts` as conversation ID
- **Message limits**: Slack has 40,000 character limit (vs Discord's 2000), but practical limit is ~4000 for readability
- **@mention detection**: App mention events (`app_mention`) are separate from regular messages
- **Socket Mode not for marketplace**: Fine for internal/single-developer tools like this project
- **Channel types**: `channels:history` for public, `groups:history` for private, `im:history` for DMs

## Patterns to Mirror

### Discord Adapter Structure (`src/adapters/discord.ts:11-40`)
```typescript
export class DiscordAdapter implements IPlatformAdapter {
  private client: Client;
  private streamingMode: 'stream' | 'batch';
  private token: string;
  private messageHandler: ((message: Message) => Promise<void>) | null = null;
  private allowedUserIds: string[];

  constructor(token: string, mode: 'stream' | 'batch' = 'stream') {
    this.client = new Client({
      intents: [...],
      partials: [...],
    });
    this.streamingMode = mode;
    this.token = token;
    // Parse user whitelist...
  }
}
```

### Discord Auth Pattern (`src/utils/discord-auth.ts:10-39`)
```typescript
export function parseAllowedUserIds(envValue: string | undefined): string[] {
  if (!envValue || envValue.trim() === '') {
    return [];
  }
  return envValue
    .split(',')
    .map(id => id.trim())
    .filter(id => id !== '' && /^\d+$/.test(id));
}

export function isDiscordUserAuthorized(userId: string | undefined, allowedIds: string[]): boolean {
  if (allowedIds.length === 0) return true;
  if (userId === undefined || userId.trim() === '') return false;
  return allowedIds.includes(userId);
}
```

### Discord Thread Handling (`src/adapters/discord.ts:154-215`)
```typescript
isThread(message: Message): boolean {
  return message.channel.isThread();
}

getParentChannelId(message: Message): string | null {
  if (message.channel.isThread()) {
    return message.channel.parentId;
  }
  return null;
}

async fetchThreadHistory(message: Message): Promise<string[]> {
  if (!message.channel.isThread()) return [];
  const messages = await message.channel.messages.fetch({ limit: 100 });
  const sorted = [...messages.values()].reverse();
  return sorted.map(msg => {
    const author = msg.author.bot ? '[Bot]' : (msg.author.displayName || msg.author.username);
    return `${author}: ${msg.content}`;
  });
}

getConversationId(message: Message): string {
  return message.channelId; // Thread ID for threads, channel ID otherwise
}
```

### Discord Message Handler Registration (`src/index.ts:103-160`)
```typescript
discord.onMessage(async message => {
  const conversationId = discord!.getConversationId(message);
  if (!message.content) return;

  const isDM = !message.guild;
  if (!isDM && !discord!.isBotMentioned(message)) return;

  const content = discord!.stripBotMention(message);
  if (!content) return;

  let threadContext: string | undefined;
  let parentConversationId: string | undefined;

  if (discord!.isThread(message)) {
    const history = await discord!.fetchThreadHistory(message);
    if (history.length > 0) {
      const historyWithoutCurrent = history.slice(0, -1);
      if (historyWithoutCurrent.length > 0) {
        threadContext = historyWithoutCurrent.join('\n');
      }
    }
    parentConversationId = discord!.getParentChannelId(message) ?? undefined;
  }

  lockManager.acquireLock(conversationId, async () => {
    await handleMessage(discord!, conversationId, content, undefined, threadContext, parentConversationId);
  }).catch(...);
});
```

### Test Pattern (`src/adapters/telegram.test.ts`)
```typescript
describe('TelegramAdapter', () => {
  describe('streaming mode configuration', () => {
    test('should return batch mode when configured', () => {
      const adapter = new TelegramAdapter('fake-token-for-testing', 'batch');
      expect(adapter.getStreamingMode()).toBe('batch');
    });
  });
});
```

## Files to Change

| File | Action | Justification |
|------|--------|---------------|
| `src/adapters/slack.ts` | CREATE | New Slack adapter implementing IPlatformAdapter |
| `src/utils/slack-auth.ts` | CREATE | Slack user authorization utilities (mirror discord-auth.ts) |
| `src/utils/slack-auth.test.ts` | CREATE | Unit tests for auth utilities |
| `src/adapters/slack.test.ts` | CREATE | Unit tests for adapter |
| `src/index.ts` | UPDATE | Register Slack adapter conditionally |
| `.env.example` | UPDATE | Add Slack environment variables |
| `docs/slack-setup.md` | CREATE | Guide for setting up Slack bot |
| `package.json` | UPDATE | Add @slack/bolt dependency |

## NOT Building

- **Custom Slack message formatting**: Slack's mrkdwn is simpler than Discord's - basic text works fine
- **Slash commands in Slack**: Users will type `/clone` etc. as text, not Slack slash commands
- **Block Kit messages**: Plain text is sufficient for this use case
- **Interactive components**: Buttons, modals, etc. - out of scope
- **HTTP webhook mode**: Socket Mode is sufficient and simpler for single-developer tool

## Tasks

### Task 1: Add @slack/bolt dependency

**Why**: Need Slack's official SDK for Socket Mode and message handling

**Mirror**: `package.json:36` (discord.js dependency pattern)

**Do**:
```bash
npm install @slack/bolt
```

Verify in package.json that @slack/bolt is added to dependencies.

**Don't**:
- Don't install @slack/web-api separately (Bolt includes it)
- Don't use @slack/socket-mode directly (Bolt wraps it)

**Verify**: `npm ls @slack/bolt`

---

### Task 2: Create Slack auth utilities (`src/utils/slack-auth.ts`)

**Why**: Whitelist-based access control matching the project's auth pattern for Discord/Telegram

**Mirror**: `src/utils/discord-auth.ts` (exact same pattern)

**Do**:
```typescript
/**
 * Slack user authorization utilities
 * Parses and validates Slack user IDs for whitelist-based access control
 */

/**
 * Parse comma-separated Slack user IDs from environment variable
 * Returns empty array if not set or invalid (open access mode)
 */
export function parseAllowedUserIds(envValue: string | undefined): string[] {
  if (!envValue || envValue.trim() === '') {
    return [];
  }

  return envValue
    .split(',')
    .map(id => id.trim())
    .filter(id => id !== '' && /^[UW][A-Z0-9]+$/.test(id)); // Slack user IDs: U or W prefix + alphanumeric
}

/**
 * Check if a Slack user ID is authorized
 * Returns true if:
 * - allowedIds is empty (open access mode)
 * - userId is in allowedIds
 */
export function isSlackUserAuthorized(userId: string | undefined, allowedIds: string[]): boolean {
  if (allowedIds.length === 0) {
    return true;
  }

  if (userId === undefined || userId.trim() === '') {
    return false;
  }

  return allowedIds.includes(userId);
}
```

**Don't**:
- Don't validate against Slack API (just format validation)
- Don't use numeric IDs (Slack uses alphanumeric strings like `U1234ABCD`)

**Verify**: `npm run type-check`

---

### Task 3: Create Slack auth tests (`src/utils/slack-auth.test.ts`)

**Why**: Unit tests for auth functions matching project patterns

**Mirror**: `src/utils/telegram-auth.test.ts`

**Do**:
```typescript
/**
 * Unit tests for Slack authorization utilities
 */
import { parseAllowedUserIds, isSlackUserAuthorized } from './slack-auth';

describe('slack-auth', () => {
  describe('parseAllowedUserIds', () => {
    test('should return empty array for undefined', () => {
      expect(parseAllowedUserIds(undefined)).toEqual([]);
    });

    test('should return empty array for empty string', () => {
      expect(parseAllowedUserIds('')).toEqual([]);
    });

    test('should return empty array for whitespace-only string', () => {
      expect(parseAllowedUserIds('   ')).toEqual([]);
    });

    test('should parse single user ID', () => {
      expect(parseAllowedUserIds('U1234ABCD')).toEqual(['U1234ABCD']);
    });

    test('should parse multiple user IDs', () => {
      expect(parseAllowedUserIds('U1234ABCD,W5678EFGH')).toEqual(['U1234ABCD', 'W5678EFGH']);
    });

    test('should handle whitespace around IDs', () => {
      expect(parseAllowedUserIds(' U1234ABCD , W5678EFGH ')).toEqual(['U1234ABCD', 'W5678EFGH']);
    });

    test('should filter out invalid IDs', () => {
      expect(parseAllowedUserIds('U1234ABCD,invalid,W5678EFGH')).toEqual(['U1234ABCD', 'W5678EFGH']);
    });

    test('should handle empty segments', () => {
      expect(parseAllowedUserIds('U1234ABCD,,W5678EFGH')).toEqual(['U1234ABCD', 'W5678EFGH']);
    });
  });

  describe('isSlackUserAuthorized', () => {
    describe('open access mode (empty allowedIds)', () => {
      test('should allow any user ID when no whitelist', () => {
        expect(isSlackUserAuthorized('U1234ABCD', [])).toBe(true);
      });

      test('should allow undefined user ID when no whitelist', () => {
        expect(isSlackUserAuthorized(undefined, [])).toBe(true);
      });
    });

    describe('whitelist mode', () => {
      const allowedIds = ['U1234ABCD', 'W5678EFGH', 'U9999ZZZZ'];

      test('should allow authorized user', () => {
        expect(isSlackUserAuthorized('W5678EFGH', allowedIds)).toBe(true);
      });

      test('should reject unauthorized user', () => {
        expect(isSlackUserAuthorized('UNOTALLOWED', allowedIds)).toBe(false);
      });

      test('should reject undefined user ID', () => {
        expect(isSlackUserAuthorized(undefined, allowedIds)).toBe(false);
      });
    });
  });
});
```

**Verify**: `npm test -- src/utils/slack-auth.test.ts`

---

### Task 4: Create Slack adapter (`src/adapters/slack.ts`)

**Why**: Main adapter implementing IPlatformAdapter for Slack

**Mirror**: `src/adapters/discord.ts` (structure, methods, patterns)

**Do**:
```typescript
/**
 * Slack platform adapter using @slack/bolt with Socket Mode
 * Handles message sending with 4000 character limit splitting (practical readability limit)
 */
import { App, LogLevel } from '@slack/bolt';
import { IPlatformAdapter } from '../types';
import { parseAllowedUserIds, isSlackUserAuthorized } from '../utils/slack-auth';

const MAX_LENGTH = 4000; // Practical limit for readability (Slack allows 40k)

/**
 * Slack message event context for the message handler
 */
export interface SlackMessageEvent {
  text: string;
  user: string;
  channel: string;
  ts: string;
  thread_ts?: string;
}

export class SlackAdapter implements IPlatformAdapter {
  private app: App;
  private streamingMode: 'stream' | 'batch';
  private messageHandler: ((event: SlackMessageEvent) => Promise<void>) | null = null;
  private allowedUserIds: string[];

  constructor(
    botToken: string,
    appToken: string,
    mode: 'stream' | 'batch' = 'batch'
  ) {
    this.app = new App({
      token: botToken,
      socketMode: true,
      appToken: appToken,
      logLevel: LogLevel.INFO,
    });
    this.streamingMode = mode;

    // Parse Slack user whitelist (optional - empty = open access)
    this.allowedUserIds = parseAllowedUserIds(process.env.SLACK_ALLOWED_USER_IDS);
    if (this.allowedUserIds.length > 0) {
      console.log(`[Slack] User whitelist enabled (${String(this.allowedUserIds.length)} users)`);
    } else {
      console.log('[Slack] User whitelist disabled (open access)');
    }

    console.log(`[Slack] Adapter initialized (mode: ${mode})`);
  }

  /**
   * Send a message to a Slack channel/thread
   * Automatically splits messages longer than 4000 characters
   */
  async sendMessage(channelId: string, message: string): Promise<void> {
    console.log(`[Slack] sendMessage called, length=${String(message.length)}`);

    // Parse channelId - may include thread_ts as "channel:thread_ts"
    const [channel, threadTs] = channelId.includes(':')
      ? channelId.split(':')
      : [channelId, undefined];

    if (message.length <= MAX_LENGTH) {
      await this.app.client.chat.postMessage({
        channel,
        text: message,
        thread_ts: threadTs,
      });
    } else {
      console.log(`[Slack] Message too long (${String(message.length)}), splitting by paragraphs`);
      const chunks = this.splitIntoParagraphChunks(message, MAX_LENGTH - 100);

      for (const chunk of chunks) {
        await this.app.client.chat.postMessage({
          channel,
          text: chunk,
          thread_ts: threadTs,
        });
      }
    }
  }

  /**
   * Split message into chunks by paragraph boundaries
   * Paragraphs are separated by double newlines
   */
  private splitIntoParagraphChunks(message: string, maxLength: number): string[] {
    const paragraphs = message.split(/\n\n+/);
    const chunks: string[] = [];
    let currentChunk = '';

    for (const para of paragraphs) {
      const newLength = currentChunk.length + para.length + 2; // +2 for \n\n

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

    // Fallback: split by lines if any chunk is still too long
    const finalChunks: string[] = [];
    for (const chunk of chunks) {
      if (chunk.length <= maxLength) {
        finalChunks.push(chunk);
      } else {
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

    console.log(`[Slack] Split into ${String(finalChunks.length)} chunks`);
    return finalChunks;
  }

  /**
   * Get the Bolt App instance
   */
  getApp(): App {
    return this.app;
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
    return 'slack';
  }

  /**
   * Check if a message is in a thread
   */
  isThread(event: SlackMessageEvent): boolean {
    return event.thread_ts !== undefined && event.thread_ts !== event.ts;
  }

  /**
   * Get parent channel ID for a thread message
   * Returns null if not in a thread
   */
  getParentConversationId(event: SlackMessageEvent): string | null {
    if (this.isThread(event)) {
      // Parent conversation is the channel with the original message ts
      return `${event.channel}:${event.thread_ts}`;
    }
    return null;
  }

  /**
   * Fetch thread history (messages in the thread)
   * Returns messages in chronological order (oldest first)
   */
  async fetchThreadHistory(event: SlackMessageEvent): Promise<string[]> {
    if (!this.isThread(event) || !event.thread_ts) {
      return [];
    }

    try {
      const result = await this.app.client.conversations.replies({
        channel: event.channel,
        ts: event.thread_ts,
        limit: 100,
      });

      if (!result.messages) {
        return [];
      }

      // Messages are already in chronological order
      return result.messages.map(msg => {
        const author = msg.bot_id ? '[Bot]' : `<@${msg.user}>`;
        return `${author}: ${msg.text ?? ''}`;
      });
    } catch (error) {
      console.error('[Slack] Failed to fetch thread history:', error);
      return [];
    }
  }

  /**
   * Get conversation ID from Slack event
   * For threads: returns "channel:thread_ts" to maintain thread context
   * For non-threads: returns channel ID only
   */
  getConversationId(event: SlackMessageEvent): string {
    // If in a thread, use "channel:thread_ts" format
    // This ensures thread replies stay in the same conversation
    if (event.thread_ts) {
      return `${event.channel}:${event.thread_ts}`;
    }
    // If starting a new conversation in channel, use "channel:ts"
    // so future replies create a thread
    return `${event.channel}:${event.ts}`;
  }

  /**
   * Strip bot mention from message text
   */
  stripBotMention(text: string): string {
    // Slack mentions are <@USERID> format
    // Remove all user mentions at the start of the message
    return text.replace(/^<@[UW][A-Z0-9]+>\s*/g, '').trim();
  }

  /**
   * Register a message handler for incoming messages
   * Must be called before start()
   */
  onMessage(handler: (event: SlackMessageEvent) => Promise<void>): void {
    this.messageHandler = handler;
  }

  /**
   * Start the bot (connects via Socket Mode)
   */
  async start(): Promise<void> {
    // Register app_mention event handler (when bot is @mentioned)
    this.app.event('app_mention', async ({ event, say }) => {
      // Authorization check
      const userId = event.user;
      if (!isSlackUserAuthorized(userId, this.allowedUserIds)) {
        const maskedId = userId ? `${userId.slice(0, 4)}***` : 'unknown';
        console.log(`[Slack] Unauthorized message from user ${maskedId}`);
        return;
      }

      if (this.messageHandler) {
        const messageEvent: SlackMessageEvent = {
          text: event.text,
          user: event.user,
          channel: event.channel,
          ts: event.ts,
          thread_ts: event.thread_ts,
        };
        // Fire-and-forget - errors handled by caller
        void this.messageHandler(messageEvent);
      }
    });

    // Also handle direct messages (DMs don't require @mention)
    this.app.event('message', async ({ event }) => {
      // Only handle DM messages (channel type 'im')
      // Skip if this is a message in a channel (requires @mention via app_mention)
      // The 'channel_type' is on certain event subtypes
      const channelType = (event as { channel_type?: string }).channel_type;
      if (channelType !== 'im') {
        return;
      }

      // Skip bot messages to prevent loops
      if ('bot_id' in event && event.bot_id) {
        return;
      }

      // Authorization check
      const userId = 'user' in event ? event.user : undefined;
      if (!isSlackUserAuthorized(userId, this.allowedUserIds)) {
        const maskedId = userId ? `${String(userId).slice(0, 4)}***` : 'unknown';
        console.log(`[Slack] Unauthorized DM from user ${maskedId}`);
        return;
      }

      if (this.messageHandler && 'text' in event && event.text) {
        const messageEvent: SlackMessageEvent = {
          text: event.text,
          user: userId ?? '',
          channel: event.channel,
          ts: event.ts,
          thread_ts: 'thread_ts' in event ? event.thread_ts : undefined,
        };
        void this.messageHandler(messageEvent);
      }
    });

    await this.app.start();
    console.log('[Slack] Bot started (Socket Mode)');
  }

  /**
   * Stop the bot gracefully
   */
  stop(): void {
    void this.app.stop();
    console.log('[Slack] Bot stopped');
  }
}
```

**Don't**:
- Don't use HTTP mode (Socket Mode is simpler)
- Don't add Block Kit formatting (plain text is sufficient)
- Don't handle slash commands (user types `/clone` as text, not Slack slash command)

**Verify**: `npm run type-check`

---

### Task 5: Create Slack adapter tests (`src/adapters/slack.test.ts`)

**Why**: Unit tests for adapter matching project patterns

**Mirror**: `src/adapters/telegram.test.ts`

**Do**:
```typescript
/**
 * Unit tests for Slack adapter
 */
import { SlackAdapter, SlackMessageEvent } from './slack';

// Mock @slack/bolt
jest.mock('@slack/bolt', () => ({
  App: jest.fn().mockImplementation(() => ({
    client: {
      chat: {
        postMessage: jest.fn().mockResolvedValue(undefined),
      },
      conversations: {
        replies: jest.fn().mockResolvedValue({ messages: [] }),
      },
    },
    event: jest.fn(),
    start: jest.fn().mockResolvedValue(undefined),
    stop: jest.fn().mockResolvedValue(undefined),
  })),
  LogLevel: {
    INFO: 'info',
  },
}));

describe('SlackAdapter', () => {
  describe('streaming mode configuration', () => {
    test('should return batch mode when configured', () => {
      const adapter = new SlackAdapter('xoxb-fake', 'xapp-fake', 'batch');
      expect(adapter.getStreamingMode()).toBe('batch');
    });

    test('should default to batch mode', () => {
      const adapter = new SlackAdapter('xoxb-fake', 'xapp-fake');
      expect(adapter.getStreamingMode()).toBe('batch');
    });

    test('should return stream mode when explicitly configured', () => {
      const adapter = new SlackAdapter('xoxb-fake', 'xapp-fake', 'stream');
      expect(adapter.getStreamingMode()).toBe('stream');
    });
  });

  describe('platform type', () => {
    test('should return slack', () => {
      const adapter = new SlackAdapter('xoxb-fake', 'xapp-fake');
      expect(adapter.getPlatformType()).toBe('slack');
    });
  });

  describe('thread detection', () => {
    let adapter: SlackAdapter;

    beforeEach(() => {
      adapter = new SlackAdapter('xoxb-fake', 'xapp-fake');
    });

    test('should detect thread when thread_ts differs from ts', () => {
      const event: SlackMessageEvent = {
        text: 'test',
        user: 'U123',
        channel: 'C456',
        ts: '1234567890.123456',
        thread_ts: '1234567890.000001',
      };
      expect(adapter.isThread(event)).toBe(true);
    });

    test('should not detect thread when thread_ts equals ts', () => {
      const event: SlackMessageEvent = {
        text: 'test',
        user: 'U123',
        channel: 'C456',
        ts: '1234567890.123456',
        thread_ts: '1234567890.123456',
      };
      expect(adapter.isThread(event)).toBe(false);
    });

    test('should not detect thread when thread_ts is undefined', () => {
      const event: SlackMessageEvent = {
        text: 'test',
        user: 'U123',
        channel: 'C456',
        ts: '1234567890.123456',
      };
      expect(adapter.isThread(event)).toBe(false);
    });
  });

  describe('conversation ID', () => {
    let adapter: SlackAdapter;

    beforeEach(() => {
      adapter = new SlackAdapter('xoxb-fake', 'xapp-fake');
    });

    test('should return channel:thread_ts for thread messages', () => {
      const event: SlackMessageEvent = {
        text: 'test',
        user: 'U123',
        channel: 'C456',
        ts: '1234567890.123456',
        thread_ts: '1234567890.000001',
      };
      expect(adapter.getConversationId(event)).toBe('C456:1234567890.000001');
    });

    test('should return channel:ts for non-thread messages', () => {
      const event: SlackMessageEvent = {
        text: 'test',
        user: 'U123',
        channel: 'C456',
        ts: '1234567890.123456',
      };
      expect(adapter.getConversationId(event)).toBe('C456:1234567890.123456');
    });
  });

  describe('stripBotMention', () => {
    let adapter: SlackAdapter;

    beforeEach(() => {
      adapter = new SlackAdapter('xoxb-fake', 'xapp-fake');
    });

    test('should strip bot mention from start', () => {
      expect(adapter.stripBotMention('<@U1234ABCD> /clone https://github.com/test/repo'))
        .toBe('/clone https://github.com/test/repo');
    });

    test('should strip multiple mentions', () => {
      expect(adapter.stripBotMention('<@U1234ABCD> <@W5678EFGH> hello'))
        .toBe('<@W5678EFGH> hello');
    });

    test('should return unchanged if no mention', () => {
      expect(adapter.stripBotMention('/status'))
        .toBe('/status');
    });
  });
});
```

**Verify**: `npm test -- src/adapters/slack.test.ts`

---

### Task 6: Update index.ts to register Slack adapter

**Why**: Conditionally initialize and start Slack adapter like Discord

**Mirror**: `src/index.ts:94-165` (Discord initialization pattern)

**Do**:

Add import at top with other adapters:
```typescript
import { SlackAdapter } from './adapters/slack';
```

Add Slack initialization after Discord initialization (around line 165):
```typescript
  // Initialize Slack adapter (conditional)
  let slack: SlackAdapter | null = null;
  if (process.env.SLACK_BOT_TOKEN && process.env.SLACK_APP_TOKEN) {
    const slackStreamingMode = (process.env.SLACK_STREAMING_MODE ?? 'batch') as
      | 'stream'
      | 'batch';
    slack = new SlackAdapter(
      process.env.SLACK_BOT_TOKEN,
      process.env.SLACK_APP_TOKEN,
      slackStreamingMode
    );

    // Register message handler
    slack.onMessage(async event => {
      const conversationId = slack!.getConversationId(event);

      // Skip if no text
      if (!event.text) return;

      // Strip the bot mention from the message
      const content = slack!.stripBotMention(event.text);
      if (!content) return; // Message was only a mention with no content

      // Check for thread context
      let threadContext: string | undefined;
      let parentConversationId: string | undefined;

      if (slack!.isThread(event)) {
        // Fetch thread history for context
        const history = await slack!.fetchThreadHistory(event);
        if (history.length > 0) {
          // Exclude the current message from history
          const historyWithoutCurrent = history.slice(0, -1);
          if (historyWithoutCurrent.length > 0) {
            threadContext = historyWithoutCurrent.join('\n');
          }
        }

        // Get parent conversation ID for context inheritance
        parentConversationId = slack!.getParentConversationId(event) ?? undefined;
      }

      // Fire-and-forget: handler returns immediately, processing happens async
      lockManager
        .acquireLock(conversationId, async () => {
          await handleMessage(
            slack!,
            conversationId,
            content,
            undefined,
            threadContext,
            parentConversationId
          );
        })
        .catch(async error => {
          console.error('[Slack] Failed to process message:', error);
          try {
            const userMessage = classifyAndFormatError(error as Error);
            await slack!.sendMessage(conversationId, userMessage);
          } catch (sendError) {
            console.error('[Slack] Failed to send error message to user:', sendError);
          }
        });
    });

    await slack.start();
  } else {
    console.log('[Slack] Adapter not initialized (missing SLACK_BOT_TOKEN or SLACK_APP_TOKEN)');
  }
```

Update shutdown handler to include Slack:
```typescript
  const shutdown = (): void => {
    console.log('[App] Shutting down gracefully...');
    telegram.stop();
    discord?.stop();
    slack?.stop();
    void pool.end().then(() => {
      console.log('[Database] Connection pool closed');
      process.exit(0);
    });
  };
```

Update ready message:
```typescript
  if (slack) {
    console.log('[App] Slack bot is also running');
  }
```

**Don't**:
- Don't make Slack required (keep it optional like Discord)
- Don't duplicate error handling logic

**Verify**: `npm run type-check && npm run build`

---

### Task 7: Update .env.example with Slack variables

**Why**: Document required environment variables for Slack

**Mirror**: `.env.example:37-54` (Discord variables pattern)

**Do**:

Add after Discord section:
```env
# Slack Bot (Socket Mode)
# Create app at https://api.slack.com/apps - see docs/slack-setup.md
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...

# Slack User Whitelist (optional - comma-separated user IDs)
# When set, only listed Slack users can interact with the bot
# When empty/unset, bot responds to all users
# Get user IDs: Slack profile > ... > Copy member ID
SLACK_ALLOWED_USER_IDS=U1234ABCD,W5678EFGH
```

Add to streaming mode section:
```env
SLACK_STREAMING_MODE=batch     # batch (default) | stream
```

**Verify**: Check file is valid (no syntax errors)

---

### Task 8: Create Slack setup guide (`docs/slack-setup.md`)

**Why**: Guide users through Slack bot creation process

**Do**:

```markdown
# Slack Bot Setup Guide

This guide walks you through creating a Slack app with Socket Mode for the Remote Coding Agent.

## Overview

The remote coding agent uses **Socket Mode** for Slack integration, which means:
- No public HTTP endpoints needed
- Works behind firewalls
- Simpler local development
- Not suitable for Slack App Directory (fine for personal/team use)

## Step 1: Create a Slack App

1. Go to [Slack API Apps](https://api.slack.com/apps)
2. Click **Create New App**
3. Choose **From scratch**
4. Enter:
   - **App Name**: `Remote Coding Agent` (or your preferred name)
   - **Workspace**: Select your workspace
5. Click **Create App**

## Step 2: Enable Socket Mode

1. In the left sidebar, click **Socket Mode**
2. Toggle **Enable Socket Mode** to ON
3. When prompted, create an App-Level Token:
   - **Token Name**: `socket-mode`
   - **Scopes**: Add `connections:write`
   - Click **Generate**
4. **Copy the token** (starts with `xapp-`) - this is your `SLACK_APP_TOKEN`

## Step 3: Configure Bot Scopes

1. In the left sidebar, click **OAuth & Permissions**
2. Scroll to **Scopes** > **Bot Token Scopes**
3. Add these scopes:
   - `app_mentions:read` - Receive @mention events
   - `chat:write` - Send messages
   - `channels:history` - Read messages in public channels (for thread context)
   - `channels:join` - Allow bot to join public channels
   - `groups:history` - Read messages in private channels (optional)
   - `im:history` - Read DM history (for DM support)
   - `im:write` - Send DMs
   - `mpim:history` - Read group DM history (optional)

## Step 4: Subscribe to Events

1. In the left sidebar, click **Event Subscriptions**
2. Toggle **Enable Events** to ON
3. Under **Subscribe to bot events**, add:
   - `app_mention` - When someone @mentions your bot
   - `message.im` - Direct messages to your bot
   - `message.channels` - Messages in public channels (optional, for broader context)
   - `message.groups` - Messages in private channels (optional)
4. Click **Save Changes**

## Step 5: Install to Workspace

1. In the left sidebar, click **Install App**
2. Click **Install to Workspace**
3. Review the permissions and click **Allow**
4. **Copy the Bot User OAuth Token** (starts with `xoxb-`) - this is your `SLACK_BOT_TOKEN`

## Step 6: Configure Environment Variables

Add to your `.env` file:

```env
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token

# Optional: Restrict to specific users
SLACK_ALLOWED_USER_IDS=U1234ABCD,W5678EFGH

# Optional: Streaming mode (batch is default for Slack)
SLACK_STREAMING_MODE=batch
```

## Step 7: Invite Bot to Channel

1. Go to the Slack channel where you want to use the bot
2. Type `/invite @Remote Coding Agent` (or your bot's name)
3. The bot should now respond to @mentions in that channel

## Usage

### Clone a Repository (Main Channel)

```
@Remote Coding Agent /clone https://github.com/user/repo
```

### Continue Work (Thread)

Reply in the thread created by the clone message:
```
@Remote Coding Agent /status
```

### Start Parallel Work (Worktree)

```
@Remote Coding Agent /worktree feature-branch
```

### Direct Messages

You can also DM the bot directly - no @mention needed:
```
/help
```

## Troubleshooting

### Bot Doesn't Respond

1. Check that Socket Mode is enabled
2. Verify both tokens are correct in `.env`
3. Check the app logs for errors
4. Ensure the bot is invited to the channel
5. Make sure you're @mentioning the bot (not just typing)

### "channel_not_found" Error

The bot needs to be invited to the channel:
```
/invite @Remote Coding Agent
```

### "missing_scope" Error

Add the required scope in **OAuth & Permissions** and reinstall the app.

### Thread Context Not Working

Ensure these scopes are added:
- `channels:history` (public channels)
- `groups:history` (private channels)

## Finding User IDs

To restrict access to specific users:

1. In Slack, click on a user's profile
2. Click the **...** (More) button
3. Click **Copy member ID**
4. Add to `SLACK_ALLOWED_USER_IDS`

## Security Recommendations

1. **Use User Whitelist**: Set `SLACK_ALLOWED_USER_IDS` to restrict bot access
2. **Private Channels**: Invite the bot only to channels where it's needed
3. **Token Security**: Never commit tokens to version control

## Reference Links

- [Slack API Documentation](https://api.slack.com/docs)
- [Bolt for JavaScript](https://tools.slack.dev/bolt-js/)
- [Socket Mode Guide](https://api.slack.com/apis/connections/socket)
- [Permission Scopes](https://api.slack.com/scopes)
```

**Verify**: Check markdown renders correctly

---

## Validation Strategy

### Automated Checks
- [ ] `npm run type-check` - Types valid
- [ ] `npm run lint` - No lint errors
- [ ] `npm run lint:fix` - Auto-fix any issues
- [ ] `npm run test` - All tests pass
- [ ] `npm run build` - Build succeeds

### New Tests to Write

| Test File | Test Case | What It Validates |
|-----------|-----------|-------------------|
| `src/utils/slack-auth.test.ts` | `parseAllowedUserIds` - various inputs | Parsing comma-separated Slack user IDs |
| `src/utils/slack-auth.test.ts` | `isSlackUserAuthorized` - whitelist modes | Authorization logic matches Discord/Telegram |
| `src/adapters/slack.test.ts` | streaming mode configuration | Adapter respects mode parameter |
| `src/adapters/slack.test.ts` | thread detection | `isThread()` correctly detects threads |
| `src/adapters/slack.test.ts` | conversation ID format | `getConversationId()` returns correct format |
| `src/adapters/slack.test.ts` | `stripBotMention` | Bot mention removal works |

### Manual/E2E Validation

1. **Set up Slack app** following `docs/slack-setup.md`

2. **Start the application**:
   ```bash
   docker-compose --profile with-db up -d postgres
   npm run dev
   ```

3. **Test @mention in channel**:
   - Go to a channel where the bot is invited
   - Type: `@RemoteCodingAgent /status`
   - Verify: Bot responds with status info

4. **Test clone workflow**:
   ```
   @RemoteCodingAgent /clone https://github.com/octocat/Hello-World
   ```
   - Verify: Bot responds, creates conversation

5. **Test thread continuation**:
   - Reply in the clone thread: `@RemoteCodingAgent /status`
   - Verify: Bot responds in thread, shows same codebase context

6. **Test DM**:
   - Send a DM to the bot: `/help`
   - Verify: Bot responds (no @mention needed)

7. **Test user whitelist**:
   - Set `SLACK_ALLOWED_USER_IDS` to exclude your ID
   - Verify: Bot ignores your messages
   - Remove restriction, verify bot responds again

### Edge Cases to Test

- [ ] Empty message after stripping mention (just `@bot` with no command)
- [ ] Very long message (>4000 chars) - should split into multiple messages
- [ ] Thread in thread (nested replies) - should maintain context
- [ ] Bot message in thread (should be ignored, no loops)
- [ ] Invalid user ID in whitelist (should be filtered out)
- [ ] Missing app token (should log error, not crash)
- [ ] Network disconnection (Socket Mode should reconnect)

### Regression Check

- [ ] Existing Discord adapter still works
- [ ] Existing Telegram adapter still works
- [ ] Test adapter endpoints still work
- [ ] GitHub adapter still works (if configured)
- [ ] All existing tests pass: `npm test`

## Risks

1. **Socket Mode reconnection**: Slack's Socket Mode should auto-reconnect, but network issues could cause temporary unavailability. Bolt SDK handles this internally.

2. **Rate limits**: Slack has rate limits (1 message per second per channel). The adapter doesn't handle rate limiting - long responses with many chunks could hit limits. Mitigation: Use batch mode (default) for Slack.

3. **Thread_ts complexity**: The `channel:thread_ts` format for conversation IDs could cause issues if messages are stored differently. Test thoroughly with the orchestrator.

4. **Event type variations**: Slack has many event subtypes. The current implementation focuses on `app_mention` and `message.im`. Edge cases with other message types might need handling later.
