"""
Prometheus metrics definitions for health-agent application.

This module defines all metrics collected by the application, organized by category:
- HTTP/API metrics: Request counts, latency, errors
- Telegram bot metrics: Message processing, response times
- AI/Agent metrics: Token usage, response generation time
- Database metrics: Query performance, connection pool
- User activity metrics: Active users, engagement
- Food tracking metrics: Photo analysis, nutrition lookups
- External API metrics: Third-party service calls

Metrics are exposed at the /metrics endpoint for Prometheus scraping.
"""

import logging
from prometheus_client import Counter, Gauge, Histogram, Info

logger = logging.getLogger(__name__)

# =============================================================================
# HTTP/API Metrics
# =============================================================================

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests received",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method", "endpoint"],
)

# =============================================================================
# Telegram Bot Metrics
# =============================================================================

telegram_messages_total = Counter(
    "telegram_messages_total",
    "Total Telegram messages processed",
    ["message_type", "status"],  # message_type: text/photo/voice, status: success/error
)

telegram_message_duration_seconds = Histogram(
    "telegram_message_duration_seconds",
    "Telegram message processing time in seconds",
    ["message_type"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

telegram_commands_total = Counter(
    "telegram_commands_total",
    "Total Telegram commands executed",
    ["command"],  # command: /start, /help, /settings, etc.
)

telegram_user_sessions_active = Gauge(
    "telegram_user_sessions_active",
    "Number of active Telegram user sessions",
)

# =============================================================================
# Error Metrics
# =============================================================================

errors_total = Counter(
    "errors_total",
    "Total errors by type and component",
    ["error_type", "component"],  # component: bot/api/database/agent
)

exceptions_unhandled_total = Counter(
    "exceptions_unhandled_total",
    "Total unhandled exceptions",
    ["exception_type"],
)

# =============================================================================
# User Activity Metrics
# =============================================================================

active_users = Gauge(
    "active_users_total",
    "Number of active users by time period",
    ["time_period"],  # time_period: last_hour/last_day/last_week
)

user_registrations_total = Counter(
    "user_registrations_total",
    "Total user registrations",
)

user_interactions_total = Counter(
    "user_interactions_total",
    "Total user interactions",
    ["interaction_type"],  # food_entry/sleep_quiz/reminder/etc.
)

# =============================================================================
# Food Tracking Metrics
# =============================================================================

food_photos_analyzed_total = Counter(
    "food_photos_analyzed_total",
    "Total food photos analyzed",
    ["confidence_level"],  # high/medium/low based on AI confidence score
)

food_photo_processing_duration_seconds = Histogram(
    "food_photo_processing_duration_seconds",
    "Food photo analysis time in seconds",
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 15.0, 30.0],
)

food_entries_created_total = Counter(
    "food_entries_created_total",
    "Total food entries created",
    ["entry_type"],  # photo/manual/voice
)

nutrition_lookups_total = Counter(
    "nutrition_lookups_total",
    "Total nutrition database lookups",
    ["source", "status"],  # source: usda/cache, status: success/error
)

# =============================================================================
# AI/Agent Metrics
# =============================================================================

agent_response_duration_seconds = Histogram(
    "agent_response_duration_seconds",
    "AI agent response generation time in seconds",
    ["model", "complexity"],  # model: haiku/sonnet/gpt-4o, complexity: simple/complex
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0],
)

agent_token_usage_total = Counter(
    "agent_token_usage_total",
    "Total AI tokens consumed",
    ["provider", "model", "token_type"],  # provider: openai/anthropic, token_type: input/output
)

agent_requests_total = Counter(
    "agent_requests_total",
    "Total AI agent requests",
    ["model", "status"],  # status: success/error/timeout
)

agent_tool_calls_total = Counter(
    "agent_tool_calls_total",
    "Total agent tool calls",
    ["tool_name", "status"],
)

# =============================================================================
# Database Metrics
# =============================================================================

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query execution time in seconds",
    ["query_type"],  # query_type: select/insert/update/delete
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)

db_connections_active = Gauge(
    "db_connections_active",
    "Number of active database connections",
)

db_pool_size = Gauge(
    "db_pool_size",
    "Database connection pool size by state",
    ["state"],  # state: available/in_use/total
)

db_queries_total = Counter(
    "db_queries_total",
    "Total database queries executed",
    ["query_type", "status"],  # status: success/error
)

db_transactions_total = Counter(
    "db_transactions_total",
    "Total database transactions",
    ["status"],  # status: committed/rolled_back
)

db_pool_exhausted_total = Counter(
    "db_pool_exhausted_total",
    "Total times connection pool was exhausted",
)

# =============================================================================
# External API Metrics
# =============================================================================

external_api_calls_total = Counter(
    "external_api_calls_total",
    "Total external API calls",
    ["service", "status"],  # service: openai/anthropic/usda, status: success/error/timeout
)

external_api_duration_seconds = Histogram(
    "external_api_duration_seconds",
    "External API call duration in seconds",
    ["service"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

external_api_rate_limit_hits_total = Counter(
    "external_api_rate_limit_hits_total",
    "Total rate limit hits by service",
    ["service"],
)

# =============================================================================
# Memory/Semantic Search Metrics
# =============================================================================

memory_searches_total = Counter(
    "memory_searches_total",
    "Total semantic memory searches",
    ["search_type", "status"],  # search_type: conversation/user_facts
)

memory_search_duration_seconds = Histogram(
    "memory_search_duration_seconds",
    "Memory search duration in seconds",
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0],
)

memory_entries_total = Gauge(
    "memory_entries_total",
    "Total entries in semantic memory",
    ["memory_type"],  # conversation/user_facts/preferences
)

# =============================================================================
# Gamification Metrics
# =============================================================================

gamification_xp_awarded_total = Counter(
    "gamification_xp_awarded_total",
    "Total XP awarded",
    ["activity_type"],
)

gamification_achievements_unlocked_total = Counter(
    "gamification_achievements_unlocked_total",
    "Total achievements unlocked",
    ["achievement_type"],
)

gamification_streaks_active = Gauge(
    "gamification_streaks_active",
    "Number of active streaks",
    ["streak_type"],
)

# =============================================================================
# Application Info
# =============================================================================

app_info = Info(
    "app_info",
    "Application information",
)


def init_metrics():
    """
    Initialize metrics with application information.

    This should be called once at application startup to set
    static metadata about the application.
    """
    import os
    from src.config import SENTRY_ENVIRONMENT

    app_info.info(
        {
            "version": os.getenv("GIT_COMMIT_SHA", "dev")[:7],
            "environment": SENTRY_ENVIRONMENT,
            "python_version": f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}",
        }
    )

    logger.info("Prometheus metrics initialized")


# =============================================================================
# Helper Functions
# =============================================================================


def get_confidence_level(confidence_score: float) -> str:
    """
    Convert a confidence score (0.0-1.0) to a categorical level.

    Args:
        confidence_score: Confidence score from 0.0 to 1.0

    Returns:
        Confidence level: 'high', 'medium', or 'low'
    """
    if confidence_score >= 0.8:
        return "high"
    elif confidence_score >= 0.5:
        return "medium"
    else:
        return "low"


def get_complexity_level(estimated_tokens: int) -> str:
    """
    Estimate complexity based on token count.

    Args:
        estimated_tokens: Estimated number of tokens in the request

    Returns:
        Complexity level: 'simple' or 'complex'
    """
    return "complex" if estimated_tokens > 500 else "simple"
