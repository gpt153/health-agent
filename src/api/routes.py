"""API routes for health agent"""
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from src.api.models import (
    ChatRequest, ChatResponse,
    UserProfileRequest, UserProfileResponse,
    ProfileUpdateRequest, PreferencesUpdateRequest,
    FoodLogRequest, FoodSummaryResponse,
    ReminderRequest, ReminderResponse, ReminderListResponse,
    ReminderStatusResponse,
    XPResponse, StreakResponse, AchievementResponse,
    HealthCheckResponse, ErrorResponse
)
from src.api.auth import verify_api_key
from src.api.middleware import limiter
from src.agent import get_agent_response
from src.memory.db_manager import db_memory_manager as memory_manager
from src.db.queries import (
    user_exists, create_user,
    get_conversation_history, clear_conversation_history,
    save_conversation_message,
    get_food_entries_by_date,
    get_active_reminders, create_reminder, get_reminder_by_id,
    get_user_xp_level, get_user_streaks, get_user_achievements
)
from src.db.connection import db
from src.models.reminder import Reminder, ReminderSchedule

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/v1/chat", response_model=ChatResponse)
@limiter.limit("10/minute")
async def chat(
    fastapi_request: Request,
    request: ChatRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Chat endpoint - sends a message to the agent and gets a response

    This endpoint reuses the same agent core that the Telegram bot uses.
    Rate limit: 10 requests per minute (AI calls are expensive)
    """
    try:
        user_id = request.user_id

        # Ensure user exists
        if not await user_exists(user_id):
            await create_user(user_id)
            await memory_manager.create_user_files(user_id)
            logger.info(f"Created new user via API: {user_id}")

        # Get conversation history if not provided
        message_history = request.message_history
        if not message_history:
            message_history = await get_conversation_history(user_id, limit=20)

        # Get agent response (same function Telegram bot uses)
        response = await get_agent_response(
            telegram_id=user_id,
            user_message=request.message,
            memory_manager=memory_manager,
            reminder_manager=None,  # API doesn't support reminder manager yet
            message_history=message_history,
            bot_application=None
        )

        # Save conversation
        await save_conversation_message(user_id, "user", request.message, message_type="text")
        await save_conversation_message(user_id, "assistant", response, message_type="text")

        return ChatResponse(
            response=response,
            timestamp=datetime.now(),
            user_id=user_id
        )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/api/v1/users", status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_user_endpoint(
    fastapi_request: Request,
    request: UserProfileRequest,
    api_key: str = Depends(verify_api_key)
):
    """Create a new user (Rate limit: 20/minute)"""
    try:
        user_id = request.user_id

        if await user_exists(user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User {user_id} already exists"
            )

        await create_user(user_id)
        await memory_manager.create_user_files(user_id)

        # Update profile if provided
        if request.profile:
            for field, value in request.profile.items():
                await memory_manager.update_profile(user_id, field, str(value))

        logger.info(f"Created user via API: {user_id}")

        return {"user_id": user_id, "created": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/api/v1/users/{user_id}", response_model=UserProfileResponse)
@limiter.limit("20/minute")
async def get_user(
    fastapi_request: Request,
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get user profile and preferences (Rate limit: 20/minute)"""
    try:
        if not await user_exists(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        # Load user memory
        user_memory = await memory_manager.load_user_memory(user_id)

        # Parse profile
        profile_content = user_memory.get("profile", "")
        profile_dict = {}
        for line in profile_content.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                profile_dict[key.strip().lower().replace(" ", "_")] = value.strip()

        # Parse preferences
        prefs_content = user_memory.get("preferences", "")
        prefs_dict = {}
        for line in prefs_content.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                prefs_dict[key.strip().lower().replace(" ", "_")] = value.strip()

        return UserProfileResponse(
            user_id=user_id,
            profile=profile_dict,
            preferences=prefs_dict if prefs_dict else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/api/v1/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
async def delete_user(
    fastapi_request: Request,
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Delete a user (for testing purposes) (Rate limit: 20/minute)"""
    try:
        if not await user_exists(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        # Delete from database
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM users WHERE telegram_id = %s", (user_id,))
                await conn.commit()

        logger.info(f"Deleted user via API: {user_id}")
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/api/v1/users/{user_id}/profile", response_model=dict)
@limiter.limit("20/minute")
async def get_user_profile(
    fastapi_request: Request,
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get user profile (Rate limit: 20/minute)"""
    try:
        if not await user_exists(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        user_memory = await memory_manager.load_user_memory(user_id)
        profile_content = user_memory.get("profile", "")

        profile_dict = {}
        for line in profile_content.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                profile_dict[key.strip().lower().replace(" ", "_")] = value.strip()

        return profile_dict

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting profile: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.patch("/api/v1/users/{user_id}/profile")
@limiter.limit("20/minute")
async def update_user_profile(
    fastapi_request: Request,
    user_id: str,
    request: ProfileUpdateRequest,
    api_key: str = Depends(verify_api_key)
):
    """Update a specific profile field (Rate limit: 20/minute)"""
    try:
        if not await user_exists(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        await memory_manager.update_profile(user_id, request.field, str(request.value))

        return {
            "success": True,
            "field": request.field,
            "value": request.value
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/api/v1/users/{user_id}/preferences")
@limiter.limit("20/minute")
async def get_user_preferences(
    fastapi_request: Request,
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get user preferences (Rate limit: 20/minute)"""
    try:
        if not await user_exists(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        user_memory = await memory_manager.load_user_memory(user_id)
        prefs_content = user_memory.get("preferences", "")

        prefs_dict = {}
        for line in prefs_content.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                prefs_dict[key.strip().lower().replace(" ", "_")] = value.strip()

        return prefs_dict

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting preferences: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.patch("/api/v1/users/{user_id}/preferences")
@limiter.limit("20/minute")
async def update_user_preferences(
    fastapi_request: Request,
    user_id: str,
    request: PreferencesUpdateRequest,
    api_key: str = Depends(verify_api_key)
):
    """Update user preferences (Rate limit: 20/minute)"""
    try:
        if not await user_exists(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        await memory_manager.update_preferences(user_id, request.preference, str(request.value))

        return {
            "success": True,
            "preference": request.preference,
            "value": request.value
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating preferences: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/api/v1/users/{user_id}/conversation", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
async def clear_conversation(
    fastapi_request: Request,
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Clear conversation history (Rate limit: 20/minute)"""
    try:
        if not await user_exists(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        await clear_conversation_history(user_id)
        logger.info(f"Cleared conversation for user {user_id}")
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/api/v1/users/{user_id}/food")
@limiter.limit("20/minute")
async def log_food(
    fastapi_request: Request,
    user_id: str,
    request: FoodLogRequest,
    api_key: str = Depends(verify_api_key)
):
    """Log food entry (Rate limit: 20/minute)"""
    try:
        if not await user_exists(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        # Use chat endpoint to process food logging through agent
        # This ensures the same logic as Telegram for food analysis
        message = f"I ate: {request.description}"
        if request.timestamp:
            message += f" at {request.timestamp.strftime('%Y-%m-%d %H:%M')}"

        response = await get_agent_response(
            telegram_id=user_id,
            user_message=message,
            memory_manager=memory_manager,
            reminder_manager=None,
            message_history=[],
            bot_application=None
        )

        return {
            "success": True,
            "description": request.description,
            "response": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging food: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/api/v1/users/{user_id}/food", response_model=FoodSummaryResponse)
@limiter.limit("20/minute")
async def get_food_summary(
    fastapi_request: Request,
    user_id: str,
    date: Optional[str] = None,
    api_key: str = Depends(verify_api_key)
):
    """Get food summary for a date (Rate limit: 20/minute)"""
    try:
        if not await user_exists(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        # Default to today if no date provided
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        entries = await get_food_entries_by_date(
            user_id=user_id,
            start_date=date,
            end_date=date
        )

        total_calories = sum(e.get("total_calories", 0) or 0 for e in entries)
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0

        for entry in entries:
            macros = entry.get("total_macros", {})
            if isinstance(macros, str):
                import json
                macros = json.loads(macros)

            total_protein += macros.get("protein", 0) or 0
            total_carbs += macros.get("carbs", 0) or 0
            total_fat += macros.get("fat", 0) or 0

        return FoodSummaryResponse(
            date=date,
            entries=entries,
            total_calories=total_calories,
            total_protein=total_protein,
            total_carbs=total_carbs,
            total_fat=total_fat
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting food summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/api/v1/users/{user_id}/reminders", response_model=ReminderResponse)
@limiter.limit("20/minute")
async def create_reminder_endpoint(
    fastapi_request: Request,
    user_id: str,
    request: ReminderRequest,
    api_key: str = Depends(verify_api_key)
):
    """Create a reminder (Rate limit: 20/minute)"""
    try:
        if not await user_exists(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        from uuid import uuid4

        # Create reminder object
        reminder_id = str(uuid4())

        if request.type == "daily" and request.daily_time:
            schedule = ReminderSchedule(
                type="daily",
                time=request.daily_time,
                timezone=request.timezone or "UTC"
            )
        elif request.type == "one_time" and request.trigger_time:
            schedule = ReminderSchedule(
                type="one_time",
                trigger_time=request.trigger_time,
                timezone=request.timezone or "UTC"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reminder configuration"
            )

        reminder = Reminder(
            id=reminder_id,
            user_id=user_id,
            reminder_type=request.type,
            message=request.message,
            schedule=schedule,
            active=True,
            enable_completion_tracking=False,
            streak_motivation=False
        )

        await create_reminder(reminder)

        return ReminderResponse(
            id=reminder_id,
            user_id=user_id,
            type=request.type,
            message=request.message,
            schedule=schedule.dict(),
            active=True
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating reminder: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/api/v1/users/{user_id}/reminders", response_model=ReminderListResponse)
@limiter.limit("20/minute")
async def get_reminders(
    fastapi_request: Request,
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get all active reminders for user (Rate limit: 20/minute)"""
    try:
        if not await user_exists(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        reminders = await get_active_reminders(user_id)

        reminder_responses = []
        for r in reminders:
            reminder_responses.append(ReminderResponse(
                id=str(r.get('id')),
                user_id=user_id,
                type=r.get('reminder_type', 'daily'),
                message=r.get('message', ''),
                schedule=r.get('schedule', {}),
                active=True
            ))

        return ReminderListResponse(reminders=reminder_responses)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting reminders: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/api/v1/users/{user_id}/reminders/{reminder_id}/status", response_model=ReminderStatusResponse)
@limiter.limit("20/minute")
async def get_reminder_status(
    fastapi_request: Request,
    user_id: str,
    reminder_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Check if a reminder has triggered (Rate limit: 20/minute)"""
    try:
        if not await user_exists(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        reminder = await get_reminder_by_id(reminder_id)
        if not reminder or reminder.get('user_id') != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reminder {reminder_id} not found"
            )

        # Check completion status from database
        from src.db.queries import db
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT completed, completed_at
                    FROM reminder_completions
                    WHERE user_id = %s AND reminder_id = %s
                    ORDER BY completed_at DESC
                    LIMIT 1
                    """,
                    (user_id, reminder_id)
                )
                row = await cur.fetchone()

        if row:
            return ReminderStatusResponse(
                id=reminder_id,
                triggered=True,
                completed=row[0],
                completed_at=row[1]
            )
        else:
            return ReminderStatusResponse(
                id=reminder_id,
                triggered=False,
                completed=False,
                completed_at=None
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting reminder status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/api/v1/users/{user_id}/xp", response_model=XPResponse)
@limiter.limit("30/minute")
async def get_xp(
    fastapi_request: Request,
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get user XP and level (Rate limit: 30/minute)"""
    try:
        if not await user_exists(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        xp_data = await get_user_xp_level(user_id)

        return XPResponse(
            user_id=user_id,
            xp=xp_data.get('xp', 0),
            level=xp_data.get('level', 1),
            tier=xp_data.get('tier', 'Bronze'),
            xp_to_next_level=xp_data.get('xp_to_next_level', 100)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting XP: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/api/v1/users/{user_id}/streaks", response_model=StreakResponse)
@limiter.limit("30/minute")
async def get_streaks_endpoint(
    fastapi_request: Request,
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get user streaks (Rate limit: 30/minute)"""
    try:
        if not await user_exists(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        streaks = await get_user_streaks(user_id)

        return StreakResponse(
            user_id=user_id,
            streaks=streaks
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting streaks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/api/v1/users/{user_id}/achievements", response_model=AchievementResponse)
@limiter.limit("30/minute")
async def get_achievements_endpoint(
    fastapi_request: Request,
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get user achievements (Rate limit: 30/minute)"""
    try:
        if not await user_exists(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        achievements = await get_user_achievements(user_id)
        from src.db.queries import get_all_achievements

        all_achievements = await get_all_achievements()

        unlocked_ids = {a['achievement_id'] for a in achievements}
        unlocked = [a for a in all_achievements if a['id'] in unlocked_ids]
        locked = [a for a in all_achievements if a['id'] not in unlocked_ids]

        return AchievementResponse(
            user_id=user_id,
            unlocked=unlocked,
            locked=locked
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting achievements: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/api/health", response_model=HealthCheckResponse)
@limiter.limit("60/minute")
async def health_check(fastapi_request: Request):
    """Health check endpoint (Rate limit: 60/minute for monitoring systems)"""
    try:
        # Check database connection
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
                await cur.fetchone()

        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "disconnected"

    return HealthCheckResponse(
        status="healthy" if db_status == "connected" else "degraded",
        database=db_status,
        timestamp=datetime.now()
    )


@router.get("/api/v1/metrics")
async def get_metrics():
    """
    Performance metrics endpoint

    Returns system metrics, database pool statistics, and cache performance.
    Used by monitoring tools and load testing infrastructure.
    """
    try:
        import psutil
        from src.cache.redis_client import get_cache

        # System metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk_io = psutil.disk_io_counters()

        system_metrics = {
            "cpu_percent": cpu_percent,
            "memory_mb": memory.used / 1024 / 1024,
            "memory_percent": memory.percent,
            "memory_available_mb": memory.available / 1024 / 1024,
            "disk_read_mb": disk_io.read_bytes / 1024 / 1024 if disk_io else 0,
            "disk_write_mb": disk_io.write_bytes / 1024 / 1024 if disk_io else 0,
        }

        # Database pool statistics
        pool_stats = db.get_pool_stats()
        database_metrics = {
            "pool_size": pool_stats.get("size", 0),
            "pool_available": pool_stats.get("available", 0),
            "pool_active": pool_stats.get("active", 0),
            "pool_min_size": pool_stats.get("min_size", 0),
            "pool_max_size": pool_stats.get("max_size", 0),
            "pool_utilization_percent": (
                (pool_stats.get("active", 0) / pool_stats.get("size", 1)) * 100
                if pool_stats.get("size", 0) > 0 else 0
            ),
        }

        # Redis cache statistics
        cache = get_cache()
        cache_stats = {}
        if cache:
            stats = cache.get_stats()
            total_reads = stats.get("hits", 0) + stats.get("misses", 0)
            hit_rate = (
                (stats.get("hits", 0) / total_reads * 100)
                if total_reads > 0 else 0
            )

            cache_stats = {
                "enabled": cache.enabled,
                "hits": stats.get("hits", 0),
                "misses": stats.get("misses", 0),
                "sets": stats.get("sets", 0),
                "deletes": stats.get("deletes", 0),
                "errors": stats.get("errors", 0),
                "total_reads": total_reads,
                "hit_rate_percent": hit_rate,
            }
        else:
            cache_stats = {
                "enabled": False,
                "hits": 0,
                "misses": 0,
                "sets": 0,
                "deletes": 0,
                "errors": 0,
                "total_reads": 0,
                "hit_rate_percent": 0,
            }

        return {
            "timestamp": datetime.now().isoformat(),
            "system": system_metrics,
            "database": database_metrics,
            "cache": cache_stats,
        }

    except Exception as e:
        logger.error(f"Error collecting metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to collect metrics: {str(e)}"
        )


@router.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.

    Exposes all application metrics in Prometheus text format.
    This endpoint should be scraped by Prometheus server.

    Returns:
        Metrics in Prometheus exposition format
    """
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from fastapi.responses import Response

    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@router.get("/api/cache/stats")
async def get_cache_statistics(api_key: str = Depends(verify_api_key)):
    """
    Get cache performance statistics

    Returns cache hit/miss rates and load reduction metrics.
    Target: 30% load reduction on user preferences, profiles, and gamification data.
    """
    from src.utils.cache import get_cache_stats

    stats = get_cache_stats()

    return {
        "cache_stats": stats,
        "target_load_reduction": 30.0,
        "target_achieved": stats["load_reduction_percent"] >= 30.0,
        "timestamp": datetime.now()
    }


# ============================================================================
# Formula API Endpoints (Epic 009 - Phase 3)
# ============================================================================

from src.api.models import (
    FormulaCreateRequest, FormulaUpdateRequest, FormulaResponse,
    FormulaListResponse, FormulaSearchRequest, FormulaSearchResponse,
    FormulaUseRequest, FormulaSuggestionRequest, FormulaSuggestionResponse
)
from src.services.formula_detection import get_formula_detection_service
from src.services.formula_suggestions import get_suggestion_service


@router.post("/api/formulas", response_model=FormulaResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_formula(
    fastapi_request: Request,
    request: FormulaCreateRequest,
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Create a new food formula

    Rate limit: 20/minute
    """
    try:
        import json

        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO food_formulas
                    (user_id, name, keywords, description, foods, total_calories,
                     total_macros, reference_photo_path, created_from_entry_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, created_at, updated_at
                    """,
                    (
                        user_id,
                        request.name,
                        request.keywords,
                        request.description,
                        json.dumps(request.foods),
                        request.total_calories,
                        json.dumps(request.total_macros),
                        request.reference_photo_path,
                        request.created_from_entry_id
                    )
                )
                result = await cur.fetchone()
                await conn.commit()

        return FormulaResponse(
            id=str(result["id"]),
            name=request.name,
            keywords=request.keywords,
            description=request.description,
            foods=request.foods,
            total_calories=request.total_calories,
            total_macros=request.total_macros,
            reference_photo_path=request.reference_photo_path,
            is_auto_detected=False,
            confidence_score=None,
            times_used=1,
            last_used_at=result["created_at"],
            created_at=result["created_at"]
        )

    except Exception as e:
        logger.error(f"Error creating formula: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/api/formulas", response_model=FormulaListResponse)
@limiter.limit("30/minute")
async def list_formulas(
    fastapi_request: Request,
    user_id: str,
    limit: int = 20,
    include_usage_stats: bool = True,
    api_key: str = Depends(verify_api_key)
):
    """
    Get all formulas for a user

    Rate limit: 30/minute
    """
    try:
        import json

        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT id, name, keywords, description, foods, total_calories,
                           total_macros, reference_photo_path, is_auto_detected,
                           confidence_score, times_used, last_used_at, created_at
                    FROM food_formulas
                    WHERE user_id = %s
                    ORDER BY times_used DESC, last_used_at DESC
                    LIMIT %s
                    """,
                    (user_id, min(limit, 100))
                )
                results = await cur.fetchall()

        formulas = []
        for row in results:
            # Handle JSONB columns
            foods = row["foods"]
            if isinstance(foods, str):
                foods = json.loads(foods)

            total_macros = row["total_macros"]
            if isinstance(total_macros, str):
                total_macros = json.loads(total_macros)

            formulas.append(FormulaResponse(
                id=str(row["id"]),
                name=row["name"],
                keywords=row["keywords"] or [],
                description=row["description"],
                foods=foods,
                total_calories=row["total_calories"],
                total_macros=total_macros,
                reference_photo_path=row["reference_photo_path"],
                is_auto_detected=row["is_auto_detected"],
                confidence_score=row["confidence_score"],
                times_used=row["times_used"],
                last_used_at=row["last_used_at"],
                created_at=row["created_at"]
            ))

        return FormulaListResponse(
            formulas=formulas,
            total_count=len(formulas)
        )

    except Exception as e:
        logger.error(f"Error listing formulas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/api/formulas/{formula_id}", response_model=FormulaResponse)
@limiter.limit("30/minute")
async def get_formula(
    fastapi_request: Request,
    formula_id: str,
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Get a specific formula by ID

    Rate limit: 30/minute
    """
    try:
        import json

        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT id, name, keywords, description, foods, total_calories,
                           total_macros, reference_photo_path, is_auto_detected,
                           confidence_score, times_used, last_used_at, created_at
                    FROM food_formulas
                    WHERE id = %s AND user_id = %s
                    """,
                    (formula_id, user_id)
                )
                row = await cur.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Formula not found"
            )

        # Handle JSONB columns
        foods = row["foods"]
        if isinstance(foods, str):
            foods = json.loads(foods)

        total_macros = row["total_macros"]
        if isinstance(total_macros, str):
            total_macros = json.loads(total_macros)

        return FormulaResponse(
            id=str(row["id"]),
            name=row["name"],
            keywords=row["keywords"] or [],
            description=row["description"],
            foods=foods,
            total_calories=row["total_calories"],
            total_macros=total_macros,
            reference_photo_path=row["reference_photo_path"],
            is_auto_detected=row["is_auto_detected"],
            confidence_score=row["confidence_score"],
            times_used=row["times_used"],
            last_used_at=row["last_used_at"],
            created_at=row["created_at"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting formula: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put("/api/formulas/{formula_id}", response_model=FormulaResponse)
@limiter.limit("20/minute")
async def update_formula(
    fastapi_request: Request,
    formula_id: str,
    request: FormulaUpdateRequest,
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Update a formula

    Rate limit: 20/minute
    """
    try:
        import json

        # Build update fields
        update_fields = []
        params = []

        if request.name is not None:
            update_fields.append("name = %s")
            params.append(request.name)

        if request.keywords is not None:
            update_fields.append("keywords = %s")
            params.append(request.keywords)

        if request.description is not None:
            update_fields.append("description = %s")
            params.append(request.description)

        if request.foods is not None:
            update_fields.append("foods = %s")
            params.append(json.dumps(request.foods))

        if request.total_calories is not None:
            update_fields.append("total_calories = %s")
            params.append(request.total_calories)

        if request.total_macros is not None:
            update_fields.append("total_macros = %s")
            params.append(json.dumps(request.total_macros))

        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )

        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.extend([formula_id, user_id])

        async with db.connection() as conn:
            async with conn.cursor() as cur:
                query = f"""
                    UPDATE food_formulas
                    SET {', '.join(update_fields)}
                    WHERE id = %s AND user_id = %s
                    RETURNING id, name, keywords, description, foods, total_calories,
                              total_macros, reference_photo_path, is_auto_detected,
                              confidence_score, times_used, last_used_at, created_at
                """
                await cur.execute(query, params)
                row = await cur.fetchone()
                await conn.commit()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Formula not found"
            )

        # Handle JSONB columns
        foods = row["foods"]
        if isinstance(foods, str):
            foods = json.loads(foods)

        total_macros = row["total_macros"]
        if isinstance(total_macros, str):
            total_macros = json.loads(total_macros)

        return FormulaResponse(
            id=str(row["id"]),
            name=row["name"],
            keywords=row["keywords"] or [],
            description=row["description"],
            foods=foods,
            total_calories=row["total_calories"],
            total_macros=total_macros,
            reference_photo_path=row["reference_photo_path"],
            is_auto_detected=row["is_auto_detected"],
            confidence_score=row["confidence_score"],
            times_used=row["times_used"],
            last_used_at=row["last_used_at"],
            created_at=row["created_at"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating formula: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/api/formulas/{formula_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
async def delete_formula(
    fastapi_request: Request,
    formula_id: str,
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Delete a formula

    Rate limit: 20/minute
    """
    try:
        async with db.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    DELETE FROM food_formulas
                    WHERE id = %s AND user_id = %s
                    """,
                    (formula_id, user_id)
                )
                deleted_count = cur.rowcount
                await conn.commit()

        if deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Formula not found"
            )

        return None  # 204 No Content

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting formula: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/api/formulas/search", response_model=FormulaSearchResponse)
@limiter.limit("30/minute")
async def search_formulas(
    fastapi_request: Request,
    keyword: str,
    user_id: str,
    limit: int = 5,
    api_key: str = Depends(verify_api_key)
):
    """
    Search formulas by keyword

    Rate limit: 30/minute
    """
    try:
        service = get_formula_detection_service()

        formulas = await service.find_formulas_by_keyword(
            user_id=user_id,
            keyword=keyword,
            limit=min(limit, 20)
        )

        return FormulaSearchResponse(
            formulas=formulas,
            query=keyword,
            match_count=len(formulas)
        )

    except Exception as e:
        logger.error(f"Error searching formulas: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/api/formulas/{formula_id}/use", status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
async def log_formula_usage(
    fastapi_request: Request,
    formula_id: str,
    request: FormulaUseRequest,
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Log formula usage

    Rate limit: 60/minute (high limit for active logging)
    """
    try:
        import json

        async with db.connection() as conn:
            async with conn.cursor() as cur:
                # Verify formula exists
                await cur.execute(
                    "SELECT id FROM food_formulas WHERE id = %s AND user_id = %s",
                    (formula_id, user_id)
                )
                if not await cur.fetchone():
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Formula not found"
                    )

                # Log usage
                await cur.execute(
                    """
                    INSERT INTO formula_usage_log
                    (formula_id, food_entry_id, user_id, match_method,
                     match_confidence, is_exact_match, variations)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        formula_id,
                        request.food_entry_id,
                        user_id,
                        request.match_method,
                        request.match_confidence,
                        request.is_exact_match,
                        json.dumps(request.variations) if request.variations else None
                    )
                )
                await conn.commit()

        return {"status": "logged", "formula_id": formula_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging formula usage: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/api/formulas/suggestions", response_model=FormulaSuggestionResponse)
@limiter.limit("30/minute")
async def get_formula_suggestions(
    fastapi_request: Request,
    request: FormulaSuggestionRequest,
    user_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Get auto-suggestions for formulas

    Rate limit: 30/minute
    """
    try:
        service = get_suggestion_service()

        suggestions = await service.suggest_formulas(
            user_id=user_id,
            text=request.text,
            image_path=request.image_path,
            max_suggestions=request.max_suggestions
        )

        # Convert dataclass suggestions to dicts
        suggestion_dicts = [
            {
                "formula_id": s.formula_id,
                "name": s.name,
                "foods": s.foods,
                "total_calories": s.total_calories,
                "total_macros": s.total_macros,
                "confidence": s.confidence,
                "reason": s.reason,
                "match_method": s.match_method
            }
            for s in suggestions
        ]

        return FormulaSuggestionResponse(
            suggestions=suggestion_dicts,
            suggestion_count=len(suggestion_dicts)
        )

    except Exception as e:
        logger.error(f"Error getting formula suggestions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
