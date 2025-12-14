"""Telegram authentication utilities"""
from src.config import ALLOWED_TELEGRAM_IDS


def is_authorized(telegram_id: str) -> bool:
    """Check if telegram user is authorized"""
    return telegram_id in ALLOWED_TELEGRAM_IDS or "" in ALLOWED_TELEGRAM_IDS
