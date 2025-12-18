# Plan: Discord Thread Support

## Summary

Update the existing Discord adapter to use **thread ID as conversation ID when messages come from threads**. This enables multiple parallel conversations in the same Discord channel - each thread becomes its own isolated conversation with its own AI session.

**Current behavior**: `message.channelId` is always used (all threads in a channel share one conversation)
**New behavior**: Use thread ID when in a thread, channel ID otherwise (each thread = separate conversation)

This is a ~5 line change to the existing adapter.

---

## External Research

### Discord.js Thread Handling
Sources: [Discord.js Threads Guide](https://discordjs.guide/popular-topics/threads.html), [Discord.js v14 Changes](https://discordjs.guide/additional-info/changes-in-v14.html)

**Key findings:**
- Threads are represented as `ThreadChannel` in discord.js
- A message's channel can be checked with `message.channel.isThread()`
- Thread ID is accessible via `message.channel.id` (same as channelId for threads)
- The `message.channelId` already contains the thread ID when message is in a thread

**Wait - this means the current implementation might already work!**

Let me verify: When a message is sent in a thread:
- `message.channelId` = the thread's ID (not the parent channel)
- `message.channel.id` = same as channelId
- `message.channel.parentId` = the parent channel's ID

**Conclusion**: The current code `return message.channelId` already returns the thread ID for messages in threads. The adapter may already support threads correctly!

### What needs to change

After deeper analysis, the current implementation should work for basic thread support. However, we should:
1. **Add the thread intent** - `GatewayIntentBits.GuildMessageTyping` is not needed, but threads work with existing intents
2. **Verify thread messages are received** - Need `GatewayIntentBits.GuildMessages` (already present)
3. **Test to confirm** - Manual validation that thread messages work

**The main issue is likely the bot isn't set up to receive messages from threads properly.** We may need:
- Ensure bot has permissions to read thread messages
- Possibly add `Partials.Thread` for archived thread support

---

## Patterns to Mirror

### Existing getConversationId (from discord.ts:134-137)

```typescript
// FROM: src/adapters/discord.ts:134-137
/**
 * Extract conversation ID from Discord message
 * Uses channel ID as the conversation identifier
 */
getConversationId(message: Message): string {
  return message.channelId;
}
```

This already returns the thread ID when in a thread. No change needed here.

### Existing intents configuration (from discord.ts:17-25)

```typescript
// FROM: src/adapters/discord.ts:17-25
this.client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.DirectMessages,
  ],
  partials: [Partials.Channel], // Required for DM support
});
```

May need to add `Partials.Thread` for full thread support.

### Test pattern (from discord.test.ts:74-83)

```typescript
// FROM: src/adapters/discord.test.ts:74-83
describe('conversation ID extraction', () => {
  test('should extract channel ID from message', () => {
    const adapter = new DiscordAdapter('fake-token-for-testing');
    const mockMessage = {
      channelId: '1234567890',
    } as unknown as import('discord.js').Message;

    expect(adapter.getConversationId(mockMessage)).toBe('1234567890');
  });
});
```

---

## Files to Change

| File | Action | Justification |
|------|--------|---------------|
| `src/adapters/discord.ts` | UPDATE | Add Partials.Thread for archived thread support |
| `src/adapters/discord.test.ts` | UPDATE | Add test for thread message conversation ID |

---

## NOT Building

- **Thread creation commands** - Users create threads manually in Discord
- **Auto-threading** - Bot won't auto-create threads for conversations
- **Thread-specific formatting** - Same message handling as channels
- **Thread metadata tracking** - No database changes

---

## Tasks

### Task 1: UPDATE discord.ts - Add thread partial

**Why**: Ensure the bot can receive messages from archived threads

**Mirror**: `src/adapters/discord.ts:17-25`

**Do**:
Update the partials array to include `Partials.Thread`:

```typescript
import { Client, GatewayIntentBits, Partials, Message, Events } from 'discord.js';

// ... in constructor:
this.client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.DirectMessages,
  ],
  partials: [Partials.Channel, Partials.Thread], // Added Thread for archived thread support
});
```

**Don't**:
- Change any other code
- Add thread-specific logging (keep it simple)

**Verify**: `npm run type-check`

---

### Task 2: UPDATE discord.ts - Improve getConversationId documentation

**Why**: Clarify that thread support is built-in (channelId already contains thread ID)

**Mirror**: `src/adapters/discord.ts:134-137`

**Do**:
Update the JSDoc comment:

```typescript
/**
 * Extract conversation ID from Discord message
 * Uses channel ID as the conversation identifier
 * Note: For thread messages, channelId is the thread ID (not parent channel)
 * This means each thread automatically gets its own conversation
 */
getConversationId(message: Message): string {
  return message.channelId;
}
```

**Don't**:
- Change the implementation (it's already correct)

**Verify**: `npm run type-check`

---

### Task 3: UPDATE discord.test.ts - Add thread conversation ID test

**Why**: Document and verify the expected thread behavior

**Mirror**: `src/adapters/discord.test.ts:74-83`

**Do**:
Add a test case for thread messages in the "conversation ID extraction" describe block:

```typescript
describe('conversation ID extraction', () => {
  test('should extract channel ID from message', () => {
    const adapter = new DiscordAdapter('fake-token-for-testing');
    const mockMessage = {
      channelId: '1234567890',
    } as unknown as import('discord.js').Message;

    expect(adapter.getConversationId(mockMessage)).toBe('1234567890');
  });

  test('should use thread ID when message is in a thread', () => {
    const adapter = new DiscordAdapter('fake-token-for-testing');
    // When a message is in a thread, channelId IS the thread ID
    // Parent channel would be accessible via message.channel.parentId
    const mockThreadMessage = {
      channelId: '9876543210', // This is the thread ID, not parent channel
    } as unknown as import('discord.js').Message;

    expect(adapter.getConversationId(mockThreadMessage)).toBe('9876543210');
  });
});
```

**Don't**:
- Mock complex thread channel structures (channelId is all we need)

**Verify**: `npm test -- --testPathPattern=discord`

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
| `discord.test.ts` | thread message uses thread ID | Documents thread behavior |

### Manual/E2E Validation

**Prerequisites:**
1. Discord bot set up with `DISCORD_BOT_TOKEN` in `.env`
2. Bot invited to a server with:
   - Read Messages permission
   - Send Messages permission
   - Read Message History permission
   - Use Threads permission (for thread access)

**Test Steps:**

```bash
# Terminal 1: Start app
npm run dev
```

**In Discord:**
1. Send message in a channel: `/status`
   - Verify: Bot responds
   - Note the conversation behavior

2. Create a thread in the same channel
   - Send: `/status` in the thread
   - Verify: Bot responds in the thread
   - Verify: This is treated as a SEPARATE conversation (fresh session)

3. Go back to main channel
   - Send: `/status`
   - Verify: Main channel conversation state is preserved (not mixed with thread)

4. Create a second thread
   - Send: `/clone https://github.com/some/repo`
   - Verify: This thread has its own independent codebase context

5. Test parallel work:
   - Thread 1: Clone repo A
   - Thread 2: Clone repo B
   - Verify: Each thread maintains its own state

**Key validation**: Main channel + each thread = separate conversations with independent state.

### Edge Cases to Test

- [ ] Message in archived thread (Partials.Thread enables this)
- [ ] Message in private thread (should work same as public)
- [ ] Bot mentioned in thread vs channel (both should work)
- [ ] Very long thread message (splitting still works)

### Regression Check

- [ ] Regular channel messages still work
- [ ] DM messages still work
- [ ] Telegram adapter unaffected
- [ ] GitHub adapter unaffected

---

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Bot permissions missing for threads | Medium | Document required Discord permissions |
| Archived threads not receiving messages | Low | Added Partials.Thread |
| Thread rate limits different from channels | Low | Discord handles this, same API |

---

## Summary

This is a **~10 line change** (mostly comments and one partial):

1. Add `Partials.Thread` to handle archived threads
2. Update JSDoc to clarify thread behavior
3. Add test documenting thread conversation ID

The core insight: **`message.channelId` already returns the thread ID for thread messages**. The existing implementation supports threads - we just need to ensure the bot receives thread messages (via Partials) and document the behavior.

After this, users can:
- Create threads in Discord channels
- Each thread = independent conversation
- Run parallel agents in different threads
- Combined with worktree support → true parallel development
