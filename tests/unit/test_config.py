"""Tests for Pydantic Settings configuration validation"""
import os
import pytest
from pathlib import Path
from pydantic import ValidationError

from src.config import Settings


class TestConfigValidation:
    """Test configuration validation with Pydantic Settings"""

    def test_valid_configuration_loads(self, monkeypatch):
        """Test that a valid configuration loads successfully"""
        # Set valid environment variables
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABC-DEF_GHI")
        monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "123456789,987654321")
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test123")

        settings = Settings()

        assert settings.telegram_bot_token == "123456789:ABC-DEF_GHI"
        assert settings.allowed_telegram_ids == ["123456789", "987654321"]
        assert settings.database_url == "postgresql://user:pass@localhost:5432/db"
        assert settings.anthropic_api_key == "sk-ant-test123"

    def test_missing_required_telegram_token(self, monkeypatch):
        """Test that missing TELEGRAM_BOT_TOKEN raises ValidationError"""
        monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "123456789")
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "telegram_bot_token" in str(exc_info.value)

    def test_missing_required_telegram_ids(self, monkeypatch):
        """Test that missing ALLOWED_TELEGRAM_IDS raises ValidationError"""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABC-DEF")
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "allowed_telegram_ids" in str(exc_info.value)

    def test_missing_required_database_url(self, monkeypatch):
        """Test that missing DATABASE_URL raises ValidationError"""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABC-DEF")
        monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "123456789")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "database_url" in str(exc_info.value)

    def test_invalid_database_url_format(self, monkeypatch):
        """Test that invalid DATABASE_URL format raises error"""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABC-DEF")
        monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "123456789")
        monkeypatch.setenv("DATABASE_URL", "mysql://localhost/db")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        error_str = str(exc_info.value)
        assert "postgresql://" in error_str or "postgres://" in error_str

    def test_invalid_database_url_structure(self, monkeypatch):
        """Test that invalid DATABASE_URL structure raises error"""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABC-DEF")
        monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "123456789")
        monkeypatch.setenv("DATABASE_URL", "postgresql://invalid")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "format invalid" in str(exc_info.value).lower()

    def test_invalid_port_range_too_high(self, monkeypatch):
        """Test that API_PORT above 65535 raises error"""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABC-DEF")
        monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "123456789")
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
        monkeypatch.setenv("API_PORT", "99999")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "65535" in str(exc_info.value)

    def test_invalid_port_range_too_low(self, monkeypatch):
        """Test that API_PORT below 1 raises error"""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABC-DEF")
        monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "123456789")
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
        monkeypatch.setenv("API_PORT", "0")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "api_port" in str(exc_info.value)

    def test_invalid_log_level(self, monkeypatch):
        """Test that invalid LOG_LEVEL raises error"""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABC-DEF")
        monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "123456789")
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
        monkeypatch.setenv("LOG_LEVEL", "INVALID")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "log_level" in str(exc_info.value)

    def test_invalid_run_mode(self, monkeypatch):
        """Test that invalid RUN_MODE raises error"""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABC-DEF")
        monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "123456789")
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
        monkeypatch.setenv("RUN_MODE", "invalid")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "run_mode" in str(exc_info.value)

    def test_openai_model_without_api_key(self, monkeypatch):
        """Test that using OpenAI model without API key raises error"""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABC-DEF")
        monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "123456789")
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
        monkeypatch.setenv("VISION_MODEL", "openai:gpt-4o-mini")
        monkeypatch.setenv("AGENT_MODEL", "anthropic:claude-3-5-sonnet-latest")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        # No OPENAI_API_KEY set

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        error_str = str(exc_info.value)
        assert "OPENAI_API_KEY" in error_str
        assert "VISION_MODEL" in error_str

    def test_anthropic_model_without_api_key(self, monkeypatch):
        """Test that using Anthropic model without API key raises error"""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABC-DEF")
        monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "123456789")
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
        monkeypatch.setenv("VISION_MODEL", "openai:gpt-4o-mini")
        monkeypatch.setenv("AGENT_MODEL", "anthropic:claude-3-5-sonnet-latest")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        # No ANTHROPIC_API_KEY set

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        error_str = str(exc_info.value)
        assert "ANTHROPIC_API_KEY" in error_str
        assert "AGENT_MODEL" in error_str

    def test_invalid_telegram_token_format(self, monkeypatch):
        """Test that invalid Telegram token format raises error"""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "invalid-token")
        monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "123456789")
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "telegram_bot_token" in str(exc_info.value)

    def test_non_numeric_telegram_id(self, monkeypatch):
        """Test that non-numeric Telegram ID raises error"""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABC-DEF")
        monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "abc123")
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        error_str = str(exc_info.value)
        assert "numeric" in error_str.lower()

    def test_empty_telegram_ids(self, monkeypatch):
        """Test that empty ALLOWED_TELEGRAM_IDS raises error"""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABC-DEF")
        monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "")
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        error_str = str(exc_info.value)
        assert "cannot be empty" in error_str.lower()

    def test_comma_separated_telegram_ids_parsing(self, monkeypatch):
        """Test that comma-separated Telegram IDs are parsed correctly"""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABC-DEF")
        monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "123456789, 987654321, 555555555")
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        settings = Settings()

        assert len(settings.allowed_telegram_ids) == 3
        assert settings.allowed_telegram_ids == ["123456789", "987654321", "555555555"]

    def test_comma_separated_api_keys_parsing(self, monkeypatch):
        """Test that comma-separated API keys are parsed correctly"""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABC-DEF")
        monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "123456789")
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
        monkeypatch.setenv("API_KEYS", "key1, key2, key3")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        settings = Settings()

        assert len(settings.api_keys) == 3
        assert settings.api_keys == ["key1", "key2", "key3"]

    def test_comma_separated_cors_origins_parsing(self, monkeypatch):
        """Test that comma-separated CORS origins are parsed correctly"""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABC-DEF")
        monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "123456789")
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000, http://example.com")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        settings = Settings()

        assert len(settings.cors_origins) == 2
        assert settings.cors_origins == ["http://localhost:3000", "http://example.com"]

    def test_default_values_applied(self, monkeypatch):
        """Test that default values are applied correctly"""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABC-DEF")
        monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "123456789")
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        settings = Settings()

        assert settings.telegram_topic_filter == "all"
        assert settings.log_level == "INFO"
        assert settings.run_mode == "bot"
        assert settings.api_host == "0.0.0.0"
        assert settings.api_port == 8080
        assert settings.usda_api_key == "DEMO_KEY"
        assert settings.enable_nutrition_verification is True
        assert settings.data_path == Path("./data")

    def test_data_path_converted_to_path(self, monkeypatch):
        """Test that DATA_PATH string is converted to Path object"""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABC-DEF")
        monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "123456789")
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
        monkeypatch.setenv("DATA_PATH", "/custom/path")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        settings = Settings()

        assert isinstance(settings.data_path, Path)
        assert settings.data_path == Path("/custom/path")

    def test_valid_log_levels(self, monkeypatch):
        """Test that all valid log levels are accepted"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_levels:
            monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABC-DEF")
            monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "123456789")
            monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
            monkeypatch.setenv("LOG_LEVEL", level)
            monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

            settings = Settings()
            assert settings.log_level == level

    def test_valid_run_modes(self, monkeypatch):
        """Test that all valid run modes are accepted"""
        valid_modes = ["bot", "api", "both"]

        for mode in valid_modes:
            monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABC-DEF")
            monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "123456789")
            monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
            monkeypatch.setenv("RUN_MODE", mode)
            monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

            settings = Settings()
            assert settings.run_mode == mode

    def test_postgres_url_scheme_accepted(self, monkeypatch):
        """Test that postgres:// scheme is also accepted"""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABC-DEF")
        monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "123456789")
        monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@localhost:5432/db")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        settings = Settings()
        assert settings.database_url == "postgres://user:pass@localhost:5432/db"

    def test_case_insensitive_env_vars(self, monkeypatch):
        """Test that environment variables are case-insensitive"""
        monkeypatch.setenv("telegram_bot_token", "123456789:ABC-DEF")
        monkeypatch.setenv("allowed_telegram_ids", "123456789")
        monkeypatch.setenv("database_url", "postgresql://user:pass@localhost:5432/db")
        monkeypatch.setenv("anthropic_api_key", "sk-ant-test")

        settings = Settings()
        assert settings.telegram_bot_token == "123456789:ABC-DEF"

    def test_both_api_keys_present(self, monkeypatch):
        """Test that both OpenAI and Anthropic keys can be set"""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:ABC-DEF")
        monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "123456789")
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/db")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setenv("VISION_MODEL", "openai:gpt-4o-mini")
        monkeypatch.setenv("AGENT_MODEL", "anthropic:claude-3-5-sonnet-latest")

        settings = Settings()
        assert settings.openai_api_key == "sk-test-openai"
        assert settings.anthropic_api_key == "sk-ant-test"
