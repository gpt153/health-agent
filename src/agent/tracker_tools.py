"""
PydanticAI tools for custom tracker querying and analysis.
Epic 006 - Phase 4: Agent Integration
"""
from pydantic_ai import RunContext
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from src.agent import AgentDeps
from src.db.queries import (
    get_tracking_categories,
    query_tracker_entries,
    get_tracker_aggregates,
    find_tracker_patterns,
    find_tracker_correlation,
    get_recent_tracker_entries,
    get_field_value_distribution
)


class TrackerQueryResult(BaseModel):
    """Result of tracker query operations"""
    success: bool
    message: str
    entries: Optional[List[Dict]] = None
    aggregates: Optional[Dict[str, float]] = None
    patterns: Optional[List[Dict]] = None
    insights: Optional[List[Dict]] = None


async def get_user_trackers(ctx: RunContext[AgentDeps]) -> TrackerQueryResult:
    """
    Get all active trackers for the user with their schemas.
    This helps the agent understand what data is available to query and reason about.

    Use this tool first to discover what trackers the user has created.
    """
    try:
        categories = await get_tracking_categories(
            ctx.deps.telegram_id,
            active_only=True
        )

        tracker_info = []
        for cat in categories:
            tracker_info.append({
                "id": str(cat["id"]),
                "name": cat["name"],
                "fields": cat["fields"],
                "icon": cat.get("icon", "📊"),
                "category_type": cat.get("category_type", "custom")
            })

        if not tracker_info:
            return TrackerQueryResult(
                success=True,
                message="No active trackers found. User hasn't created any trackers yet.",
                entries=[]
            )

        message = f"Found {len(tracker_info)} active tracker(s):\n\n"
        for t in tracker_info:
            field_names = ', '.join(t['fields'].keys())
            message += f"{t['icon']} **{t['name']}** (ID: {t['id']})\n"
            message += f"   Fields: {field_names}\n\n"

        return TrackerQueryResult(
            success=True,
            message=message,
            entries=tracker_info
        )
    except Exception as e:
        return TrackerQueryResult(
            success=False,
            message=f"Failed to get trackers: {str(e)}"
        )


async def query_tracker_data(
    ctx: RunContext[AgentDeps],
    tracker_name: str,
    field_name: str,
    operator: str,
    value: Any,
    days_back: int = 30
) -> TrackerQueryResult:
    """
    Query tracker entries by field value.

    Use this to find specific tracker data based on field conditions.

    Examples:
    - tracker_name="Energy", field_name="level", operator="<", value=5
      → Find all days where energy level was below 5
    - tracker_name="Period", field_name="flow", operator=">=", value=4
      → Find days with heavy flow (4 or 5)
    - tracker_name="Mood", field_name="mood_rating", operator=">", value=7
      → Find days with good mood

    Args:
        tracker_name: Name of the tracker (e.g., "Energy", "Period")
        field_name: Field to query (e.g., "level", "flow")
        operator: Comparison operator: '=', '>', '<', '>=', '<='
        value: Value to compare against
        days_back: How many days to look back (default: 30)
    """
    try:
        # Get tracker definition
        categories = await get_tracking_categories(ctx.deps.telegram_id)
        category = next(
            (c for c in categories if c["name"].lower() == tracker_name.lower()),
            None
        )

        if not category:
            return TrackerQueryResult(
                success=False,
                message=f"Tracker '{tracker_name}' not found. Use get_user_trackers() to see available trackers."
            )

        # Check if field exists
        if field_name not in category["fields"]:
            available_fields = ', '.join(category["fields"].keys())
            return TrackerQueryResult(
                success=False,
                message=f"Field '{field_name}' not found in tracker '{tracker_name}'. Available fields: {available_fields}"
            )

        # Query entries
        start_date = datetime.now() - timedelta(days=days_back)
        entries = await query_tracker_entries(
            user_id=ctx.deps.telegram_id,
            category_id=UUID(category["id"]),
            field_name=field_name,
            operator=operator,
            value=value,
            start_date=start_date
        )

        message = f"Found {len(entries)} entries where {field_name} {operator} {value} (past {days_back} days)"

        return TrackerQueryResult(
            success=True,
            message=message,
            entries=entries
        )
    except Exception as e:
        return TrackerQueryResult(
            success=False,
            message=f"Query failed: {str(e)}"
        )


async def get_tracker_statistics(
    ctx: RunContext[AgentDeps],
    tracker_name: str,
    field_name: str,
    days_back: int = 30
) -> TrackerQueryResult:
    """
    Get statistics for a tracker field (average, min, max, count).

    Use this to understand overall trends and patterns in numeric tracker data.

    Examples:
    - tracker_name="Energy", field_name="level", days_back=7
      → Get average energy level over the past week
    - tracker_name="Sleep Quality", field_name="quality_rating", days_back=30
      → Get sleep quality stats for the past month
    - tracker_name="Mood", field_name="mood_rating", days_back=14
      → Get mood statistics for past 2 weeks

    Args:
        tracker_name: Name of the tracker
        field_name: Field to analyze
        days_back: Number of days to analyze (default: 30)
    """
    try:
        categories = await get_tracking_categories(ctx.deps.telegram_id)
        category = next(
            (c for c in categories if c["name"].lower() == tracker_name.lower()),
            None
        )

        if not category:
            return TrackerQueryResult(
                success=False,
                message=f"Tracker '{tracker_name}' not found"
            )

        if field_name not in category["fields"]:
            available_fields = ', '.join(category["fields"].keys())
            return TrackerQueryResult(
                success=False,
                message=f"Field '{field_name}' not found. Available: {available_fields}"
            )

        start_date = datetime.now() - timedelta(days=days_back)
        category_id = UUID(category["id"])

        # Get all aggregates
        avg = await get_tracker_aggregates(
            ctx.deps.telegram_id, category_id, field_name, "avg", start_date
        )
        min_val = await get_tracker_aggregates(
            ctx.deps.telegram_id, category_id, field_name, "min", start_date
        )
        max_val = await get_tracker_aggregates(
            ctx.deps.telegram_id, category_id, field_name, "max", start_date
        )
        count = await get_tracker_aggregates(
            ctx.deps.telegram_id, category_id, field_name, "count", start_date
        )

        stats = {
            "average": float(avg) if avg else 0.0,
            "minimum": float(min_val) if min_val else 0.0,
            "maximum": float(max_val) if max_val else 0.0,
            "count": int(count) if count else 0
        }

        if stats["count"] == 0:
            return TrackerQueryResult(
                success=True,
                message=f"No data found for {tracker_name}.{field_name} in the past {days_back} days",
                aggregates=stats
            )

        message = f"**{tracker_name} - {field_name}** (past {days_back} days)\n\n"
        message += f"📊 Average: {stats['average']:.1f}\n"
        message += f"📉 Minimum: {stats['minimum']}\n"
        message += f"📈 Maximum: {stats['maximum']}\n"
        message += f"🔢 Entries: {stats['count']}"

        return TrackerQueryResult(
            success=True,
            message=message,
            aggregates=stats
        )
    except Exception as e:
        return TrackerQueryResult(
            success=False,
            message=f"Statistics failed: {str(e)}"
        )


async def find_tracker_low_values(
    ctx: RunContext[AgentDeps],
    tracker_name: str,
    field_name: str,
    threshold: float,
    days_back: int = 30
) -> TrackerQueryResult:
    """
    Find days where a tracker value was below a threshold.
    Useful for identifying concerning patterns (low energy, poor sleep, etc.).

    Examples:
    - tracker_name="Energy", field_name="level", threshold=5
      → Find days with low energy (< 5)
    - tracker_name="Sleep Quality", field_name="quality_rating", threshold=6
      → Find nights with poor sleep
    - tracker_name="Mood", field_name="mood_rating", threshold=4
      → Find days with low mood

    Args:
        tracker_name: Name of the tracker
        field_name: Field to analyze
        threshold: Threshold value (finds values BELOW this)
        days_back: Number of days to look back (default: 30)
    """
    try:
        categories = await get_tracking_categories(ctx.deps.telegram_id)
        category = next(
            (c for c in categories if c["name"].lower() == tracker_name.lower()),
            None
        )

        if not category:
            return TrackerQueryResult(
                success=False,
                message=f"Tracker '{tracker_name}' not found"
            )

        pattern_days = await find_tracker_patterns(
            user_id=ctx.deps.telegram_id,
            category_id=UUID(category["id"]),
            field_name=field_name,
            threshold=threshold,
            operator="<",
            days=days_back
        )

        if not pattern_days:
            return TrackerQueryResult(
                success=True,
                message=f"✅ Good news! No days with {field_name} below {threshold} in the past {days_back} days.",
                patterns=[]
            )

        percentage = (len(pattern_days) / days_back) * 100

        message = f"⚠️ Found {len(pattern_days)} days with {field_name} < {threshold} ({percentage:.1f}% of days)\n\n"
        message += "**Recent occurrences:**\n"
        for day in pattern_days[:5]:  # Show first 5
            message += f"• {day['date']}: {field_name}={day['field_value']}"
            if day.get('notes'):
                message += f" - {day['notes']}"
            message += "\n"

        return TrackerQueryResult(
            success=True,
            message=message,
            patterns=pattern_days
        )
    except Exception as e:
        return TrackerQueryResult(
            success=False,
            message=f"Pattern detection failed: {str(e)}"
        )


async def get_tracker_value_distribution(
    ctx: RunContext[AgentDeps],
    tracker_name: str,
    field_name: str,
    days_back: int = 30
) -> TrackerQueryResult:
    """
    Get distribution of values for a field.
    Useful for categorical data (symptoms, moods, etc.).

    Examples:
    - tracker_name="Symptoms", field_name="symptom_type"
      → See which symptoms are most common
    - tracker_name="Exercise", field_name="exercise_type"
      → See which types of exercise user does most
    - tracker_name="Mood", field_name="emotions"
      → See emotional patterns

    Args:
        tracker_name: Name of the tracker
        field_name: Field to analyze
        days_back: Number of days to analyze (default: 30)
    """
    try:
        categories = await get_tracking_categories(ctx.deps.telegram_id)
        category = next(
            (c for c in categories if c["name"].lower() == tracker_name.lower()),
            None
        )

        if not category:
            return TrackerQueryResult(
                success=False,
                message=f"Tracker '{tracker_name}' not found"
            )

        start_date = datetime.now() - timedelta(days=days_back)

        distribution = await get_field_value_distribution(
            user_id=ctx.deps.telegram_id,
            category_id=UUID(category["id"]),
            field_name=field_name,
            start_date=start_date
        )

        if not distribution:
            return TrackerQueryResult(
                success=True,
                message=f"No data found for {tracker_name}.{field_name} in the past {days_back} days",
                insights=[]
            )

        message = f"**{tracker_name} - {field_name} Distribution** (past {days_back} days)\n\n"
        for item in distribution[:10]:  # Show top 10
            value = item['field_value']
            count = item['count']
            pct = item['percentage']
            message += f"• {value}: {count} times ({pct}%)\n"

        return TrackerQueryResult(
            success=True,
            message=message,
            insights=distribution
        )
    except Exception as e:
        return TrackerQueryResult(
            success=False,
            message=f"Distribution analysis failed: {str(e)}"
        )


async def get_recent_tracker_data(
    ctx: RunContext[AgentDeps],
    tracker_name: str,
    limit: int = 7
) -> TrackerQueryResult:
    """
    Get most recent entries for a tracker.
    Useful for showing user their recent tracking history.

    Examples:
    - tracker_name="Energy", limit=7
      → Show past week of energy levels
    - tracker_name="Period", limit=3
      → Show last 3 period tracking entries
    - tracker_name="Medication", limit=5
      → Show last 5 medication logs

    Args:
        tracker_name: Name of the tracker
        limit: Number of recent entries to retrieve (default: 7)
    """
    try:
        categories = await get_tracking_categories(ctx.deps.telegram_id)
        category = next(
            (c for c in categories if c["name"].lower() == tracker_name.lower()),
            None
        )

        if not category:
            return TrackerQueryResult(
                success=False,
                message=f"Tracker '{tracker_name}' not found"
            )

        entries = await get_recent_tracker_entries(
            user_id=ctx.deps.telegram_id,
            category_id=UUID(category["id"]),
            limit=limit
        )

        if not entries:
            return TrackerQueryResult(
                success=True,
                message=f"No entries found for {tracker_name}",
                entries=[]
            )

        message = f"**Recent {tracker_name} entries:**\n\n"
        for entry in entries:
            timestamp = entry['timestamp']
            data = entry['data']
            notes = entry.get('notes', '')

            message += f"📅 {timestamp.strftime('%Y-%m-%d %H:%M')}\n"
            for field, value in data.items():
                message += f"   • {field}: {value}\n"
            if notes:
                message += f"   💭 {notes}\n"
            message += "\n"

        return TrackerQueryResult(
            success=True,
            message=message,
            entries=entries
        )
    except Exception as e:
        return TrackerQueryResult(
            success=False,
            message=f"Failed to get recent entries: {str(e)}"
        )
