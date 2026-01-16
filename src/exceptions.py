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

    Example:
        raise HealthAgentError(
            message="Failed to save user data",
            user_id="123456",
            operation="save_food_entry",
            context={"entry_id": "abc-123"}
        )
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
            "error_message": self.message,  # Avoid conflict with logging's 'message' field
            "request_id": self.request_id,
            "user_id": self.user_id,
            "operation": self.operation,
            "error_context": self.context,  # Avoid conflict with logging's 'context'
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

    Example:
        raise ValidationError(
            message="Quantity must be positive",
            field="quantity",
            value=-5,
            user_id="123456"
        )
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

    Example:
        try:
            await db.execute(query)
        except psycopg.Error as e:
            raise wrap_external_exception(
                e,
                operation="save_food_entry",
                user_id="123456",
                context={"query": query}
            )
    """
    # Import here to avoid circular dependencies
    try:
        import psycopg
    except ImportError:
        psycopg = None

    try:
        import httpx
    except ImportError:
        httpx = None

    # Database errors
    if psycopg and isinstance(error, psycopg.OperationalError):
        return ConnectionError(
            message=f"Database connection failed: {str(error)}",
            user_id=user_id,
            operation=operation,
            context=context,
            cause=error
        )
    elif psycopg and isinstance(error, psycopg.Error):
        return QueryError(
            message=f"Database query failed: {str(error)}",
            user_id=user_id,
            operation=operation,
            context=context,
            cause=error
        )

    # HTTP errors
    elif httpx and isinstance(error, httpx.TimeoutException):
        return ExternalAPIError(
            message=f"API request timed out: {str(error)}",
            user_id=user_id,
            operation=operation,
            context=context,
            cause=error
        )
    elif httpx and isinstance(error, httpx.HTTPStatusError):
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
