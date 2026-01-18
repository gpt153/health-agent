"""User context and breadcrumb utilities for Sentry."""

import logging
from typing import Any, Dict, Optional

import sentry_sdk
from sentry_sdk import set_user, set_tag, add_breadcrumb as sentry_add_breadcrumb

logger = logging.getLogger(__name__)


def set_user_context(
    user_id: str,
    username: Optional[str] = None,
    email: Optional[str] = None,
    **kwargs
) -> None:
    """
    Set user context for Sentry error tracking.

    This attaches user information to all subsequent Sentry events,
    making it easy to identify which user experienced an error.

    Args:
        user_id: Unique user identifier (e.g., Telegram user ID)
        username: Username or display name (optional)
        email: User email address (optional)
        **kwargs: Additional user attributes to track

    Example:
        >>> set_user_context("123456789", username="john_doe")
    """
    user_data = {
        "id": user_id,
    }

    if username:
        user_data["username"] = username

    if email:
        user_data["email"] = email

    # Add any additional user attributes
    user_data.update(kwargs)

    set_user(user_data)
    logger.debug(f"Set Sentry user context: user_id={user_id}")


def clear_user_context() -> None:
    """
    Clear user context from Sentry.

    Useful when processing requests that aren't associated with a specific user,
    or when switching between users in the same process.
    """
    set_user(None)
    logger.debug("Cleared Sentry user context")


def set_context_tag(key: str, value: str) -> None:
    """
    Set a tag on the current Sentry scope.

    Tags are key-value pairs that can be used to filter and search
    events in Sentry. They're useful for categorizing errors.

    Args:
        key: Tag name (e.g., "message_type", "api_version")
        value: Tag value (e.g., "photo", "v2")

    Example:
        >>> set_context_tag("message_type", "photo")
        >>> set_context_tag("handler", "food_photo")
    """
    set_tag(key, value)


def add_breadcrumb(
    category: str,
    message: str,
    level: str = "info",
    data: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Add a breadcrumb to Sentry's event trail.

    Breadcrumbs are a trail of events that led up to an error.
    They help understand the context when debugging issues.

    Args:
        category: Breadcrumb category (e.g., "telegram", "database", "api")
        message: Human-readable description of the event
        level: Severity level (debug, info, warning, error)
        data: Additional structured data about the event

    Example:
        >>> add_breadcrumb(
        ...     "telegram",
        ...     "User sent photo message",
        ...     data={"photo_size": 1024000, "file_id": "abc123"}
        ... )
    """
    sentry_add_breadcrumb(
        category=category,
        message=message,
        level=level,
        data=data or {},
    )


def capture_exception_with_context(
    exception: Exception,
    context: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """
    Manually capture an exception with additional context.

    Use this when you want to report an exception to Sentry
    but still handle it gracefully in your code.

    Args:
        exception: The exception to capture
        context: Additional context data to attach
        tags: Tags to attach to this specific event

    Returns:
        Event ID from Sentry, or None if not sent

    Example:
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     event_id = capture_exception_with_context(
        ...         e,
        ...         context={"operation": "photo_analysis"},
        ...         tags={"component": "vision"}
        ...     )
        ...     logger.error(f"Operation failed, Sentry event: {event_id}")
    """
    with sentry_sdk.push_scope() as scope:
        # Add context data
        if context:
            for key, value in context.items():
                scope.set_context(key, value)

        # Add tags
        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)

        # Capture the exception
        event_id = sentry_sdk.capture_exception(exception)
        return event_id


def capture_message(
    message: str,
    level: str = "info",
    tags: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """
    Capture a message (not an exception) in Sentry.

    Useful for tracking important events that aren't errors,
    like unusual user behavior or system state changes.

    Args:
        message: The message to capture
        level: Severity level (debug, info, warning, error, fatal)
        tags: Tags to attach to this event

    Returns:
        Event ID from Sentry, or None if not sent

    Example:
        >>> capture_message(
        ...     "User completed onboarding",
        ...     level="info",
        ...     tags={"onboarding_path": "nutrition"}
        ... )
    """
    with sentry_sdk.push_scope() as scope:
        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)

        event_id = sentry_sdk.capture_message(message, level=level)
        return event_id
