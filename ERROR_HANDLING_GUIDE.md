# Error Handling Guide

## Overview

The health-agent application uses a standardized exception hierarchy defined in `src/exceptions.py`. This provides consistent error handling, structured logging, and user-friendly error messages across the entire codebase.

## Exception Hierarchy

```
HealthAgentError (base)
├── ValidationError (user input errors)
├── DatabaseError
│   ├── ConnectionError
│   ├── QueryError
│   └── RecordNotFoundError
├── ExternalAPIError
│   ├── USDAAPIError
│   ├── OpenAIAPIError
│   └── Mem0APIError
├── AuthenticationError
├── AuthorizationError
├── ConfigurationError
├── AgentError
│   ├── ToolValidationError
│   ├── VisionAnalysisError
│   └── NutritionValidationError
└── TelegramBotError
    └── MessageSendError
```

## Key Features

### 1. Automatic Context Capture

All exceptions automatically capture:
- **User ID**: If applicable
- **Request ID**: Unique identifier for tracing (auto-generated UUID)
- **Operation**: What operation was being performed
- **Timestamp**: When the error occurred (UTC)
- **Cause**: Original exception if wrapping another error

### 2. Dual Messages

Every exception has two message types:
- **Technical message** (`message`): Detailed error for logs and developers
- **User message** (`user_message`): Friendly message safe to show to end users

### 3. Automatic Logging

Exceptions log themselves automatically on creation with full context using structured logging.

### 4. API Serialization

All exceptions can be serialized to JSON for API responses via the `to_dict()` method.

## Usage Examples

### Basic Exception

```python
from src.exceptions import ValidationError

# Raise validation error
raise ValidationError(
    message="Quantity must be positive",
    field="quantity",
    value=-5,
    user_id="123456",
    operation="validate_food_entry"
)
```

### Database Errors

```python
from src.exceptions import RecordNotFoundError, wrap_external_exception

# Explicitly raise not found error
if not user_record:
    raise RecordNotFoundError(
        message=f"User {user_id} not found",
        record_type="User",
        record_id=user_id,
        user_id=user_id,
        operation="get_user"
    )

# Wrap database exceptions
try:
    await db.execute(query)
except psycopg.Error as e:
    raise wrap_external_exception(
        e,
        operation="save_food_entry",
        user_id=user_id,
        context={"entry_id": entry_id}
    )
```

### API Errors

```python
from src.exceptions import OpenAIAPIError

try:
    response = await openai_client.chat.completions.create(...)
except Exception as e:
    raise OpenAIAPIError(
        message=f"OpenAI API call failed: {str(e)}",
        user_id=user_id,
        operation="analyze_food_photo",
        status_code=getattr(e, 'status_code', None),
        cause=e
    )
```

### Configuration Errors

```python
from src.exceptions import ConfigurationError

if not api_key:
    raise ConfigurationError(
        message="OPENAI_API_KEY is required but not set",
        config_key="OPENAI_API_KEY"
    )
```

### Catching Exceptions

```python
from src.exceptions import (
    HealthAgentError,
    DatabaseError,
    ValidationError
)

try:
    await save_food_entry(entry)
except ValidationError as e:
    # User input error - show user_message
    await send_message(user_id, e.user_message)
except DatabaseError as e:
    # System error - log and show generic message
    logger.error(f"DB error: {e.request_id}")
    await send_message(user_id, "We're having trouble saving your data. Please try again.")
except HealthAgentError as e:
    # Catch any other custom error
    logger.error(f"Error: {e.request_id}")
    await send_message(user_id, e.user_message)
```

## Helper Functions

### wrap_external_exception()

Automatically converts external exceptions (psycopg, httpx, etc.) into our exception hierarchy:

```python
from src.exceptions import wrap_external_exception

try:
    async with db.connection() as conn:
        await conn.execute(query)
except Exception as e:
    raise wrap_external_exception(
        e,
        operation="execute_query",
        user_id=user_id,
        context={"query": query[:100]}
    )
```

This function detects the exception type and wraps it appropriately:
- `psycopg.OperationalError` → `ConnectionError`
- `psycopg.Error` → `QueryError`
- `httpx.TimeoutException` → `ExternalAPIError`
- `httpx.HTTPStatusError` → `ExternalAPIError` (with status code)
- Unknown exceptions → `HealthAgentError`

## FastAPI Integration

The FastAPI application (`src/api/server.py`) has global exception handlers that automatically convert our exceptions to appropriate HTTP responses:

| Exception | HTTP Status | Response |
|-----------|-------------|----------|
| `ValidationError` | 400 Bad Request | Serialized exception with `user_message` |
| `AuthenticationError` | 401 Unauthorized | Serialized exception |
| `AuthorizationError` | 403 Forbidden | Serialized exception |
| `RecordNotFoundError` | 404 Not Found | Serialized exception |
| `DatabaseError` | 500 Internal Server Error | Serialized exception |
| `ConfigurationError` | 503 Service Unavailable | Serialized exception |
| `HealthAgentError` | 500 Internal Server Error | Serialized exception |
| Other exceptions | 500 Internal Server Error | Generic error message |

Example API error response:

```json
{
  "error": "RecordNotFoundError",
  "message": "User 123456 not found",
  "user_message": "User not found.",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2026-01-16T12:34:56.789012"
}
```

## Logging Structure

All exceptions log with structured context:

```python
{
    "error_type": "DatabaseError",
    "error_message": "Failed to save food entry",
    "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "user_id": "123456",
    "operation": "save_food_entry",
    "error_context": {"entry_id": "abc-123"},
    "timestamp": "2026-01-16T12:34:56.789012",
    "cause": "connection refused"
}
```

This enables:
- **Request tracing** - Follow a single request through logs via `request_id`
- **User analysis** - See all errors for a specific user
- **Operation monitoring** - Track which operations fail most
- **Error aggregation** - Group by error type or cause

## Best Practices

### 1. Use Specific Exceptions

❌ **Don't:**
```python
raise Exception("Database error")
```

✅ **Do:**
```python
raise QueryError(
    message="Failed to insert food entry",
    user_id=user_id,
    operation="save_food_entry"
)
```

### 2. Provide Context

❌ **Don't:**
```python
raise ValidationError("Invalid input")
```

✅ **Do:**
```python
raise ValidationError(
    message="Quantity must be positive",
    field="quantity",
    value=quantity,
    user_id=user_id
)
```

### 3. Preserve Original Exceptions

❌ **Don't:**
```python
except psycopg.Error as e:
    raise DatabaseError(str(e))
```

✅ **Do:**
```python
except psycopg.Error as e:
    raise wrap_external_exception(
        e,
        operation="save_data",
        user_id=user_id
    )
```

### 4. Re-raise Custom Exceptions

❌ **Don't:**
```python
try:
    save_data()
except HealthAgentError as e:
    raise Exception(str(e))  # Loses context!
```

✅ **Do:**
```python
try:
    save_data()
except HealthAgentError:
    raise  # Preserves all context
```

### 5. Use User Messages Appropriately

❌ **Don't expose internal details:**
```python
raise DatabaseError(
    message="INSERT INTO users failed",
    user_message="INSERT INTO users failed"  # ❌ Internal detail
)
```

✅ **Do provide friendly messages:**
```python
raise DatabaseError(
    message="Failed to insert user record: duplicate key",
    user_message="This user already exists."  # ✅ User-friendly
)
```

## Migration from Old Error Handling

If you're updating existing code:

### Before
```python
try:
    result = await db.execute(query)
except Exception as e:
    logger.error(f"Database error: {e}")
    raise
```

### After
```python
try:
    result = await db.execute(query)
except Exception as e:
    raise wrap_external_exception(
        e,
        operation="execute_query",
        user_id=user_id,
        context={"query_type": "insert"}
    )
```

## Testing

```python
import pytest
from src.exceptions import ValidationError, RecordNotFoundError

def test_validation_error():
    """Test ValidationError creation and serialization"""
    error = ValidationError(
        message="Invalid quantity",
        field="quantity",
        value=-5,
        user_id="123"
    )

    assert error.field == "quantity"
    assert error.user_id == "123"
    assert "request_id" in error.to_dict()
    assert isinstance(error, HealthAgentError)

def test_exception_inheritance():
    """Test exception hierarchy"""
    error = RecordNotFoundError("not found")

    assert isinstance(error, DatabaseError)
    assert isinstance(error, HealthAgentError)
```

## Backward Compatibility

The old `CodeValidationError` from `src/agent/dynamic_tools.py` is now an alias for `ToolValidationError`:

```python
from src.agent.dynamic_tools import CodeValidationError  # Still works!
# Actually imports ToolValidationError from src.exceptions
```

## Further Reading

- See `src/exceptions.py` for complete exception definitions
- See `tests/unit/test_exceptions.py` for comprehensive tests
- See `STANDARDIZED_ERROR_HANDLING_PLAN.md` for original implementation plan
