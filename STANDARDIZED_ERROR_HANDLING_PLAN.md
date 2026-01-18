# Standardized Error Handling Implementation Plan

**Issue:** #71
**Priority:** MEDIUM
**Estimated Time:** 4 hours
**Epic:** 007 - Phase 2 High-Priority Refactoring

## Executive Summary

This plan implements a comprehensive, standardized error handling system across the health-agent codebase. The solution creates a custom exception hierarchy with rich context, consistent logging, and user-friendly error messages to improve debugging, monitoring, and user experience.

## Current State Analysis

### Existing Error Handling Patterns

1. **Generic Exception Catching (197+ instances across 35 files)**
   - Most handlers use broad `except Exception as e` patterns
   - Inconsistent error logging (216+ logger calls across 41 files)
   - Limited context preservation in error messages
   - Mix of error handling approaches

2. **Current Custom Exceptions**
   - `CodeValidationError` in `src/agent/dynamic_tools.py` (single use case)
   - FastAPI's `HTTPException` for API errors (2 files)
   - Telegram's native error types (`telegram.error.*`) for bot operations

3. **Key Pain Points**
   - Database errors lose connection context
   - API failures don't preserve request details
   - External service errors (USDA, Mem0, OpenAI) lack tracing
   - Authentication failures don't provide enough diagnostic info
   - No standardized way to distinguish user vs. system errors

### Files with Heavy Exception Usage

**Database Layer (High Priority):**
- `src/db/queries.py` (6 try/except blocks)
- `src/db/connection.py` (connection pool errors)
- `src/db/food_entry_utils.py` (5 try/except blocks)

**API Layer (High Priority):**
- `src/api/routes.py` (18 exception handlers)
- `src/api/auth.py` (authentication errors)
- `src/api/server.py` (startup/shutdown errors)

**Bot Layer (High Priority):**
- `src/bot.py` (19 try/except blocks)
- `src/handlers/*.py` (multiple handlers with inconsistent error handling)

**External Integrations (Medium Priority):**
- `src/memory/mem0_manager.py` (5 try/except blocks)
- `src/utils/nutrition_search.py` (4 try/except blocks)
- `src/utils/vision.py` (4 try/except blocks)
- `src/utils/voice.py` (voice transcription errors)
- `src/utils/web_nutrition_search.py` (4 try/except blocks)

**Agent/AI Layer (Medium Priority):**
- `src/agent/__init__.py` (39 try/except blocks)
- `src/agent/dynamic_tools.py` (4 try/except blocks)
- `src/agent/nutrition_*.py` (multiple validation/consensus handlers)

## Solution Design

### 1. Exception Hierarchy (`src/exceptions.py`)

```python
"""
Standardized exception hierarchy for health-agent
Provides rich context, consistent logging, and user-friendly error messages
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)


class HealthAgentError(Exception):
    """
    Base exception for all health-agent errors

    Provides:
    - Automatic timestamping
    - Request ID for tracing
    - User-friendly messages
    - Structured context
    - Automatic logging
    """

    def __init__(
        self,
        message: str,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        operation: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.user_id = user_id
        self.request_id = request_id or str(uuid4())
        self.operation = operation
        self.context = context or {}
        self.cause = cause
        self.user_message = user_message or "An error occurred. Please try again."
        self.timestamp = datetime.utcnow()

        # Auto-log on creation
        self._log_error()

    def _log_error(self) -> None:
        """Log error with full context"""
        log_data = {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "request_id": self.request_id,
            "user_id": self.user_id,
            "operation": self.operation,
            "context": self.context,
            "timestamp": self.timestamp.isoformat()
        }

        if self.cause:
            log_data["cause"] = str(self.cause)
            logger.error(f"{self.__class__.__name__}: {self.message}", extra=log_data, exc_info=self.cause)
        else:
            logger.error(f"{self.__class__.__name__}: {self.message}", extra=log_data)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize exception for API responses"""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "user_message": self.user_message,
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat()
        }


# ==========================================
# Validation Errors (User Input)
# ==========================================

class ValidationError(HealthAgentError):
    """
    Raised when user input fails validation

    Examples:
    - Invalid food quantity
    - Malformed tracking data
    - Invalid reminder time
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ):
        self.field = field
        self.value = value
        super().__init__(
            message=message,
            user_message=f"Invalid {field}: {message}" if field else message,
            context={"field": field, "value": value},
            **kwargs
        )


# ==========================================
# Database Errors
# ==========================================

class DatabaseError(HealthAgentError):
    """
    Base class for database-related errors
    """
    pass


class ConnectionError(DatabaseError):
    """Database connection failed"""

    def __init__(self, message: str = "Database connection failed", **kwargs):
        super().__init__(
            message=message,
            user_message="We're having trouble connecting to the database. Please try again in a moment.",
            **kwargs
        )


class QueryError(DatabaseError):
    """Database query execution failed"""

    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        **kwargs
    ):
        self.query = query
        super().__init__(
            message=message,
            user_message="We encountered an issue saving your data. Please try again.",
            context={"query": query},
            **kwargs
        )


class RecordNotFoundError(DatabaseError):
    """Requested database record does not exist"""

    def __init__(
        self,
        message: str,
        record_type: Optional[str] = None,
        record_id: Optional[str] = None,
        **kwargs
    ):
        self.record_type = record_type
        self.record_id = record_id
        super().__init__(
            message=message,
            user_message=f"{record_type or 'Record'} not found.",
            context={"record_type": record_type, "record_id": record_id},
            **kwargs
        )


# ==========================================
# External API Errors
# ==========================================

class ExternalAPIError(HealthAgentError):
    """
    Base class for external API failures
    """

    def __init__(
        self,
        message: str,
        service: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs
    ):
        self.service = service
        self.status_code = status_code
        super().__init__(
            message=message,
            user_message=f"We're having trouble connecting to {service or 'an external service'}. Please try again later.",
            context={"service": service, "status_code": status_code},
            **kwargs
        )


class USDAAPIError(ExternalAPIError):
    """USDA FoodData Central API error"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            service="USDA FoodData Central",
            **kwargs
        )


class OpenAIAPIError(ExternalAPIError):
    """OpenAI API error (vision, embeddings, etc.)"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            service="OpenAI",
            **kwargs
        )


class Mem0APIError(ExternalAPIError):
    """Mem0 memory service error"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            service="Mem0 Memory",
            user_message="We're having trouble accessing your memory. Your current conversation will still work.",
            **kwargs
        )


# ==========================================
# Authentication & Authorization
# ==========================================

class AuthenticationError(HealthAgentError):
    """Authentication failed"""

    def __init__(
        self,
        message: str = "Authentication failed",
        **kwargs
    ):
        super().__init__(
            message=message,
            user_message="Authentication failed. Please check your credentials.",
            **kwargs
        )


class AuthorizationError(HealthAgentError):
    """User lacks permission for requested operation"""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        resource: Optional[str] = None,
        **kwargs
    ):
        self.resource = resource
        super().__init__(
            message=message,
            user_message=f"You don't have permission to access {resource or 'this resource'}.",
            context={"resource": resource},
            **kwargs
        )


# ==========================================
# Configuration Errors
# ==========================================

class ConfigurationError(HealthAgentError):
    """System configuration is invalid or missing"""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        **kwargs
    ):
        self.config_key = config_key
        super().__init__(
            message=message,
            user_message="The system is not properly configured. Please contact support.",
            context={"config_key": config_key},
            **kwargs
        )


# ==========================================
# Agent/AI Errors
# ==========================================

class AgentError(HealthAgentError):
    """AI agent processing error"""
    pass


class ToolValidationError(AgentError):
    """Dynamic tool code validation failed"""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        **kwargs
    ):
        self.tool_name = tool_name
        super().__init__(
            message=message,
            user_message="The requested tool contains unsafe code and cannot be executed.",
            context={"tool_name": tool_name},
            **kwargs
        )


class VisionAnalysisError(AgentError):
    """Food photo vision analysis failed"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            user_message="We couldn't analyze your food photo. Please try again or describe your meal manually.",
            **kwargs
        )


class NutritionValidationError(AgentError):
    """Nutrition data validation failed"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            user_message="We couldn't validate the nutrition data. Please check your entry.",
            **kwargs
        )


# ==========================================
# Telegram Bot Errors
# ==========================================

class TelegramBotError(HealthAgentError):
    """Telegram bot operation failed"""
    pass


class MessageSendError(TelegramBotError):
    """Failed to send Telegram message"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            user_message="We couldn't send your message. Please try again.",
            **kwargs
        )


# ==========================================
# Helper Functions
# ==========================================

def wrap_external_exception(
    error: Exception,
    operation: str,
    user_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> HealthAgentError:
    """
    Wrap external exceptions (psycopg, httpx, etc.) into our exception hierarchy

    Args:
        error: Original exception
        operation: What operation was being performed
        user_id: User ID if applicable
        context: Additional context

    Returns:
        Appropriate HealthAgentError subclass
    """
    import psycopg
    import httpx

    # Database errors
    if isinstance(error, psycopg.OperationalError):
        return ConnectionError(
            message=f"Database connection failed: {str(error)}",
            user_id=user_id,
            operation=operation,
            context=context,
            cause=error
        )
    elif isinstance(error, psycopg.Error):
        return QueryError(
            message=f"Database query failed: {str(error)}",
            user_id=user_id,
            operation=operation,
            context=context,
            cause=error
        )

    # HTTP errors
    elif isinstance(error, httpx.TimeoutException):
        return ExternalAPIError(
            message=f"API request timed out: {str(error)}",
            user_id=user_id,
            operation=operation,
            context=context,
            cause=error
        )
    elif isinstance(error, httpx.HTTPStatusError):
        return ExternalAPIError(
            message=f"API returned error: {error.response.status_code}",
            status_code=error.response.status_code,
            user_id=user_id,
            operation=operation,
            context=context,
            cause=error
        )

    # Generic fallback
    else:
        return HealthAgentError(
            message=f"{operation} failed: {str(error)}",
            user_id=user_id,
            operation=operation,
            context=context,
            cause=error
        )
```

## Implementation Plan

### Phase 1: Foundation (30 minutes)

**1.1 Create Exception Module**
- [ ] Create `src/exceptions.py` with full hierarchy
- [ ] Add docstrings and usage examples
- [ ] Create unit tests for exception behavior

**Files to create:**
- `src/exceptions.py` (new file)
- `tests/unit/test_exceptions.py` (new file)

### Phase 2: Core Infrastructure Updates (60 minutes)

**2.1 Database Layer**
- [ ] Update `src/db/connection.py`
  - Wrap connection pool errors in `ConnectionError`
  - Handle `RuntimeError` on uninitialized pool
- [ ] Update `src/db/queries.py`
  - Wrap all psycopg errors with `wrap_external_exception()`
  - Use `RecordNotFoundError` for missing records
  - Use `QueryError` for failed operations
- [ ] Update `src/db/food_entry_utils.py`
  - Use `ValidationError` for invalid food data
  - Use `QueryError` for database operations

**2.2 Configuration**
- [ ] Update `src/config.py`
  - Replace `ValueError` with `ConfigurationError`
  - Add detailed context for missing config

### Phase 3: API Layer (45 minutes)

**3.1 API Routes**
- [ ] Update `src/api/routes.py`
  - Catch `HealthAgentError` and convert to JSON responses
  - Replace generic `HTTPException` with specific errors
  - Use `RecordNotFoundError` → 404
  - Use `ValidationError` → 400
  - Use `AuthenticationError` → 401
  - Use `DatabaseError` → 500

**3.2 Authentication**
- [ ] Update `src/api/auth.py`
  - Replace `HTTPException` with `AuthenticationError`
  - Add request context to errors

**3.3 Global Exception Handler**
- [ ] Update `src/api/server.py`
  - Add FastAPI exception handler for `HealthAgentError`
  - Serialize exceptions with `to_dict()`
  - Preserve request IDs in responses

### Phase 4: External Integrations (45 minutes)

**4.1 Memory Systems**
- [ ] Update `src/memory/mem0_manager.py`
  - Use `Mem0APIError` for initialization failures
  - Use `ConfigurationError` for missing API keys
  - Graceful degradation on errors

**4.2 Nutrition Services**
- [ ] Update `src/utils/nutrition_search.py`
  - Use `USDAAPIError` for API failures
  - Use `wrap_external_exception()` for httpx errors
- [ ] Update `src/utils/web_nutrition_search.py`
  - Similar error wrapping
- [ ] Update `src/utils/nutrition_validation.py`
  - Use `NutritionValidationError`

**4.3 AI Services**
- [ ] Update `src/utils/vision.py`
  - Use `VisionAnalysisError` for photo analysis failures
  - Use `OpenAIAPIError` for API errors
- [ ] Update `src/utils/voice.py`
  - Use `OpenAIAPIError` for transcription failures

### Phase 5: Agent & Bot Layer (60 minutes)

**5.1 Agent Core**
- [ ] Update `src/agent/__init__.py`
  - Use appropriate errors for tool failures
  - Preserve user_id in all errors
  - Add operation context
- [ ] Update `src/agent/dynamic_tools.py`
  - Replace `CodeValidationError` with new `ToolValidationError`
  - Maintain backward compatibility

**5.2 Bot Handlers**
- [ ] Update `src/bot.py`
  - Catch `HealthAgentError` and send `user_message` to Telegram
  - Log full error context
  - Handle `telegram.error.*` exceptions
- [ ] Update handlers (`src/handlers/*.py`)
  - Use `ValidationError` for invalid input
  - Use `MessageSendError` for Telegram failures
  - Consistent error responses

### Phase 6: Testing & Documentation (30 minutes)

**6.1 Unit Tests**
- [ ] Test exception hierarchy
- [ ] Test auto-logging behavior
- [ ] Test `wrap_external_exception()` with various error types
- [ ] Test serialization (`to_dict()`)

**6.2 Integration Tests**
- [ ] Test database error propagation
- [ ] Test API error responses
- [ ] Test Telegram error handling

**6.3 Documentation**
- [ ] Add usage examples to `src/exceptions.py`
- [ ] Update `DEVELOPMENT.md` with error handling guidelines
- [ ] Document error handling best practices

## Migration Strategy

### Backward Compatibility
- Keep existing `try/except` blocks functional during transition
- Gradually replace generic exceptions with custom ones
- Maintain existing API error codes

### Rollout Sequence
1. **Deploy exception module** (non-breaking)
2. **Update database layer** (internal, low risk)
3. **Update API layer** (requires API versioning consideration)
4. **Update bot handlers** (test with small user group first)
5. **Complete remaining integrations**

### Risk Mitigation
- Preserve all existing error logging
- Add new structured logging without removing old logs
- Test each layer independently
- Gradual rollout with monitoring

## Success Criteria

1. **Zero generic `Exception` catching in core paths**
   - Database, API, Agent, Bot layers use custom exceptions

2. **Consistent logging structure**
   - All errors include: timestamp, request_id, user_id, operation, context

3. **User-friendly error messages**
   - All exceptions have appropriate `user_message`
   - Telegram bot shows helpful errors
   - API returns structured error responses

4. **Improved debugging**
   - Request IDs enable tracing across services
   - Structured logging enables better monitoring
   - Original exception cause preserved

5. **Test coverage**
   - 90%+ coverage for `src/exceptions.py`
   - Integration tests for error propagation

## Files Modified

### New Files (2)
1. `src/exceptions.py`
2. `tests/unit/test_exceptions.py`

### Modified Files (30+)

**Core Infrastructure:**
- `src/db/connection.py`
- `src/db/queries.py`
- `src/db/food_entry_utils.py`
- `src/config.py`

**API Layer:**
- `src/api/routes.py`
- `src/api/auth.py`
- `src/api/server.py`

**External Integrations:**
- `src/memory/mem0_manager.py`
- `src/utils/nutrition_search.py`
- `src/utils/web_nutrition_search.py`
- `src/utils/nutrition_validation.py`
- `src/utils/vision.py`
- `src/utils/voice.py`

**Agent & Bot:**
- `src/agent/__init__.py`
- `src/agent/dynamic_tools.py`
- `src/bot.py`
- `src/handlers/onboarding.py`
- `src/handlers/sleep_quiz.py`
- `src/handlers/reminders.py`
- `src/handlers/tracking.py`
- `src/handlers/food_photo.py`
- `src/handlers/settings.py`
- `src/handlers/sleep_settings.py`

**Scheduler:**
- `src/scheduler/reminder_manager.py`

**Documentation:**
- `DEVELOPMENT.md`

## Timeline

| Phase | Duration | Tasks |
|-------|----------|-------|
| Phase 1 | 30 min | Create exception module + tests |
| Phase 2 | 60 min | Database + config updates |
| Phase 3 | 45 min | API layer updates |
| Phase 4 | 45 min | External integrations |
| Phase 5 | 60 min | Agent + bot layer |
| Phase 6 | 30 min | Testing + documentation |
| **Total** | **4 hours** | |

## Post-Implementation

### Monitoring
- Track error frequency by type
- Monitor request IDs for tracing
- Alert on configuration errors (critical)
- Track database connection errors (critical)

### Future Enhancements
- Integrate with Sentry for error tracking
- Add retry logic for transient external API errors
- Implement circuit breakers for external services
- Add error rate limiting to prevent log flooding

## Notes

- This implementation maintains full backward compatibility
- All existing error handling continues to work during migration
- Changes can be deployed incrementally without breaking functionality
- Focus on high-traffic code paths first (database, API, bot)
