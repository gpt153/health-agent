# Implementation Plan: Pydantic Settings for Configuration Validation

**Issue:** #74
**Epic:** 007 - Phase 2 High-Priority Refactoring
**Priority:** MEDIUM
**Estimated Time:** 2 hours
**Status:** Planning

## Overview

Replace the current `src/config.py` module with Pydantic's `BaseSettings` to provide comprehensive configuration validation, fail-fast behavior, and clear error messages for invalid configuration.

## Current State Analysis

### Existing Configuration Structure

The current `src/config.py` uses simple `os.getenv()` calls with basic string defaults:

**Configuration Variables:**
1. **Telegram Settings**
   - `TELEGRAM_BOT_TOKEN` (str) - Required
   - `ALLOWED_TELEGRAM_IDS` (list[str]) - Required, comma-separated
   - `TELEGRAM_TOPIC_FILTER` (str) - Default: "all"

2. **Database**
   - `DATABASE_URL` (str) - Required, PostgreSQL connection string

3. **AI Models**
   - `OPENAI_API_KEY` (str) - Optional
   - `ANTHROPIC_API_KEY` (str) - Optional
   - `VISION_MODEL` (str) - Default: "openai:gpt-4o-mini"
   - `AGENT_MODEL` (str) - Default: "anthropic:claude-3-5-sonnet-latest"

4. **Storage**
   - `DATA_PATH` (Path) - Default: "./data"

5. **Logging**
   - `LOG_LEVEL` (str) - Default: "INFO"

6. **USDA Nutrition**
   - `USDA_API_KEY` (str) - Default: "DEMO_KEY"
   - `ENABLE_NUTRITION_VERIFICATION` (bool) - Default: true

7. **API Settings** (from .env.example)
   - `RUN_MODE` (str) - Default: "bot"
   - `API_HOST` (str) - Default: "0.0.0.0"
   - `API_PORT` (int) - Default: 8080
   - `API_KEYS` (list[str]) - Comma-separated
   - `CORS_ORIGINS` (list[str]) - Comma-separated

### Current Validation

Minimal validation exists in `validate_config()`:
- Checks if `TELEGRAM_BOT_TOKEN` is non-empty
- Checks if `ALLOWED_TELEGRAM_IDS` is non-empty
- Checks if `DATABASE_URL` is non-empty
- No format validation, range checking, or detailed error messages

### Usage Patterns

Config is imported across 17 files:
- Direct imports: `from src.config import TELEGRAM_BOT_TOKEN, LOG_LEVEL`
- Used in: bot.py, main.py, db/connection.py, api/server.py, agent/, utils/, memory/

## Requirements

### 1. Configuration Validation

**Database URL Format:**
- Must be a valid PostgreSQL URL
- Format: `postgresql://[user[:password]@][host][:port][/dbname]`
- Validate scheme is `postgresql` or `postgres`

**API Keys Non-Empty:**
- When a model requires an API key, ensure it's set
- `VISION_MODEL` starting with "openai:" requires `OPENAI_API_KEY`
- `VISION_MODEL` starting with "anthropic:" requires `ANTHROPIC_API_KEY`
- `AGENT_MODEL` starting with "openai:" requires `OPENAI_API_KEY`
- `AGENT_MODEL` starting with "anthropic:" requires `ANTHROPIC_API_KEY`

**Port Ranges:**
- `API_PORT` must be between 1 and 65535

**Valid Log Levels:**
- Must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL

**Run Mode:**
- Must be one of: "bot", "api", "both"

### 2. Field Validators

**Vision API Key:**
- If `VISION_MODEL` starts with provider prefix, corresponding API key must exist
- Validate at startup, not runtime

**PostgreSQL Connection:**
- Validate URL format (not actual connection - that's runtime)
- Ensure all required parts are present

**Telegram Token Format:**
- Basic format validation: `[0-9]+:[A-Za-z0-9_-]+`
- Must contain colon separator

**Cache TTL:**
- If cache settings exist, TTL must be >= 60 seconds
- (Note: No cache settings in current config, prepare for future)

### 3. Fail Fast

**Invalid Config = Startup Failure:**
- Application should not start with invalid configuration
- Pydantic will raise `ValidationError` on instantiation

**Clear Error Messages:**
- Use Pydantic's field descriptions
- Add custom error messages for validators
- Show which field failed and why

**Suggest Valid Values:**
- Include examples in error messages
- Show valid ranges for numeric fields
- List valid options for enum-like fields

## Implementation Plan

### Step 1: Add Pydantic Settings Dependency

**File:** `requirements.txt`

**Action:** Already has `pydantic>=2.0.0` and `pydantic-ai>=0.0.14`, but ensure we have `pydantic-settings`:

```python
pydantic>=2.0.0
pydantic-settings>=2.0.0
```

**Verification:** Check if already included in pydantic-ai dependencies, otherwise add explicitly.

### Step 2: Create New Settings Module

**File:** `src/config.py` (replace existing)

**Structure:**
```python
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Literal

class Settings(BaseSettings):
    """Application configuration with validation"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore unknown env vars
    )

    # Telegram Settings
    telegram_bot_token: str = Field(
        ...,  # Required
        description="Telegram bot token from @BotFather",
        pattern=r"^\d+:[A-Za-z0-9_-]+$"
    )

    allowed_telegram_ids: list[str] = Field(
        ...,  # Required
        description="Comma-separated list of allowed Telegram user IDs"
    )

    telegram_topic_filter: str = Field(
        default="all",
        description="Topic filter: 'all', 'none', whitelist (123,456), or blacklist (!123,456)"
    )

    # Database
    database_url: str = Field(
        ...,  # Required
        description="PostgreSQL connection URL"
    )

    # AI Models
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key (required if using OpenAI models)"
    )

    anthropic_api_key: str = Field(
        default="",
        description="Anthropic API key (required if using Anthropic models)"
    )

    vision_model: str = Field(
        default="openai:gpt-4o-mini",
        description="Vision model: 'openai:gpt-4o-mini' or 'anthropic:claude-3-5-sonnet-latest'"
    )

    agent_model: str = Field(
        default="anthropic:claude-3-5-sonnet-latest",
        description="Agent model: 'openai:gpt-4o' or 'anthropic:claude-3-5-sonnet-latest'"
    )

    # Storage
    data_path: Path = Field(
        default=Path("./data"),
        description="Path to data storage directory"
    )

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )

    # USDA Nutrition
    usda_api_key: str = Field(
        default="DEMO_KEY",
        description="USDA FoodData Central API key"
    )

    enable_nutrition_verification: bool = Field(
        default=True,
        description="Enable nutrition verification with USDA API"
    )

    # API Settings
    run_mode: Literal["bot", "api", "both"] = Field(
        default="bot",
        description="Run mode: 'bot' (Telegram only), 'api' (REST API only), or 'both'"
    )

    api_host: str = Field(
        default="0.0.0.0",
        description="API server host"
    )

    api_port: int = Field(
        default=8080,
        ge=1,
        le=65535,
        description="API server port (1-65535)"
    )

    api_keys: list[str] = Field(
        default_factory=list,
        description="Comma-separated list of valid API keys"
    )

    cors_origins: list[str] = Field(
        default_factory=list,
        description="Comma-separated list of allowed CORS origins"
    )

    # Field Validators

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate PostgreSQL URL format"""
        if not v.startswith(("postgresql://", "postgres://")):
            raise ValueError(
                f"DATABASE_URL must start with 'postgresql://' or 'postgres://'. "
                f"Got: {v[:20]}..."
            )

        # Basic structure check
        if "@" in v and "/" in v.split("@")[-1]:
            return v
        else:
            raise ValueError(
                "DATABASE_URL format invalid. "
                "Expected: postgresql://user:password@host:port/database"
            )

    @field_validator("allowed_telegram_ids")
    @classmethod
    def validate_telegram_ids(cls, v: list[str]) -> list[str]:
        """Validate Telegram IDs are non-empty"""
        if not v or v == [""]:
            raise ValueError(
                "ALLOWED_TELEGRAM_IDS cannot be empty. "
                "Get your Telegram ID from @userinfobot"
            )

        # Validate each ID is numeric
        for tid in v:
            if not tid.strip().isdigit():
                raise ValueError(
                    f"Invalid Telegram ID '{tid}'. "
                    "Telegram IDs must be numeric (e.g., 123456789)"
                )

        return v

    @model_validator(mode="after")
    def validate_api_keys_for_models(self) -> "Settings":
        """Validate that required API keys are present for selected models"""
        errors = []

        # Check vision model
        if self.vision_model.startswith("openai:") and not self.openai_api_key:
            errors.append(
                f"VISION_MODEL is set to '{self.vision_model}' but OPENAI_API_KEY is not set. "
                "Get your API key at https://platform.openai.com/api-keys"
            )

        if self.vision_model.startswith("anthropic:") and not self.anthropic_api_key:
            errors.append(
                f"VISION_MODEL is set to '{self.vision_model}' but ANTHROPIC_API_KEY is not set. "
                "Get your API key at https://console.anthropic.com/"
            )

        # Check agent model
        if self.agent_model.startswith("openai:") and not self.openai_api_key:
            errors.append(
                f"AGENT_MODEL is set to '{self.agent_model}' but OPENAI_API_KEY is not set. "
                "Get your API key at https://platform.openai.com/api-keys"
            )

        if self.agent_model.startswith("anthropic:") and not self.anthropic_api_key:
            errors.append(
                f"AGENT_MODEL is set to '{self.agent_model}' but ANTHROPIC_API_KEY is not set. "
                "Get your API key at https://console.anthropic.com/"
            )

        if errors:
            raise ValueError("\n".join(errors))

        return self

    @field_validator("data_path")
    @classmethod
    def validate_data_path(cls, v: Path) -> Path:
        """Ensure data path is a Path object"""
        if isinstance(v, str):
            return Path(v)
        return v


# Global settings instance
# This will validate configuration on import and fail fast if invalid
try:
    settings = Settings()
except Exception as e:
    import sys
    print(f"\n❌ Configuration Error:\n{e}\n", file=sys.stderr)
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


def validate_config() -> None:
    """Validate configuration (deprecated - validation happens on import)"""
    # Keep for backward compatibility but no longer needed
    # Settings validation happens automatically on instantiation
    pass
```

### Step 3: Handle Comma-Separated Lists

Pydantic doesn't automatically split comma-separated strings into lists. We need custom parsing:

**Add to Settings class:**

```python
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
```

### Step 4: Update Environment Variable Names

Pydantic Settings uses lowercase with underscores by default, but we can keep uppercase names:

**Option A:** Keep uppercase in .env (recommended for backward compatibility)
- Set `case_sensitive=False` in `SettingsConfigDict`
- Pydantic will match `TELEGRAM_BOT_TOKEN` to `telegram_bot_token`

**Option B:** Change field names to uppercase
- Use `alias` parameter: `Field(alias="TELEGRAM_BOT_TOKEN")`

**Decision:** Use Option A (case_sensitive=False) for minimal migration.

### Step 5: Test Configuration Validation

**File:** `tests/test_config.py` (new)

**Test Cases:**
1. Valid configuration loads successfully
2. Missing required field raises ValidationError
3. Invalid DATABASE_URL format raises error
4. Invalid port range raises error
5. Invalid log level raises error
6. Model without API key raises error
7. Invalid Telegram token format raises error
8. Non-numeric Telegram ID raises error
9. Empty ALLOWED_TELEGRAM_IDS raises error
10. Comma-separated lists parse correctly

### Step 6: Update Documentation

**Files to update:**
1. `README.md` - Update "Environment Variables" section
2. `.env.example` - Add comments about validation
3. `DEVELOPMENT.md` - Document new validation behavior

**Add section explaining:**
- Configuration validation happens at startup
- Invalid config = immediate failure with clear error message
- How to interpret validation errors
- Common configuration mistakes and fixes

## Migration Strategy

### Phase 1: Backward Compatible Implementation

1. Keep old variable names exported
2. Existing imports continue to work
3. Add validation but maintain same interface

### Phase 2: Test and Validate

1. Run existing tests with new config
2. Test startup with invalid configurations
3. Verify error messages are clear
4. Test all config-dependent features

### Phase 3: Optional Refactoring (Future)

If desired, existing code can migrate to using `settings` object directly:

```python
# Old way (still works)
from src.config import TELEGRAM_BOT_TOKEN, LOG_LEVEL

# New way (optional migration)
from src.config import settings

telegram_token = settings.telegram_bot_token
log_level = settings.log_level
```

## Validation Rules Summary

| Field | Validation | Error Message |
|-------|-----------|---------------|
| `telegram_bot_token` | Pattern: `\d+:[A-Za-z0-9_-]+` | "Invalid Telegram bot token format. Expected: 123456:ABC-xyz..." |
| `allowed_telegram_ids` | Non-empty, numeric | "ALLOWED_TELEGRAM_IDS cannot be empty. Get your ID from @userinfobot" |
| `database_url` | Starts with `postgresql://` | "DATABASE_URL must be a valid PostgreSQL connection string" |
| `api_port` | 1 <= port <= 65535 | "API_PORT must be between 1 and 65535" |
| `log_level` | In ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | "LOG_LEVEL must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL" |
| `run_mode` | In ["bot", "api", "both"] | "RUN_MODE must be 'bot', 'api', or 'both'" |
| `vision_model` + API keys | If openai: require OPENAI_API_KEY | "VISION_MODEL requires OPENAI_API_KEY to be set" |
| `agent_model` + API keys | If anthropic: require ANTHROPIC_API_KEY | "AGENT_MODEL requires ANTHROPIC_API_KEY to be set" |

## Error Message Examples

### Missing Required Field
```
❌ Configuration Error:
1 validation error for Settings
telegram_bot_token
  Field required [type=missing, input_value={'database_url': 'postg...}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.10/v/missing

Hint: Set TELEGRAM_BOT_TOKEN in your .env file or environment variables.
Get your bot token from @BotFather on Telegram.
```

### Invalid Database URL
```
❌ Configuration Error:
1 validation error for Settings
database_url
  Value error, DATABASE_URL must start with 'postgresql://' or 'postgres://'. Got: mysql://localhost/db [type=value_error, input_value='mysql://localhost/db', input_type=str]
```

### Invalid Port Range
```
❌ Configuration Error:
1 validation error for Settings
api_port
  Input should be less than or equal to 65535 [type=less_than_equal, input_value=99999, input_type=int]

Valid range: 1-65535
```

### Missing API Key for Model
```
❌ Configuration Error:
1 validation error for Settings
  Value error, VISION_MODEL is set to 'openai:gpt-4o-mini' but OPENAI_API_KEY is not set. Get your API key at https://platform.openai.com/api-keys [type=value_error, input_value={'telegram_bot_token': '...}, input_type=dict]
```

## Implementation Checklist

- [ ] Step 1: Verify pydantic-settings dependency
- [ ] Step 2: Implement new Settings class in src/config.py
  - [ ] Add all configuration fields
  - [ ] Add field validators for each requirement
  - [ ] Add model validator for API key consistency
  - [ ] Add comma-separated list parsing
  - [ ] Export backward-compatible variable names
- [ ] Step 3: Test configuration validation
  - [ ] Create test file with comprehensive test cases
  - [ ] Test valid configuration
  - [ ] Test each validation rule
  - [ ] Test error messages
- [ ] Step 4: Update documentation
  - [ ] Update README.md environment variables section
  - [ ] Add validation notes to .env.example
  - [ ] Document error interpretation in DEVELOPMENT.md
- [ ] Step 5: Integration testing
  - [ ] Test bot startup with valid config
  - [ ] Test bot startup with invalid config (should fail fast)
  - [ ] Test API startup with valid config
  - [ ] Verify all existing features work
- [ ] Step 6: Final review
  - [ ] Review all error messages for clarity
  - [ ] Ensure all requirements are met
  - [ ] Confirm backward compatibility

## Success Criteria

✅ **All validation requirements implemented:**
- Database URL format validation
- API keys validated against model selection
- Port range validation (1-65535)
- Valid log levels enforced
- Telegram token format validation

✅ **Fail fast behavior:**
- Application exits immediately with invalid config
- Clear error messages displayed
- Suggested valid values included

✅ **Backward compatibility:**
- All existing imports continue to work
- No changes required to existing code
- Old validate_config() function still exists (no-op)

✅ **Clear error messages:**
- Each validation error includes context
- Suggests how to fix the issue
- Provides examples or valid ranges

✅ **Tests passing:**
- All configuration validation tests pass
- Existing integration tests pass with new config
- Invalid configurations correctly rejected

## Notes

- This is a **non-breaking change** due to backward compatibility layer
- Consider removing old variable exports in a future major version
- Future enhancement: Add runtime connection testing (separate from config validation)
- Consider adding `--validate-config` CLI flag to test configuration without starting services

## Time Breakdown

- **Step 1-2:** Implement Settings class - 45 minutes
- **Step 3:** Write comprehensive tests - 30 minutes
- **Step 4:** Update documentation - 20 minutes
- **Step 5:** Integration testing - 20 minutes
- **Step 6:** Final review and polish - 5 minutes

**Total:** ~2 hours
