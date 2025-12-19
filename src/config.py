"""Configuration management"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_TELEGRAM_IDS: list[str] = os.getenv("ALLOWED_TELEGRAM_IDS", "").split(",")

# Topic filtering for shared groups with multiple bots
# - 'all' (default): Respond to all topics and DMs
# - 'none': Only respond to DMs, ignore all topics
# - '123,456,789': Whitelist - only respond to listed topics (and DMs)
# - '!123,456': Blacklist - respond to all topics EXCEPT these (and DMs)
TELEGRAM_TOPIC_FILTER: str = os.getenv("TELEGRAM_TOPIC_FILTER", "all")

# Database
DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/health_agent")

# AI Models
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
VISION_MODEL: str = os.getenv("VISION_MODEL", "openai:gpt-4o-mini")
AGENT_MODEL: str = os.getenv("AGENT_MODEL", "anthropic:claude-3-5-sonnet-latest")

# Storage
DATA_PATH: Path = Path(os.getenv("DATA_PATH", "./data"))

# Logging
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# USDA Nutrition Database
USDA_API_KEY: str = os.getenv("USDA_API_KEY", "DEMO_KEY")
ENABLE_NUTRITION_VERIFICATION: bool = os.getenv("ENABLE_NUTRITION_VERIFICATION", "true").lower() == "true"

# Validation
def validate_config() -> None:
    """Validate required configuration"""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is required")
    if not ALLOWED_TELEGRAM_IDS or ALLOWED_TELEGRAM_IDS == [""]:
        raise ValueError("ALLOWED_TELEGRAM_IDS is required")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is required")
    # API keys are optional for MVP (using mock vision AI)
