# Issue #67: Refactor handle_message Function

**Epic:** 007 - Phase 2 High-Priority Refactoring
**Priority:** HIGH
**Estimated Time:** 3 hours
**Status:** Planning
**Created:** 2026-01-15

## Problem Statement

The `handle_message` function in `src/bot.py` (line 706) is currently **160 lines** and violates the Single Responsibility Principle by mixing multiple concerns:

1. **Message routing** - Determining which handler should process the message
2. **Input validation** - Checking topic filters, authorization, and message format
3. **Context extraction** - Getting user state, subscription status, onboarding state
4. **Response formatting** - Handling Markdown parsing errors, error messages

This makes the function:
- Hard to test (requires mocking many dependencies)
- Difficult to maintain (changes affect multiple concerns)
- Error-prone (deep nesting, multiple returns)
- Hard to understand (cognitive load is high)

## Goal

Refactor `handle_message` from **160 lines to ~40 lines** by extracting well-defined helper functions:

1. `validate_message_input()` - Input validation and early returns
2. `extract_message_context()` - User state and context gathering
3. `route_message()` - Message routing logic
4. `format_response()` - Response formatting and error handling

## Current Function Analysis

### Line-by-Line Breakdown (706-900)

**Lines 706-716: Initialization & Topic Filter (11 lines)**
```python
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages"""
    user_id = str(update.effective_user.id)

    # Check topic filter
    if not should_process_message(update):
        return

    text = update.message.text
    logger.info(f"Message from {user_id}: {text[:50]}...")
```

**Lines 718-738: Pending Activation Check (21 lines)**
```python
    from src.db.queries import get_user_subscription_status, get_onboarding_state
    subscription = await get_user_subscription_status(user_id)

    if subscription and subscription['status'] == 'pending':
        # User is pending, check if message looks like an invite code
        message_clean = text.strip().upper()
        if len(message_clean) >= 4 and len(message_clean) <= 50 and message_clean.replace(' ', '').isalnum():
            await activate(update, context)
            return
        else:
            await update.message.reply_text(
                "⚠️ **Please activate your account first**\n\n"
                "Send your invite code to start using the bot.\n\n"
                "Example: `HEALTH2024`\n\n"
                "Don't have a code? Use /start to get more information."
            )
            return
```

**Lines 740-745: Onboarding Check (6 lines)**
```python
    onboarding = await get_onboarding_state(user_id)
    if onboarding and not onboarding.get('completed_at'):
        await handle_onboarding_message(update, context)
        return
```

**Lines 747-749: Authorization Check (3 lines)**
```python
    if not await is_authorized(user_id):
        return
```

**Lines 751-788: Custom Note Entry State (38 lines)**
```python
    if context.user_data.get('awaiting_custom_note'):
        # Handle cancel command
        if text.strip().lower() == '/cancel':
            context.user_data.pop('awaiting_custom_note', None)
            context.user_data.pop('pending_note', None)
            await update.message.reply_text("✅ Note entry cancelled.")
            return

        # Get pending note data
        pending_note = context.user_data.get('pending_note', {})
        reminder_id = pending_note.get('reminder_id')
        scheduled_time = pending_note.get('scheduled_time')

        if not reminder_id or not scheduled_time:
            await update.message.reply_text("❌ Error: Missing note context. Please try again.")
            context.user_data.pop('awaiting_custom_note', None)
            context.user_data.pop('pending_note', None)
            return

        # Trim note to max 200 characters
        note_text = text.strip()[:200]

        # Save the note
        from src.db.queries import update_completion_note
        try:
            await update_completion_note(user_id, reminder_id, scheduled_time, note_text)
            await update.message.reply_text(
                f"✅ **Note saved!**\n\n📝 \"{note_text}\"\n\nThis will help track patterns over time.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error saving custom note: {e}", exc_info=True)
            await update.message.reply_text("❌ Error saving note. Please try again.")

        # Clean up
        context.user_data.pop('awaiting_custom_note', None)
        context.user_data.pop('pending_note', None)
        return
```

**Lines 790-833: Timezone Setup (Commented Out, 44 lines)**
- Currently disabled but adds complexity

**Lines 835-900: AI Response Processing (65 lines)**
```python
    try:
        from src.utils.typing_indicator import PersistentTypingIndicator

        async with PersistentTypingIndicator(update.message.chat):
            message_history = await get_conversation_history(user_id, limit=20)

            from src.utils.query_router import query_router
            model_choice, routing_reason = query_router.route_query(text)

            model_override = None
            if model_choice == "haiku":
                model_override = "anthropic:claude-3-5-haiku-latest"
                logger.info(f"[ROUTER] Using Haiku for fast response: {routing_reason}")

            response = await get_agent_response(
                user_id, text, memory_manager, reminder_manager, message_history,
                bot_application=context.application,
                model_override=model_override
            )

        await save_conversation_message(user_id, "user", text, message_type="text")
        await save_conversation_message(user_id, "assistant", response, message_type="text")

        async def background_memory_tasks():
            mem0_manager.add_message(user_id, text, role="user", metadata={"message_type": "text"})
            mem0_manager.add_message(user_id, response, role="assistant", metadata={"message_type": "text"})

            logger.info(f"[DEBUG-FLOW] BEFORE auto_save_user_info for user {user_id}")
            logger.info(f"[DEBUG-FLOW] User message: {text[:100]}")
            logger.info(f"[DEBUG-FLOW] Agent response: {response[:100]}")
            await auto_save_user_info(user_id, text, response)
            logger.info(f"[DEBUG-FLOW] AFTER auto_save_user_info completed successfully")

        import asyncio
        asyncio.create_task(background_memory_tasks())

        # Send response - try with Markdown first, fallback to plain text
        try:
            await update.message.reply_text(response, parse_mode="Markdown")
            logger.info(f"Sent AI response to {user_id}")
        except telegram.error.BadRequest as e:
            if "can't parse entities" in str(e).lower():
                logger.warning(f"Markdown parse error, sending as plain text: {e}")
                await update.message.reply_text(response)
            else:
                raise

    except Exception as e:
        logger.error(f"Error in handle_message: {e}", exc_info=True)
        await update.message.reply_text(
            "Sorry, I encountered an error. Please try again!"
        )
```

### Responsibilities Identified

1. **Input Validation**
   - Topic filter check
   - Authorization check

2. **Context Extraction**
   - Get user ID
   - Get subscription status
   - Get onboarding state
   - Get user conversation state (awaiting_custom_note)

3. **Message Routing**
   - Pending activation → activation handler
   - Onboarding incomplete → onboarding handler
   - Custom note awaited → note handler
   - Normal message → AI agent

4. **Response Formatting**
   - Markdown parsing with fallback
   - Error handling
   - Background tasks (memory saving)

## Proposed Architecture

### 1. `validate_message_input(update, user_id)` → `ValidationResult`

**Purpose:** Early validation and filtering
**Lines Saved:** ~10 lines
**Returns:** NamedTuple with `is_valid: bool`, `reason: str | None`

```python
from typing import NamedTuple

class ValidationResult(NamedTuple):
    is_valid: bool
    reason: str | None = None

async def validate_message_input(
    update: Update,
    user_id: str
) -> ValidationResult:
    """
    Validate message input and check if it should be processed.

    Checks:
    - Topic filter (should_process_message)
    - Authorization (is_authorized)

    Returns:
        ValidationResult with is_valid=True if message should be processed,
        is_valid=False with reason if it should be ignored.
    """
    # Check topic filter
    if not should_process_message(update):
        return ValidationResult(is_valid=False, reason="topic_filter")

    # Check authorization (for active users)
    if not await is_authorized(user_id):
        return ValidationResult(is_valid=False, reason="unauthorized")

    return ValidationResult(is_valid=True)
```

### 2. `extract_message_context(user_id, context)` → `MessageContext`

**Purpose:** Gather all user state and context
**Lines Saved:** ~15 lines
**Returns:** Dataclass with user state information

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class MessageContext:
    """User context for message processing"""
    user_id: str
    subscription: Optional[dict]
    onboarding: Optional[dict]
    awaiting_custom_note: bool
    pending_note: Optional[dict]

    @property
    def is_pending_activation(self) -> bool:
        return self.subscription and self.subscription.get('status') == 'pending'

    @property
    def is_in_onboarding(self) -> bool:
        return self.onboarding and not self.onboarding.get('completed_at')

    @property
    def is_in_note_entry(self) -> bool:
        return self.awaiting_custom_note

async def extract_message_context(
    user_id: str,
    context: ContextTypes.DEFAULT_TYPE
) -> MessageContext:
    """
    Extract user context needed for message routing.

    Fetches:
    - Subscription status
    - Onboarding state
    - User conversation state (custom note entry)

    Returns:
        MessageContext with all relevant user state
    """
    from src.db.queries import get_user_subscription_status, get_onboarding_state

    subscription = await get_user_subscription_status(user_id)
    onboarding = await get_onboarding_state(user_id)

    return MessageContext(
        user_id=user_id,
        subscription=subscription,
        onboarding=onboarding,
        awaiting_custom_note=context.user_data.get('awaiting_custom_note', False),
        pending_note=context.user_data.get('pending_note')
    )
```

### 3. `route_message(update, context, msg_context, text)` → `None`

**Purpose:** Route message to appropriate handler
**Lines Saved:** ~80 lines
**Returns:** None (handles routing internally)

```python
async def route_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    msg_context: MessageContext,
    text: str
) -> None:
    """
    Route message to the appropriate handler based on user state.

    Routing priority:
    1. Pending activation → check for invite code or prompt
    2. Onboarding incomplete → onboarding handler
    3. Custom note entry → note handler
    4. Normal message → AI agent

    Args:
        update: Telegram update object
        context: Telegram context
        msg_context: User message context
        text: Message text
    """
    # Route 1: Pending activation
    if msg_context.is_pending_activation:
        await _handle_pending_activation(update, context, text)
        return

    # Route 2: Onboarding incomplete
    if msg_context.is_in_onboarding:
        await handle_onboarding_message(update, context)
        return

    # Route 3: Custom note entry
    if msg_context.is_in_note_entry:
        await _handle_custom_note_entry(
            update, context, text, msg_context.pending_note
        )
        return

    # Route 4: Normal AI agent processing
    await _handle_ai_message(update, context, msg_context.user_id, text)
```

### 4. `format_response(update, response)` → `None`

**Purpose:** Format and send response with error handling
**Lines Saved:** ~15 lines
**Returns:** None (sends response directly)

```python
async def format_response(
    update: Update,
    response: str,
    user_id: str
) -> None:
    """
    Format and send response with Markdown fallback.

    Attempts to send with Markdown formatting first.
    Falls back to plain text if Markdown parsing fails.

    Args:
        update: Telegram update object
        response: Response text to send
        user_id: User ID for logging
    """
    try:
        await update.message.reply_text(response, parse_mode="Markdown")
        logger.info(f"Sent AI response to {user_id}")
    except telegram.error.BadRequest as e:
        if "can't parse entities" in str(e).lower():
            logger.warning(f"Markdown parse error, sending as plain text: {e}")
            await update.message.reply_text(response)
        else:
            raise
```

### 5. Private Helper Functions

Extract the three routing handlers into private functions:

```python
async def _handle_pending_activation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str
) -> None:
    """Handle message from user pending activation"""
    message_clean = text.strip().upper()
    if len(message_clean) >= 4 and len(message_clean) <= 50 and message_clean.replace(' ', '').isalnum():
        await activate(update, context)
    else:
        await update.message.reply_text(
            "⚠️ **Please activate your account first**\n\n"
            "Send your invite code to start using the bot.\n\n"
            "Example: `HEALTH2024`\n\n"
            "Don't have a code? Use /start to get more information."
        )

async def _handle_custom_note_entry(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    pending_note: Optional[dict]
) -> None:
    """Handle custom note entry flow"""
    # Handle cancel command
    if text.strip().lower() == '/cancel':
        context.user_data.pop('awaiting_custom_note', None)
        context.user_data.pop('pending_note', None)
        await update.message.reply_text("✅ Note entry cancelled.")
        return

    # Validate pending note data
    if not pending_note:
        await update.message.reply_text("❌ Error: Missing note context. Please try again.")
        context.user_data.pop('awaiting_custom_note', None)
        return

    reminder_id = pending_note.get('reminder_id')
    scheduled_time = pending_note.get('scheduled_time')

    if not reminder_id or not scheduled_time:
        await update.message.reply_text("❌ Error: Missing note context. Please try again.")
        context.user_data.pop('awaiting_custom_note', None)
        context.user_data.pop('pending_note', None)
        return

    # Save the note
    note_text = text.strip()[:200]
    from src.db.queries import update_completion_note

    try:
        await update_completion_note(
            str(update.effective_user.id),
            reminder_id,
            scheduled_time,
            note_text
        )
        await update.message.reply_text(
            f"✅ **Note saved!**\n\n📝 \"{note_text}\"\n\nThis will help track patterns over time.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error saving custom note: {e}", exc_info=True)
        await update.message.reply_text("❌ Error saving note. Please try again.")

    # Clean up
    context.user_data.pop('awaiting_custom_note', None)
    context.user_data.pop('pending_note', None)

async def _handle_ai_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: str,
    text: str
) -> None:
    """Handle normal AI agent message processing"""
    try:
        from src.utils.typing_indicator import PersistentTypingIndicator

        async with PersistentTypingIndicator(update.message.chat):
            # Load conversation history
            message_history = await get_conversation_history(user_id, limit=20)

            # Route query to appropriate model
            from src.utils.query_router import query_router
            model_choice, routing_reason = query_router.route_query(text)

            model_override = None
            if model_choice == "haiku":
                model_override = "anthropic:claude-3-5-haiku-latest"
                logger.info(f"[ROUTER] Using Haiku for fast response: {routing_reason}")

            # Get agent response
            response = await get_agent_response(
                user_id, text, memory_manager, reminder_manager, message_history,
                bot_application=context.application,
                model_override=model_override
            )

        # Save conversation
        await save_conversation_message(user_id, "user", text, message_type="text")
        await save_conversation_message(user_id, "assistant", response, message_type="text")

        # Background memory tasks
        async def background_memory_tasks():
            mem0_manager.add_message(user_id, text, role="user", metadata={"message_type": "text"})
            mem0_manager.add_message(user_id, response, role="assistant", metadata={"message_type": "text"})

            # auto_save_user_info is defined in src/bot.py
            logger.info(f"[DEBUG-FLOW] BEFORE auto_save_user_info for user {user_id}")
            logger.info(f"[DEBUG-FLOW] User message: {text[:100]}")
            logger.info(f"[DEBUG-FLOW] Agent response: {response[:100]}")
            await auto_save_user_info(user_id, text, response)
            logger.info(f"[DEBUG-FLOW] AFTER auto_save_user_info completed successfully")

        import asyncio
        asyncio.create_task(background_memory_tasks())

        # Send response with formatting
        await format_response(update, response, user_id)

    except Exception as e:
        logger.error(f"Error in AI message handling: {e}", exc_info=True)
        await update.message.reply_text(
            "Sorry, I encountered an error. Please try again!"
        )
```

## Refactored `handle_message` (~40 lines)

```python
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle text messages - main entry point for message processing.

    This function orchestrates message handling by:
    1. Validating input and authorization
    2. Extracting user context
    3. Routing to appropriate handler

    The actual processing is delegated to specialized handlers.
    """
    user_id = str(update.effective_user.id)
    text = update.message.text

    logger.info(f"Message from {user_id}: {text[:50]}...")

    # Step 1: Validate input
    validation = await validate_message_input(update, user_id)
    if not validation.is_valid:
        logger.debug(f"Message ignored: {validation.reason}")
        return

    # Step 2: Extract context
    msg_context = await extract_message_context(user_id, context)

    # Step 3: Route to handler
    await route_message(update, context, msg_context, text)
```

**Line count: ~24 lines** (well under 40 target)

## Implementation Plan

### Phase 1: Create Data Models (30 min)

1. Create `src/models/message_context.py`:
   ```python
   from dataclasses import dataclass
   from typing import Optional, NamedTuple

   class ValidationResult(NamedTuple):
       is_valid: bool
       reason: str | None = None

   @dataclass
   class MessageContext:
       user_id: str
       subscription: Optional[dict]
       onboarding: Optional[dict]
       awaiting_custom_note: bool
       pending_note: Optional[dict]

       @property
       def is_pending_activation(self) -> bool:
           return self.subscription and self.subscription.get('status') == 'pending'

       @property
       def is_in_onboarding(self) -> bool:
           return self.onboarding and not self.onboarding.get('completed_at')

       @property
       def is_in_note_entry(self) -> bool:
           return self.awaiting_custom_note
   ```

### Phase 2: Extract Helper Functions (1 hour)

2. Create `src/handlers/message_helpers.py`:
   - Implement `validate_message_input()`
   - Implement `extract_message_context()`
   - Implement `format_response()`

3. Create `src/handlers/message_routing.py`:
   - Implement `route_message()`
   - Implement `_handle_pending_activation()`
   - Implement `_handle_custom_note_entry()`
   - Implement `_handle_ai_message()`

### Phase 3: Refactor main function (30 min)

4. Update `src/bot.py`:
   - Add imports for new modules
   - Replace 160-line `handle_message` with 40-line version
   - Verify all imports are correct

### Phase 4: Testing (1 hour)

5. Manual testing:
   - Test pending activation flow
   - Test onboarding flow
   - Test custom note entry flow
   - Test normal AI message flow
   - Test topic filter
   - Test authorization
   - Test Markdown fallback
   - Test error handling

6. Edge cases:
   - Missing pending_note data
   - Invalid invite codes
   - Markdown parse errors
   - Database errors during note saving

## Files to Create

1. `src/models/message_context.py` - Data models
2. `src/handlers/message_helpers.py` - Validation, context extraction, formatting
3. `src/handlers/message_routing.py` - Routing logic and route handlers

## Files to Modify

1. `src/bot.py` - Replace handle_message function

## Success Criteria

✅ `handle_message` reduced from 160 lines to ~40 lines
✅ All routing logic extracted to separate functions
✅ All validation logic extracted to separate functions
✅ All formatting logic extracted to separate functions
✅ No behavioral changes - all flows work exactly as before
✅ Error handling preserved
✅ Logging preserved
✅ Code is more testable (smaller, focused functions)
✅ Code is more maintainable (clear separation of concerns)

## Testing Strategy

### Unit Tests (Future Work)

Create `tests/test_message_routing.py`:
- Test `validate_message_input()` with different scenarios
- Test `extract_message_context()` with various user states
- Test `route_message()` routing logic
- Test `format_response()` Markdown fallback

### Manual Testing Checklist

- [ ] Pending user sends invite code → activates
- [ ] Pending user sends non-code → gets prompt
- [ ] User in onboarding → routes to onboarding handler
- [ ] User entering custom note → saves note correctly
- [ ] User sends /cancel during note entry → cancels
- [ ] Normal user sends message → gets AI response
- [ ] Topic filter works correctly
- [ ] Unauthorized user is blocked
- [ ] Markdown parse error → falls back to plain text
- [ ] Error in AI processing → shows error message

## Dependencies

- No new external dependencies
- Uses existing:
  - `telegram` (Update, ContextTypes)
  - `src.db.queries` (database functions)
  - `src.utils.auth` (is_authorized)
  - `src.agent` (get_agent_response)
  - `src.handlers.onboarding` (handle_onboarding_message)

## Risks & Mitigation

**Risk 1:** Breaking existing functionality during refactor
**Mitigation:** Thorough manual testing of all flows

**Risk 2:** Missing edge cases in routing logic
**Mitigation:** Careful code review, preserve all existing checks

**Risk 3:** Import issues with circular dependencies
**Mitigation:** Keep helpers in separate modules, avoid circular imports

## Future Improvements

After this refactor is complete, consider:

1. **Unit tests** for each extracted function
2. **Integration tests** for full message flows
3. **Type hints** throughout (already using in proposed code)
4. **Remove commented timezone code** (lines 790-833)
5. **Extract background_memory_tasks** to separate module

## Timeline

- **Phase 1** (Data models): 30 min
- **Phase 2** (Helper functions): 1 hour
- **Phase 3** (Main refactor): 30 min
- **Phase 4** (Testing): 1 hour

**Total: 3 hours** (matches estimate)

## Approval Required

This plan requires review before implementation because:
- It touches a critical message handling path
- Changes affect all user interactions
- Risk of regression if not done carefully

Once approved, implementation can proceed phase-by-phase with testing after each phase.
