# Plan: Standardize Adapter Authorization Pattern

## Summary

Standardize the user whitelist/authorization pattern across all platform adapters. Currently GitHub handles auth internally while Telegram exposes `isAuthorized()` for external use. This plan moves all auth checks inside adapters and documents the pattern in CLAUDE.md for future adapter implementations.

## Current State

| Adapter | Auth Implemented | Where Check Happens | Env Var |
|---------|------------------|---------------------|---------|
| GitHub | Yes | Inside adapter (`handleWebhook()`) | `GITHUB_ALLOWED_USERS` |
| Telegram | Yes | Outside adapter (`src/index.ts`) | `TELEGRAM_ALLOWED_USER_IDS` |
| Discord | No | N/A | N/A |
| Test | No (intentional) | N/A | N/A |

## Target Pattern

**Auth checks happen INSIDE adapters**, not in index.ts. This ensures:
1. Encapsulation - adapters own their authorization logic
2. Consistency - all adapters behave the same way
3. Simplicity - callers don't need to know about auth

### Error Handling & Messaging Strategy

| Scenario | Behavior | Logging |
|----------|----------|---------|
| Unauthorized user | Silent rejection (no response to user) | Log with masked user ID for debugging |
| Invalid env var format | Treat as open access, log warning | `[Platform] Invalid whitelist format, defaulting to open access` |
| Missing user ID in message | Reject if whitelist enabled | Log as unauthorized |

**Rationale for silent rejection**: Responding to unauthorized users reveals the bot exists and is active. Silent rejection is more secure.

## Patterns to Mirror

### GitHub Adapter Auth Pattern (TARGET)
```typescript
// FROM: src/adapters/github.ts:58-70
export class GitHubAdapter implements IPlatformAdapter {
  private allowedUsers: string[];

  constructor(token: string, webhookSecret: string) {
    // ...
    this.allowedUsers = parseAllowedUsers(process.env.GITHUB_ALLOWED_USERS);
    if (this.allowedUsers.length > 0) {
      console.log(`[GitHub] User whitelist enabled (${this.allowedUsers.length} users)`);
    } else {
      console.log('[GitHub] User whitelist disabled (open access)');
    }
  }
}

// FROM: src/adapters/github.ts:410-417
// Inside handleWebhook() - auth check before processing
const senderUsername = event.sender?.login;
if (!isGitHubUserAuthorized(senderUsername, this.allowedUsers)) {
  const maskedUser = senderUsername ? `${senderUsername.slice(0, 3)}***` : 'unknown';
  console.log(`[GitHub] Unauthorized webhook from user ${maskedUser}`);
  return; // Silent rejection
}
```

### Telegram Adapter Current Pattern (TO CHANGE)
```typescript
// FROM: src/adapters/telegram.ts:42-44
// Currently exposes method for EXTERNAL use
isAuthorized(userId: number | undefined): boolean {
  return isUserAuthorized(userId, this.allowedUserIds);
}

// FROM: src/index.ts:253-257
// Auth check happens OUTSIDE adapter (BAD)
const userId = ctx.from?.id;
if (!telegram.isAuthorized(userId)) {
  console.log(`[Telegram] Unauthorized message from user ${userId}`);
  return;
}
```

## Files to Change

| File | Action | Justification |
|------|--------|---------------|
| `src/adapters/telegram.ts` | UPDATE | Move auth check inside, add callback-based message handling |
| `src/adapters/discord.ts` | UPDATE | Add auth with `DISCORD_ALLOWED_USER_IDS` |
| `src/index.ts` | UPDATE | Remove Telegram auth check, simplify Discord handler |
| `src/utils/discord-auth.ts` | CREATE | Auth utilities for Discord (mirrors telegram-auth.ts) |
| `src/utils/discord-auth.test.ts` | CREATE | Tests for Discord auth |
| `.env.example` | UPDATE | Add `DISCORD_ALLOWED_USER_IDS` |
| `CLAUDE.md` | UPDATE | Document adapter auth pattern |

## NOT Building

- No changes to `IPlatformAdapter` interface (auth is internal implementation detail)
- No changes to Test adapter (intentionally open for testing)
- No generic auth utility (platforms have different ID types - strings vs numbers)

## Tasks

### Task 1: Create Discord auth utilities

**Why**: Discord uses numeric user IDs like Telegram. Need parsing and validation functions.

**Mirror**: `src/utils/telegram-auth.ts`

**Do**:
Create `src/utils/discord-auth.ts`:
```typescript
/**
 * Discord user authorization utilities
 * Parses and validates user IDs for whitelist-based access control
 */

/**
 * Parse comma-separated user IDs from environment variable
 * Returns empty array if not set (open access mode)
 */
export function parseAllowedUserIds(envValue: string | undefined): string[] {
  if (!envValue || envValue.trim() === '') {
    return [];
  }

  return envValue
    .split(',')
    .map(id => id.trim())
    .filter(id => id !== '');
}

/**
 * Check if a user ID is authorized
 * Returns true if:
 * - allowedIds is empty (open access mode)
 * - userId is in allowedIds
 */
export function isUserAuthorized(userId: string | undefined, allowedIds: string[]): boolean {
  if (allowedIds.length === 0) {
    return true;
  }

  if (userId === undefined || userId === '') {
    return false;
  }

  return allowedIds.includes(userId);
}
```

**Note**: Discord user IDs are snowflakes (large integers as strings). Using string[] instead of number[] to avoid precision issues.

**Verify**: `npm run type-check`

### Task 2: Create Discord auth tests

**Why**: Match test coverage of other auth modules.

**Mirror**: `src/utils/telegram-auth.test.ts`

**Do**:
Create `src/utils/discord-auth.test.ts` with tests for:
- `parseAllowedUserIds`: undefined, empty, single ID, multiple IDs, whitespace handling
- `isUserAuthorized`: open access mode, whitelist mode, undefined/empty user ID

**Verify**: `npm test src/utils/discord-auth.test.ts`

### Task 3: Update Discord adapter with auth

**Why**: Add user whitelist support matching the GitHub pattern.

**Mirror**: `src/adapters/github.ts:58-70` (constructor) and `src/adapters/github.ts:410-417` (auth check)

**Do**:
Update `src/adapters/discord.ts`:

1. Add imports:
```typescript
import { parseAllowedUserIds, isUserAuthorized } from '../utils/discord-auth';
```

2. Add private field:
```typescript
private allowedUserIds: string[];
```

3. In constructor, after existing init:
```typescript
this.allowedUserIds = parseAllowedUserIds(process.env.DISCORD_ALLOWED_USER_IDS);
if (this.allowedUserIds.length > 0) {
  console.log(`[Discord] User whitelist enabled (${String(this.allowedUserIds.length)} users)`);
} else {
  console.log('[Discord] User whitelist disabled (open access)');
}
```

4. In `start()`, update the message handler to check auth:
```typescript
this.client.on(Events.MessageCreate, (message: Message) => {
  if (message.author.bot) return;

  // Authorization check
  const userId = message.author.id;
  if (!isUserAuthorized(userId, this.allowedUserIds)) {
    console.log(`[Discord] Unauthorized message from user ${userId.slice(0, 5)}***`);
    return;
  }

  if (this.messageHandler) {
    void this.messageHandler(message);
  }
});
```

**Verify**: `npm run type-check && npm run lint`

### Task 4: Update Telegram adapter to handle auth internally

**Why**: Move auth check from index.ts into adapter for consistency with GitHub pattern.

**Mirror**: `src/adapters/github.ts` handleWebhook pattern

**Do**:
Update `src/adapters/telegram.ts`:

1. Add `onMessage` callback pattern (like Discord):
```typescript
private messageHandler: ((ctx: Context) => Promise<void>) | null = null;

onMessage(handler: (ctx: Context) => Promise<void>): void {
  this.messageHandler = handler;
}
```

2. Update `start()` to register internal handler with auth check:
```typescript
async start(): Promise<void> {
  // Register message handler with auth check
  this.bot.on('message', async (ctx) => {
    if (!('text' in ctx.message)) return;

    // Authorization check - inside adapter
    const userId = ctx.from?.id;
    if (!isUserAuthorized(userId, this.allowedUserIds)) {
      console.log(`[Telegram] Unauthorized message from user ${String(userId)}`);
      return;
    }

    if (this.messageHandler) {
      await this.messageHandler(ctx);
    }
  });

  await this.bot.launch({ dropPendingUpdates: true });
  console.log('[Telegram] Bot started (polling mode, pending updates dropped)');
}
```

3. Remove the public `isAuthorized()` method (no longer needed externally)

**Verify**: `npm run type-check`

### Task 5: Update index.ts to use callback pattern

**Why**: Simplify main file - adapters now handle their own auth.

**Do**:
Update `src/index.ts`:

1. For Telegram, change from direct `bot.on('message')` to callback pattern:
```typescript
// Register message handler (auth handled inside adapter)
telegram.onMessage(async ctx => {
  const conversationId = telegram.getConversationId(ctx);
  const message = ctx.message && 'text' in ctx.message ? ctx.message.text : null;

  if (!message) return;

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

await telegram.start();
```

2. Remove the auth check from the existing handler (lines 253-257).

3. Discord handler is already using callback pattern and auth will be internal after Task 3.

**Verify**: `npm run type-check && npm run build`

### Task 6: Update .env.example

**Why**: Document the new Discord env var.

**Do**:
Add after DISCORD_BOT_TOKEN:
```
# Discord User Whitelist (optional - comma-separated user IDs)
# When set, only listed Discord users can interact with the bot
# When empty/unset, bot responds to all users
# Get user IDs by enabling Developer Mode in Discord settings
DISCORD_ALLOWED_USER_IDS=123456789012345678,987654321098765432
```

**Verify**: Visual inspection

### Task 7: Update CLAUDE.md with adapter auth pattern

**Why**: Document the pattern for future adapter implementations.

**Do**:
Add new section in "Development Guidelines" after "When Creating New Features":

```markdown
### Platform Adapter Authorization Pattern

All platform adapters must handle user authorization internally. Do NOT expose auth methods for external use.

**Pattern**:
1. Parse allowed users from env var in constructor (e.g., `PLATFORM_ALLOWED_USER_IDS`)
2. Log whitelist status on startup (enabled with count, or disabled)
3. Check authorization inside the message handler, before processing
4. Silent rejection for unauthorized users (log but don't respond)
5. Empty whitelist = open access (backwards compatible)

**Example** (from GitHubAdapter):
```typescript
constructor() {
  this.allowedUsers = parseAllowedUsers(process.env.GITHUB_ALLOWED_USERS);
  if (this.allowedUsers.length > 0) {
    console.log(`[GitHub] User whitelist enabled (${this.allowedUsers.length} users)`);
  } else {
    console.log('[GitHub] User whitelist disabled (open access)');
  }
}

// Inside message handler:
if (!isGitHubUserAuthorized(senderUsername, this.allowedUsers)) {
  console.log(`[GitHub] Unauthorized webhook from user ${maskedUser}`);
  return; // Silent rejection
}
```

**Env var naming**: `{PLATFORM}_ALLOWED_USERS` for username-based (GitHub) or `{PLATFORM}_ALLOWED_USER_IDS` for ID-based (Telegram, Discord).

**Error handling**:
- Invalid env var format → log warning, default to open access
- Unauthorized user → silent rejection, log masked user ID
- Missing user ID → reject if whitelist enabled, log as unauthorized
```

**Verify**: Visual inspection

## Validation Strategy

### Automated Checks
- [ ] `npm run type-check` - Types valid
- [ ] `npm run lint` - No new lint errors
- [ ] `npm test` - All tests pass (including new discord-auth tests)
- [ ] `npm run build` - Build succeeds

### New Tests to Write

| Test File | Test Case | What It Validates |
|-----------|-----------|-------------------|
| `src/utils/discord-auth.test.ts` | parseAllowedUserIds with undefined | Returns empty array |
| `src/utils/discord-auth.test.ts` | parseAllowedUserIds with IDs | Parses correctly |
| `src/utils/discord-auth.test.ts` | isUserAuthorized open access | Allows all when empty list |
| `src/utils/discord-auth.test.ts` | isUserAuthorized whitelist | Allows/rejects correctly |

### Manual Validation

1. **Telegram auth test**:
   ```bash
   # Set whitelist in .env
   TELEGRAM_ALLOWED_USER_IDS=YOUR_USER_ID
   npm run dev
   # Send message from allowed user - should work
   # Send message from different user - should be silently rejected (check logs)
   ```

2. **Discord auth test** (if Discord is configured):
   ```bash
   DISCORD_ALLOWED_USER_IDS=YOUR_USER_ID
   npm run dev
   # Same test as Telegram
   ```

3. **Open access test**:
   ```bash
   # Remove/comment out whitelist env vars
   npm run dev
   # All users should be able to interact
   ```

### Edge Cases
- [ ] Empty string env var = open access (not crash)
- [ ] Whitespace-only env var = open access
- [ ] Single user in whitelist works
- [ ] User ID with leading/trailing spaces still matches
- [ ] Malformed env var (e.g., `user1,,user2`) handles gracefully
- [ ] Very long whitelist (100+ users) works without performance issues

### Regression Check
- [ ] GitHub adapter still works (no changes to its auth logic)
- [ ] Test adapter still works (no auth added)
- [ ] Existing Telegram functionality preserved

## Risks

1. **Breaking change for Telegram**: The `isAuthorized()` method is being removed. If any external code calls it, it will break. Mitigation: This is an internal tool, unlikely to have external callers.

2. **Context type in callback**: Telegram's `Context` type from Telegraf may need to be exported or the callback signature adjusted. May need to import type from telegraf.
