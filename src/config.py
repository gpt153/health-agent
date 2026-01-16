"""Configuration management with Pydantic Settings validation"""
import sys
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration with comprehensive validation"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore unknown env vars
    )

    # Telegram Settings
    telegram_bot_token: str = Field(
        ...,  # Required
        description="Telegram bot token from @BotFather",
        pattern=r"^\d+:[A-Za-z0-9_-]+$",
    )

    allowed_telegram_ids: list[str] = Field(
        ...,  # Required
        description="Comma-separated list of allowed Telegram user IDs",
    )

    telegram_topic_filter: str = Field(
        default="all",
        description="Topic filter: 'all', 'none', whitelist (123,456), or blacklist (!123,456)",
    )

    # Database
    database_url: str = Field(
        ...,  # Required
        description="PostgreSQL connection URL",
    )

    # AI Models
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key (required if using OpenAI models)",
    )

    anthropic_api_key: str = Field(
        default="",
        description="Anthropic API key (required if using Anthropic models)",
    )

    vision_model: str = Field(
        default="openai:gpt-4o-mini",
        description="Vision model: 'openai:gpt-4o-mini' or 'anthropic:claude-3-5-sonnet-latest'",
    )

    agent_model: str = Field(
        default="anthropic:claude-3-5-sonnet-latest",
        description="Agent model: 'openai:gpt-4o' or 'anthropic:claude-3-5-sonnet-latest'",
    )

    # Storage
    data_path: Path = Field(
        default=Path("./data"),
        description="Path to data storage directory",
    )

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )

    # USDA Nutrition
    usda_api_key: str = Field(
        default="DEMO_KEY",
        description="USDA FoodData Central API key",
    )

    enable_nutrition_verification: bool = Field(
        default=True,
        description="Enable nutrition verification with USDA API",
    )

    # API Settings
    run_mode: Literal["bot", "api", "both"] = Field(
        default="bot",
        description="Run mode: 'bot' (Telegram only), 'api' (REST API only), or 'both'",
    )

    api_host: str = Field(
        default="0.0.0.0",
        description="API server host",
    )

    api_port: int = Field(
        default=8080,
        ge=1,
        le=65535,
        description="API server port (1-65535)",
    )

    api_keys: list[str] = Field(
        default_factory=list,
        description="Comma-separated list of valid API keys",
    )

    cors_origins: list[str] = Field(
        default_factory=list,
        description="Comma-separated list of allowed CORS origins",
    )

    # Rate Limiting
    rate_limit_storage_url: str = Field(
        default="memory://",
        description="Rate limit storage URL: 'memory://' for development, 'redis://localhost:6379' for production",
    )

    # Field Validators

    @field_validator("allowed_telegram_ids", mode="before")
    @classmethod
    def parse_telegram_ids(cls, v: str | list[str]) -> list[str]:
        """Parse comma-separated Telegram IDs"""
        if isinstance(v, str):
            return [id.strip() for id in v.split(",") if id.strip()]
        return v

    @field_validator("api_keys", mode="before")
    @classmethod
    def parse_api_keys(cls, v: str | list[str]) -> list[str]:
        """Parse comma-separated API keys"""
        if isinstance(v, str):
            if not v:  # Empty string
                return []
            return [key.strip() for key in v.split(",") if key.strip()]
        return v if v else []

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse comma-separated CORS origins"""
        if isinstance(v, str):
            if not v:  # Empty string
                return []
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v if v else []

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate PostgreSQL URL format"""
        if not v.startswith(("postgresql://", "postgres://")):
            raise ValueError(
                f"DATABASE_URL must start with 'postgresql://' or 'postgres://'. "
                f"Got: {v[:20] if len(v) > 20 else v}...\n"
                f"Example: postgresql://user:password@localhost:5432/database"
            )

        # Basic structure check
        if "@" not in v or "/" not in v.split("@")[-1]:
            raise ValueError(
                "DATABASE_URL format invalid. "
                "Expected: postgresql://user:password@host:port/database"
            )

        return v

    @field_validator("allowed_telegram_ids")
    @classmethod
    def validate_telegram_ids(cls, v: list[str]) -> list[str]:
        """Validate Telegram IDs are non-empty and numeric"""
        if not v or v == [""]:
            raise ValueError(
                "ALLOWED_TELEGRAM_IDS cannot be empty. "
                "Get your Telegram ID from @userinfobot on Telegram."
            )

        # Validate each ID is numeric
        for tid in v:
            if not tid.strip().isdigit():
                raise ValueError(
                    f"Invalid Telegram ID '{tid}'. "
                    "Telegram IDs must be numeric (e.g., 123456789). "
                    "Get your ID from @userinfobot on Telegram."
                )

        return v

    @field_validator("data_path", mode="before")
    @classmethod
    def validate_data_path(cls, v: Path | str) -> Path:
        """Ensure data path is a Path object"""
        if isinstance(v, str):
            return Path(v)
        return v

    @model_validator(mode="after")
    def validate_api_keys_for_models(self) -> "Settings":
        """Validate that required API keys are present for selected models"""
        errors = []

        # Check vision model
        if self.vision_model.startswith("openai:") and not self.openai_api_key:
            errors.append(
                f"❌ VISION_MODEL is set to '{self.vision_model}' but OPENAI_API_KEY is not set.\n"
                "   Get your API key at: https://platform.openai.com/api-keys"
            )

        if self.vision_model.startswith("anthropic:") and not self.anthropic_api_key:
            errors.append(
                f"❌ VISION_MODEL is set to '{self.vision_model}' but ANTHROPIC_API_KEY is not set.\n"
                "   Get your API key at: https://console.anthropic.com/"
            )

        # Check agent model
        if self.agent_model.startswith("openai:") and not self.openai_api_key:
            errors.append(
                f"❌ AGENT_MODEL is set to '{self.agent_model}' but OPENAI_API_KEY is not set.\n"
                "   Get your API key at: https://platform.openai.com/api-keys"
            )

        if self.agent_model.startswith("anthropic:") and not self.anthropic_api_key:
            errors.append(
                f"❌ AGENT_MODEL is set to '{self.agent_model}' but ANTHROPIC_API_KEY is not set.\n"
                "   Get your API key at: https://console.anthropic.com/"
            )

        if errors:
            raise ValueError("\n\n".join(errors))

        return self


# Global settings instance
# This will validate configuration on import and fail fast if invalid
try:
    settings = Settings()
except Exception as e:
    print(f"\n{'=' * 80}", file=sys.stderr)
    print("❌ CONFIGURATION ERROR", file=sys.stderr)
    print(f"{'=' * 80}\n", file=sys.stderr)
    print(str(e), file=sys.stderr)
    print(f"\n{'=' * 80}", file=sys.stderr)
    print("💡 Check your .env file and ensure all required fields are set.", file=sys.stderr)
    print("   See .env.example for reference.", file=sys.stderr)
    print(f"{'=' * 80}\n", file=sys.stderr)
    sys.exit(1)


# Backward compatibility: Export old variable names
# This allows existing code to work without changes
TELEGRAM_BOT_TOKEN = settings.telegram_bot_token
ALLOWED_TELEGRAM_IDS = settings.allowed_telegram_ids
TELEGRAM_TOPIC_FILTER = settings.telegram_topic_filter
DATABASE_URL = settings.database_url
OPENAI_API_KEY = settings.openai_api_key
ANTHROPIC_API_KEY = settings.anthropic_api_key
VISION_MODEL = settings.vision_model
AGENT_MODEL = settings.agent_model
DATA_PATH = settings.data_path
LOG_LEVEL = settings.log_level
USDA_API_KEY = settings.usda_api_key
ENABLE_NUTRITION_VERIFICATION = settings.enable_nutrition_verification
RATE_LIMIT_STORAGE_URL = settings.rate_limit_storage_url


def validate_config() -> None:
    """
    Validate configuration (deprecated - validation happens automatically on import).

    This function is kept for backward compatibility but no longer does anything.
    Configuration validation now happens automatically when Settings is instantiated.
    """
    # Validation happens automatically on Settings instantiation
    pass
