# Plan: Slack Markdown Block for AI Responses

## Summary

The AI assistant returns GitHub-flavored markdown, which doesn't render correctly in Slack (Slack uses its own `mrkdwn` format). We'll use Slack's native `markdown` block type (released February 2025) to let Slack handle the conversion automatically. This is simpler than the Telegram approach (which requires a conversion library) because Slack handles the translation internally.

## External Research

### Documentation
- [Markdown block reference](https://docs.slack.dev/reference/block-kit/blocks/markdown-block/) - Block Kit specification
- [Markdown block announcement](https://docs.slack.dev/changelog/2025/02/03/block-kit-markdown/) - Released February 2025
- [Best practices for AI apps](https://docs.slack.dev/ai/ai-apps-best-practices/) - Official guidance for AI bots
- [AI Assistant tutorial](https://docs.slack.dev/tools/bolt-js/tutorials/ai-assistant/) - Implementation examples

### Key Findings
1. **Native solution exists**: Slack introduced `type: "markdown"` block specifically for AI apps
2. **No conversion library needed**: Unlike Telegram, Slack handles translation internally
3. **12,000 character limit per block**: Much more generous than Discord's 2,000 or Telegram's 4,096
4. **Block expansion**: A single markdown block may expand to multiple blocks after translation (e.g., code blocks become separate blocks)

### Supported Markdown Features
| Feature | Supported |
|---------|-----------|
| Bold (`**text**`) | Yes |
| Italic (`*text*`) | Yes |
| Strikethrough (`~~text~~`) | Yes |
| Inline code | Yes |
| Code blocks (triple backticks) | Yes |
| Links `[text](url)` | Yes |
| Headers (H1-H6) | Yes (rendered as bold) |
| Lists (ordered/unordered) | Yes |
| Block quotes | Yes |
| Tables | No |
| Syntax-highlighted code | No |

### Gotchas
- The `MarkdownBlock` type is available in `@slack/types` (already in dependencies via `@slack/bolt` 4.6.0)
- Must use `blocks` array in `chat.postMessage`, not plain `text` parameter
- Still need fallback to plain text for messages > 12K characters

## Patterns to Mirror

### Telegram Adapter Formatting Pattern (src/adapters/telegram.ts:60-151)
```typescript
// FROM: src/adapters/telegram.ts:60-77
async sendMessage(chatId: string, message: string): Promise<void> {
  const id = parseInt(chatId);
  console.log(`[Telegram] sendMessage called, length=${String(message.length)}`);

  if (message.length <= MAX_LENGTH) {
    // Short message: try MarkdownV2 formatting
    await this.sendFormattedChunk(id, message);
  } else {
    // Long message: split by paragraphs, format each chunk
    console.log(
      `[Telegram] Message too long (${String(message.length)}), splitting by paragraphs`
    );
    const chunks = this.splitIntoParagraphChunks(message, MAX_LENGTH - 200);

    for (const chunk of chunks) {
      await this.sendFormattedChunk(id, chunk);
    }
  }
}
```

### Current Slack Adapter (src/adapters/slack.ts:52-78)
```typescript
// FROM: src/adapters/slack.ts:52-78 (current implementation without formatting)
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
    // ... splitting logic
  }
}
```

### Test Pattern (src/adapters/telegram.test.ts:40-98)
```typescript
// FROM: src/adapters/telegram.test.ts:40-62
describe('message formatting', () => {
  let adapter: TelegramAdapter;
  let mockSendMessage: jest.Mock;
  const mockConvert = telegramMarkdown.convertToTelegramMarkdown as jest.Mock;

  beforeEach(() => {
    adapter = new TelegramAdapter('fake-token-for-testing');
    mockSendMessage = jest.fn().mockResolvedValue(undefined);
    // Override bot's sendMessage
    (adapter.getBot().telegram as unknown as { sendMessage: jest.Mock }).sendMessage =
      mockSendMessage;
    mockConvert.mockClear();
  });

  test('should convert markdown and send with MarkdownV2 parse_mode', async () => {
    mockConvert.mockReturnValue('*formatted*');
    await adapter.sendMessage('12345', '**test**');

    expect(mockConvert).toHaveBeenCalledWith('**test**');
    expect(mockSendMessage).toHaveBeenCalledWith(12345, '*formatted*', {
      parse_mode: 'MarkdownV2',
    });
  });
});
```

## Files to Change

| File | Action | Justification |
|------|--------|---------------|
| `src/adapters/slack.ts` | UPDATE | Use Block Kit markdown block instead of plain text |

## NOT Building

- No conversion utility/library (Slack handles translation internally)
- No streaming with `chatStream()` (existing streaming mode config is sufficient)
- No AI disclaimer context block (can be added later if needed)
- No feedback mechanism (out of scope for this task)

## Tasks

### Task 1: Update Slack sendMessage to use markdown blocks

**Why**: Messages from the AI come in GitHub-flavored markdown which doesn't render correctly in Slack. Using the native markdown block type lets Slack handle the conversion.

**Mirror**: `src/adapters/telegram.ts:60-77` (formatting strategy with fallback)

**Do**:
1. Update the constant from practical limit to markdown block limit:
```typescript
const MAX_MARKDOWN_BLOCK_LENGTH = 12000; // Slack markdown block limit
const MAX_PLAIN_TEXT_LENGTH = 4000; // Practical limit for readability (Slack allows 40k)
```

2. Modify `sendMessage` to use markdown blocks:
```typescript
async sendMessage(channelId: string, message: string): Promise<void> {
  console.log(`[Slack] sendMessage called, length=${String(message.length)}`);

  const [channel, threadTs] = channelId.includes(':')
    ? channelId.split(':')
    : [channelId, undefined];

  if (message.length <= MAX_MARKDOWN_BLOCK_LENGTH) {
    // Use markdown block for proper formatting
    await this.sendWithMarkdownBlock(channel, message, threadTs);
  } else {
    // Long message: split by paragraphs
    console.log(
      `[Slack] Message too long (${String(message.length)}), splitting by paragraphs`
    );
    const chunks = this.splitIntoParagraphChunks(message, MAX_MARKDOWN_BLOCK_LENGTH - 500);

    for (const chunk of chunks) {
      await this.sendWithMarkdownBlock(channel, chunk, threadTs);
    }
  }
}
```

3. Add new method for sending with markdown block:
```typescript
/**
 * Send a message using Slack's markdown block for proper formatting
 * Falls back to plain text if block fails
 */
private async sendWithMarkdownBlock(
  channel: string,
  message: string,
  threadTs?: string
): Promise<void> {
  try {
    await this.app.client.chat.postMessage({
      channel,
      thread_ts: threadTs,
      blocks: [
        {
          type: 'markdown',
          text: message,
        },
      ],
      // Fallback text for notifications/accessibility
      text: message.substring(0, 150) + (message.length > 150 ? '...' : ''),
    });
    console.log(`[Slack] Markdown block sent (${String(message.length)} chars)`);
  } catch (error) {
    // Fallback to plain text
    const err = error as Error;
    console.warn('[Slack] Markdown block failed, using plain text:', err.message);
    await this.app.client.chat.postMessage({
      channel,
      thread_ts: threadTs,
      text: message,
    });
  }
}
```

4. Update `splitIntoParagraphChunks` to use new constant in the log:
```typescript
console.log(`[Slack] Split into ${String(finalChunks.length)} chunks`);
```

**Don't**:
- Don't add any external conversion libraries
- Don't import types from `@slack/types` (the block structure is simple enough as literal)
- Don't change the paragraph splitting logic (it works well)

**Verify**: `npm run type-check && npm test -- src/adapters/slack.test.ts`

### Task 2: Add tests for markdown block formatting

**Why**: Ensure the markdown block is used correctly and fallback works.

**Mirror**: `src/adapters/telegram.test.ts:40-98`

**Do**:
Add new test cases to `src/adapters/slack.test.ts`:
```typescript
describe('message formatting', () => {
  let adapter: SlackAdapter;
  let mockPostMessage: jest.Mock;

  beforeEach(() => {
    adapter = new SlackAdapter('xoxb-fake', 'xapp-fake');
    mockPostMessage = adapter.getApp().client.chat.postMessage as jest.Mock;
    mockPostMessage.mockClear();
  });

  test('should send short messages with markdown block', async () => {
    await adapter.sendMessage('C123:1234.5678', '**Hello** world');

    expect(mockPostMessage).toHaveBeenCalledWith({
      channel: 'C123',
      thread_ts: '1234.5678',
      blocks: [
        {
          type: 'markdown',
          text: '**Hello** world',
        },
      ],
      text: '**Hello** world',
    });
  });

  test('should fallback to plain text when markdown block fails', async () => {
    mockPostMessage
      .mockRejectedValueOnce(new Error('markdown block not supported'))
      .mockResolvedValueOnce(undefined);

    await adapter.sendMessage('C123', 'test message');

    expect(mockPostMessage).toHaveBeenCalledTimes(2);
    // First call with markdown block
    expect(mockPostMessage).toHaveBeenNthCalledWith(1, expect.objectContaining({
      blocks: expect.any(Array),
    }));
    // Second call plain text fallback
    expect(mockPostMessage).toHaveBeenNthCalledWith(2, expect.objectContaining({
      text: 'test message',
    }));
    expect(mockPostMessage.mock.calls[1][0]).not.toHaveProperty('blocks');
  });

  test('should split long messages into multiple markdown blocks', async () => {
    const paragraph1 = 'a'.repeat(10000);
    const paragraph2 = 'b'.repeat(10000);
    const message = `${paragraph1}\n\n${paragraph2}`;

    await adapter.sendMessage('C123', message);

    expect(mockPostMessage).toHaveBeenCalledTimes(2);
    // Both calls should use markdown blocks
    expect(mockPostMessage.mock.calls[0][0]).toHaveProperty('blocks');
    expect(mockPostMessage.mock.calls[1][0]).toHaveProperty('blocks');
  });
});
```

**Don't**:
- Don't remove existing tests
- Don't test internal implementation details beyond the block structure

**Verify**: `npm test -- src/adapters/slack.test.ts`

## Validation Strategy

### Automated Checks
- [ ] `npm run type-check` - Types valid
- [ ] `npm run lint` - No lint errors
- [ ] `npm run test` - All tests pass
- [ ] `npm run build` - Build succeeds

### New Tests to Write
| Test File | Test Case | What It Validates |
|-----------|-----------|-------------------|
| `src/adapters/slack.test.ts` | should send short messages with markdown block | Markdown block is used for normal messages |
| `src/adapters/slack.test.ts` | should fallback to plain text when markdown block fails | Error handling works |
| `src/adapters/slack.test.ts` | should split long messages into multiple markdown blocks | Long message handling |

### Manual/E2E Validation
```bash
# Start the app
docker-compose --profile with-db up -d postgres
npm run dev

# Use test adapter to send a markdown-heavy message
curl -X POST http://localhost:3000/test/message \
  -H "Content-Type: application/json" \
  -d '{
    "conversationId": "test-slack-md",
    "message": "/help"
  }'

# Check response formatting
curl http://localhost:3000/test/messages/test-slack-md | jq
```

For real Slack testing:
1. Configure Slack credentials in `.env`
2. Start app with `npm run dev`
3. Mention the bot with a command that triggers AI response
4. Verify response shows proper formatting (bold, code blocks, lists)

### Edge Cases
- [ ] Empty message - should not crash
- [ ] Message with only code blocks - should render properly
- [ ] Message exactly at 12,000 chars - should not split
- [ ] Message at 12,001 chars - should split into two blocks
- [ ] Markdown block API error - should fallback to plain text

### Regression Check
- [ ] Existing Slack commands still work (`/status`, `/help`, `/clone`)
- [ ] Thread replies still go to correct thread
- [ ] DM handling still works
- [ ] Other adapters (Telegram, Discord) unaffected

## Risks

1. **Markdown block availability**: The `markdown` block type was released in February 2025. If a user's Slack workspace hasn't updated, the block may fail. Mitigation: fallback to plain text.

2. **Block expansion**: A single markdown block may expand to multiple blocks after translation. This is handled by Slack automatically and shouldn't cause issues.

3. **Character limit**: 12,000 chars per block is generous but AI responses could exceed this. Mitigation: paragraph splitting already implemented.
