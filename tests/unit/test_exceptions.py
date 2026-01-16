"""Unit tests for custom exception hierarchy"""
import pytest
from datetime import datetime
from src.exceptions import (
    HealthAgentError,
    ValidationError,
    DatabaseError,
    ConnectionError,
    QueryError,
    RecordNotFoundError,
    ExternalAPIError,
    USDAAPIError,
    OpenAIAPIError,
    Mem0APIError,
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    AgentError,
    ToolValidationError,
    VisionAnalysisError,
    NutritionValidationError,
    TelegramBotError,
    MessageSendError,
    wrap_external_exception
)


class TestHealthAgentError:
    """Test base exception class"""

    def test_basic_exception(self):
        """Test basic exception creation"""
        error = HealthAgentError("Test error")
        assert error.message == "Test error"
        assert error.user_message == "An error occurred. Please try again."
        assert error.request_id is not None
        assert isinstance(error.timestamp, datetime)

    def test_exception_with_context(self):
        """Test exception with full context"""
        error = HealthAgentError(
            message="Database save failed",
            user_id="123456",
            operation="save_food_entry",
            context={"entry_id": "abc-123"},
            user_message="Could not save your food entry"
        )
        assert error.user_id == "123456"
        assert error.operation == "save_food_entry"
        assert error.context["entry_id"] == "abc-123"
        assert error.user_message == "Could not save your food entry"

    def test_exception_with_cause(self):
        """Test exception wrapping another exception"""
        original_error = ValueError("Invalid value")
        error = HealthAgentError(
            message="Validation failed",
            cause=original_error
        )
        assert error.cause == original_error

    def test_to_dict(self):
        """Test exception serialization"""
        error = HealthAgentError(
            message="Test error",
            user_id="123456"
        )
        error_dict = error.to_dict()
        assert error_dict["error"] == "HealthAgentError"
        assert error_dict["message"] == "Test error"
        assert error_dict["user_message"] == "An error occurred. Please try again."
        assert "request_id" in error_dict
        assert "timestamp" in error_dict


class TestValidationError:
    """Test validation error"""

    def test_validation_error(self):
        """Test validation error with field"""
        error = ValidationError(
            message="Must be positive",
            field="quantity",
            value=-5
        )
        assert error.field == "quantity"
        assert error.value == -5
        assert "Invalid quantity" in error.user_message


class TestDatabaseErrors:
    """Test database-related errors"""

    def test_connection_error(self):
        """Test connection error"""
        error = ConnectionError()
        assert "connection" in error.message.lower()
        assert "database" in error.user_message.lower()

    def test_query_error(self):
        """Test query error"""
        error = QueryError(
            message="Query failed",
            query="SELECT * FROM users"
        )
        assert error.query == "SELECT * FROM users"

    def test_record_not_found(self):
        """Test record not found"""
        error = RecordNotFoundError(
            message="User not found",
            record_type="User",
            record_id="123"
        )
        assert error.record_type == "User"
        assert error.record_id == "123"
        assert "User not found" in error.user_message


class TestExternalAPIErrors:
    """Test external API errors"""

    def test_generic_api_error(self):
        """Test generic API error"""
        error = ExternalAPIError(
            message="API failed",
            service="TestAPI",
            status_code=500
        )
        assert error.service == "TestAPI"
        assert error.status_code == 500
        assert "TestAPI" in error.user_message

    def test_usda_api_error(self):
        """Test USDA-specific error"""
        error = USDAAPIError("USDA API timeout")
        assert error.service == "USDA FoodData Central"

    def test_openai_api_error(self):
        """Test OpenAI-specific error"""
        error = OpenAIAPIError("OpenAI rate limit")
        assert error.service == "OpenAI"

    def test_mem0_api_error(self):
        """Test Mem0-specific error"""
        error = Mem0APIError("Mem0 connection failed")
        assert error.service == "Mem0 Memory"
        assert "memory" in error.user_message.lower()


class TestAuthErrors:
    """Test authentication/authorization errors"""

    def test_authentication_error(self):
        """Test authentication error"""
        error = AuthenticationError()
        assert "authentication" in error.message.lower()
        assert "authentication" in error.user_message.lower()

    def test_authorization_error(self):
        """Test authorization error"""
        error = AuthorizationError(resource="admin_panel")
        assert error.resource == "admin_panel"
        assert "permission" in error.user_message.lower()


class TestConfigurationError:
    """Test configuration errors"""

    def test_configuration_error(self):
        """Test configuration error"""
        error = ConfigurationError(
            message="Missing API key",
            config_key="OPENAI_API_KEY"
        )
        assert error.config_key == "OPENAI_API_KEY"
        assert "configured" in error.user_message.lower()


class TestAgentErrors:
    """Test agent/AI errors"""

    def test_tool_validation_error(self):
        """Test tool validation error"""
        error = ToolValidationError(
            message="Unsafe code detected",
            tool_name="delete_files"
        )
        assert error.tool_name == "delete_files"
        assert "unsafe" in error.user_message.lower()

    def test_vision_analysis_error(self):
        """Test vision analysis error"""
        error = VisionAnalysisError("Could not analyze image")
        assert "photo" in error.user_message.lower()

    def test_nutrition_validation_error(self):
        """Test nutrition validation error"""
        error = NutritionValidationError("Invalid macros")
        assert "nutrition" in error.user_message.lower()


class TestTelegramErrors:
    """Test Telegram bot errors"""

    def test_message_send_error(self):
        """Test message send error"""
        error = MessageSendError("Network timeout")
        assert "message" in error.user_message.lower()


class TestWrapExternalException:
    """Test exception wrapping helper"""

    def test_wrap_generic_exception(self):
        """Test wrapping generic exception"""
        original = ValueError("Invalid input")
        wrapped = wrap_external_exception(
            original,
            operation="process_data",
            user_id="123"
        )
        assert isinstance(wrapped, HealthAgentError)
        assert wrapped.cause == original
        assert wrapped.operation == "process_data"
        assert wrapped.user_id == "123"

    def test_wrap_psycopg_operational_error(self):
        """Test wrapping psycopg operational error"""
        try:
            import psycopg
            original = psycopg.OperationalError("Connection refused")
            wrapped = wrap_external_exception(
                original,
                operation="connect_db"
            )
            assert isinstance(wrapped, ConnectionError)
            assert wrapped.cause == original
        except ImportError:
            pytest.skip("psycopg not installed")

    def test_wrap_psycopg_error(self):
        """Test wrapping generic psycopg error"""
        try:
            import psycopg
            original = psycopg.Error("Query failed")
            wrapped = wrap_external_exception(
                original,
                operation="execute_query"
            )
            assert isinstance(wrapped, QueryError)
            assert wrapped.cause == original
        except ImportError:
            pytest.skip("psycopg not installed")

    def test_wrap_httpx_timeout(self):
        """Test wrapping httpx timeout"""
        try:
            import httpx
            original = httpx.TimeoutException("Request timeout")
            wrapped = wrap_external_exception(
                original,
                operation="api_call"
            )
            assert isinstance(wrapped, ExternalAPIError)
            assert "timeout" in wrapped.message.lower()
        except ImportError:
            pytest.skip("httpx not installed")


class TestInheritance:
    """Test exception hierarchy"""

    def test_all_inherit_from_base(self):
        """Test that all custom exceptions inherit from HealthAgentError"""
        exceptions = [
            ValidationError("test"),
            DatabaseError("test"),
            ConnectionError(),
            QueryError("test"),
            RecordNotFoundError("test"),
            ExternalAPIError("test"),
            USDAAPIError("test"),
            OpenAIAPIError("test"),
            Mem0APIError("test"),
            AuthenticationError(),
            AuthorizationError(),
            ConfigurationError("test"),
            AgentError("test"),
            ToolValidationError("test"),
            VisionAnalysisError("test"),
            NutritionValidationError("test"),
            TelegramBotError("test"),
            MessageSendError("test")
        ]
        for exc in exceptions:
            assert isinstance(exc, HealthAgentError)
            assert isinstance(exc, Exception)

    def test_database_hierarchy(self):
        """Test database error hierarchy"""
        conn_error = ConnectionError()
        query_error = QueryError("test")
        not_found = RecordNotFoundError("test")

        assert isinstance(conn_error, DatabaseError)
        assert isinstance(query_error, DatabaseError)
        assert isinstance(not_found, DatabaseError)

    def test_agent_hierarchy(self):
        """Test agent error hierarchy"""
        tool_error = ToolValidationError("test")
        vision_error = VisionAnalysisError("test")
        nutrition_error = NutritionValidationError("test")

        assert isinstance(tool_error, AgentError)
        assert isinstance(vision_error, AgentError)
        assert isinstance(nutrition_error, AgentError)
