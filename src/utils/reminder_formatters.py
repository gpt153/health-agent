"""Formatters for reminder statistics and analytics display"""
from typing import Dict, List


def create_progress_bar(percentage: float, width: int = 10, filled: str = "█", empty: str = "░") -> str:
    """
    Create a text-based progress bar

    Args:
        percentage: Value between 0.0 and 1.0
        width: Total width of the bar in characters
        filled: Character for filled portion
        empty: Character for empty portion

    Returns:
        Progress bar string
    """
    filled_count = int(percentage * width)
    empty_count = width - filled_count
    return filled * filled_count + empty * empty_count


def format_percentage_with_bar(value: float, label: str = "", width: int = 10) -> str:
    """
    Format percentage with visual bar

    Args:
        value: Percentage as float (0.0 to 1.0)
        label: Optional label to prepend
        width: Width of progress bar

    Returns:
        Formatted string like "Label: ████████░░ 80%"
    """
    bar = create_progress_bar(value, width)
    percentage_str = f"{value*100:.0f}%"
    prefix = f"{label}: " if label else ""
    return f"{prefix}{bar} {percentage_str}"


def format_reminder_statistics(analytics: dict, reminder_message: str) -> str:
    """
    Format reminder analytics into user-friendly Telegram message

    Args:
        analytics: Dict from get_reminder_analytics()
        reminder_message: The reminder's message text

    Returns:
        Formatted Markdown string for Telegram
    """
    if "error" in analytics:
        return f"❌ {analytics['error']}"

    # Header
    lines = [
        f"📊 **Statistics for: {reminder_message}**",
        f"_(Last {analytics['period_days']} days)_\n"
    ]

    # Completion rate with visual indicator and progress bar
    rate = analytics['completion_rate']
    rate_decimal = rate / 100.0  # Convert to 0.0-1.0

    if rate >= 80:
        emoji = "🔥"
        message = "Excellent!"
    elif rate >= 60:
        emoji = "👍"
        message = "Good job!"
    elif rate >= 40:
        emoji = "📈"
        message = "Keep improving!"
    else:
        emoji = "💪"
        message = "You got this!"

    progress_bar = create_progress_bar(rate_decimal)
    lines.append(f"**{emoji} Completion Rate**")
    lines.append(f"{progress_bar} **{rate}%** {message}")
    lines.append("")

    # Summary stats
    lines.append("**Summary:**")
    lines.append(f"✅ Completed: {analytics['total_completions']} / {analytics['total_expected']} days")

    if analytics['total_skips'] > 0:
        lines.append(f"⏭️ Skipped: {analytics['total_skips']} days")

    if analytics['total_missed'] > 0:
        lines.append(f"❌ Missed: {analytics['total_missed']} days")

    lines.append("")

    # Streak information
    lines.append("**Streaks:**")
    current_streak = analytics['current_streak']
    best_streak = analytics['best_streak']

    if current_streak > 0:
        fire_emoji = "🔥" * min(current_streak, 3)
        lines.append(f"{fire_emoji} Current: **{current_streak} days**")
    else:
        lines.append(f"Current: {current_streak} days (start today!)")

    if best_streak > 0:
        lines.append(f"🏆 Best: {best_streak} days")

    lines.append("")

    # Timing information
    if analytics['average_delay_minutes'] != 0:
        delay = analytics['average_delay_minutes']
        if delay > 0:
            hours = delay // 60
            mins = delay % 60
            if hours > 0:
                time_str = f"{hours}h {mins}m"
            else:
                time_str = f"{mins}m"
            lines.append(f"⏱️ Average: {time_str} after scheduled time")
        else:
            lines.append(f"⏱️ Average: Completed early!")
        lines.append("")

    # Skip reasons breakdown
    if analytics['skip_reasons']:
        lines.append("**Skip Reasons:**")
        reason_emoji = {
            'sick': '😷',
            'out_of_stock': '📦',
            'doctor_advice': '🏥',
            'other': '⏭️'
        }
        reason_names = {
            'sick': 'Not feeling well',
            'out_of_stock': 'Out of stock',
            'doctor_advice': "Doctor's advice",
            'other': 'Other'
        }
        for reason, count in analytics['skip_reasons'].items():
            emoji = reason_emoji.get(reason, '⏭️')
            name = reason_names.get(reason, reason)
            lines.append(f"{emoji} {name}: {count}")
        lines.append("")

    # Motivational message
    if rate >= 80:
        lines.append("🌟 _Amazing consistency! Keep it up!_")
    elif rate >= 60:
        lines.append("💪 _Great progress! You're building a strong habit!_")
    elif rate >= 40:
        lines.append("📈 _You're on the right track! Every day counts!_")
    elif current_streak > 0:
        lines.append(f"🔥 _{current_streak}-day streak active! Don't break it!_")
    else:
        lines.append("💙 _Every journey starts with a single step. You got this!_")

    return "\n".join(lines)


def format_day_of_week_patterns(patterns: dict, reminder_message: str) -> str:
    """
    Format day-of-week patterns into user-friendly display

    Args:
        patterns: Dict from analyze_day_of_week_patterns()
        reminder_message: The reminder's message text

    Returns:
        Formatted Markdown string
    """
    lines = [
        f"📅 **Weekly Patterns: {reminder_message}**\n",
        "Here's how you're doing each day of the week:\n"
    ]

    # Sort by day order (Monday first)
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    for day in day_order:
        stats = patterns[day]
        rate = stats['completion_rate']

        # Visual indicator
        if rate >= 80:
            emoji = "🔥"
        elif rate >= 60:
            emoji = "✅"
        elif rate >= 40:
            emoji = "📊"
        else:
            emoji = "📉"

        # Format day stats
        day_line = f"{emoji} **{day}**: {rate}% ({stats['completions']} done"

        if stats['skips'] > 0:
            day_line += f", {stats['skips']} skipped"

        if stats['missed'] > 0:
            day_line += f", {stats['missed']} missed"

        day_line += ")"

        lines.append(day_line)

    # Find best and worst days
    sorted_days = sorted(patterns.items(), key=lambda x: x[1]['completion_rate'], reverse=True)
    best_day = sorted_days[0]
    worst_day = sorted_days[-1]

    lines.append("")
    lines.append(f"🏆 **Best day**: {best_day[0]} ({best_day[1]['completion_rate']}%)")

    if worst_day[1]['completion_rate'] < best_day[1]['completion_rate']:
        lines.append(f"💪 **Needs focus**: {worst_day[0]} ({worst_day[1]['completion_rate']}%)")

    return "\n".join(lines)


def format_multi_reminder_comparison(comparisons: List[dict]) -> str:
    """
    Format multi-reminder comparison into user-friendly display

    Args:
        comparisons: List of dicts from get_multi_reminder_comparison()

    Returns:
        Formatted Markdown string
    """
    if not comparisons:
        return "📊 **No tracked reminders found**\n\nCreate a reminder with health-related keywords to enable tracking!"

    lines = [
        "📊 **All Your Reminders**\n",
        f"Showing {len(comparisons)} tracked reminder(s):\n"
    ]

    for i, reminder in enumerate(comparisons, 1):
        rate = reminder['completion_rate']

        # Visual indicator
        if rate >= 80:
            emoji = "🔥"
        elif rate >= 60:
            emoji = "✅"
        elif rate >= 40:
            emoji = "📊"
        else:
            emoji = "💪"

        # Format reminder line
        message = reminder['message']
        if len(message) > 40:
            message = message[:37] + "..."

        lines.append(f"{i}. {emoji} **{message}**")
        lines.append(f"   Rate: {rate}% | Streak: {reminder['current_streak']} | Done: {reminder['total_completions']}")

        if i < len(comparisons):
            lines.append("")

    # Overall stats
    total_completions = sum(r['total_completions'] for r in comparisons)
    avg_rate = sum(r['completion_rate'] for r in comparisons) / len(comparisons)

    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append(f"**Overall**: {avg_rate:.1f}% avg | {total_completions} total completions")

    return "\n".join(lines)


def format_streak_notification(
    streak_count: int,
    reminder_message: str,
    milestone: bool = False
) -> str:
    """
    Format streak achievement notification

    Args:
        streak_count: Current streak count
        reminder_message: The reminder's message
        milestone: Whether this is a milestone (5, 10, 20, 30, etc.)

    Returns:
        Formatted notification message
    """
    fire_emoji = "🔥" * min(streak_count, 5)

    if milestone:
        if streak_count >= 30:
            return (
                f"🎉🔥 **INCREDIBLE!** 🔥🎉\n\n"
                f"You've hit a **{streak_count}-day streak** for:\n"
                f"_{reminder_message}_\n\n"
                f"This is exceptional consistency! You're building a powerful habit! 💪"
            )
        elif streak_count >= 20:
            return (
                f"🏆 **AMAZING STREAK!** 🏆\n\n"
                f"{fire_emoji} **{streak_count} days** in a row!\n"
                f"_{reminder_message}_\n\n"
                f"You're unstoppable! Keep going! 🚀"
            )
        elif streak_count >= 10:
            return (
                f"🌟 **DOUBLE DIGITS!** 🌟\n\n"
                f"{fire_emoji} **{streak_count} days** strong!\n"
                f"_{reminder_message}_\n\n"
                f"This is becoming a real habit! 💪"
            )
        elif streak_count >= 5:
            return (
                f"✨ **5-Day Milestone!** ✨\n\n"
                f"{fire_emoji} You're on a roll!\n"
                f"_{reminder_message}_\n\n"
                f"The habit is forming! 🎯"
            )
    else:
        return f"{fire_emoji} {streak_count}-day streak for {reminder_message}!"


def format_adaptive_suggestions(suggestions: list[dict], reminder_name: str) -> str:
    """
    Format adaptive suggestions into user-friendly message

    Args:
        suggestions: List of suggestion dicts from generate_adaptive_suggestions()
        reminder_name: Name of the reminder

    Returns:
        Formatted Markdown string
    """
    if not suggestions:
        return f"✅ Your '{reminder_name}' reminder is working great! No optimizations needed right now."

    lines = [
        f"💡 **Smart Suggestions for: {reminder_name}**\n",
        f"Based on your completion patterns, here are some ways to improve:\n"
    ]

    for i, suggestion in enumerate(suggestions, 1):
        priority_emoji = {
            "high": "🔴",
            "medium": "🟡",
            "low": "🟢"
        }.get(suggestion["priority"], "⚪")

        lines.append(f"{priority_emoji} **{i}. {suggestion['title']}**")
        lines.append(f"   {suggestion['description']}\n")

    lines.append("📊 These suggestions are based on your actual completion data over the past 30 days.")
    lines.append("\nWant me to apply any of these changes? Just let me know!")

    return "\n".join(lines)
