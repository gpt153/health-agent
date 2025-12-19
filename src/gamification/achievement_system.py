"""
Achievement System

Tracks and awards achievements across multiple categories:
- Consistency (streaks, perfect periods)
- Domain-specific (medication, nutrition, exercise, sleep, etc.)
- Milestones (levels, total XP)
- Recovery (bouncing back from setbacks)

Features:
- Progress tracking for locked achievements
- Automatic detection and awarding
- XP rewards for unlocking achievements
"""

from typing import Dict, List, Optional
from datetime import date, datetime, timedelta
import logging

from src.gamification import mock_store

logger = logging.getLogger(__name__)


async def check_and_award_achievements(
    user_id: str,
    trigger_type: str,
    context: Dict
) -> List[Dict[str, any]]:
    """
    Check if user unlocked any achievements based on recent activity

    Args:
        user_id: User's Telegram ID
        trigger_type: What triggered the check ('streak', 'level_up', 'completion', 'xp_milestone')
        context: Additional context (e.g., {'streak_type': 'medication', 'streak_count': 7})

    Returns:
        List of newly unlocked achievements:
        [
            {
                'achievement_id': str,
                'achievement_key': str,
                'name': str,
                'description': str,
                'icon': str,
                'xp_reward': int,
                'tier': str,
                'unlocked_at': datetime
            }
        ]
    """
    newly_unlocked = []

    # Get all achievements
    all_achievements = mock_store.get_all_achievements()

    # Get user's already unlocked achievements
    user_achievements = mock_store.get_user_achievements(user_id)
    unlocked_ids = {ach['achievement_id'] for ach in user_achievements if ach.get('unlocked_at')}

    # Map achievement IDs to keys
    achievement_id_to_key = {ach['id']: ach['achievement_key'] for ach in all_achievements}
    unlocked_keys = {achievement_id_to_key.get(aid) for aid in unlocked_ids if achievement_id_to_key.get(aid)}

    # Check each achievement
    for achievement in all_achievements:
        achievement_key = achievement['achievement_key']

        # Skip if already unlocked
        if achievement_key in unlocked_keys:
            continue

        # Check if achievement criteria is met
        criteria = achievement['criteria']
        is_unlocked = False

        if criteria['type'] == 'completion_count':
            # Check total completion count across all domains or specific domain
            is_unlocked = await _check_completion_count(user_id, criteria, context)

        elif criteria['type'] == 'streak':
            # Check streak achievements
            is_unlocked = await _check_streak_achievement(user_id, criteria, context)

        elif criteria['type'] == 'perfect_period':
            # Check perfect completion period
            is_unlocked = await _check_perfect_period(user_id, criteria, context)

        elif criteria['type'] == 'domain_count':
            # Check domain-specific completion counts
            is_unlocked = await _check_domain_count(user_id, criteria, context)

        elif criteria['type'] == 'level':
            # Check level milestone
            is_unlocked = await _check_level_milestone(user_id, criteria, context)

        elif criteria['type'] == 'total_xp':
            # Check total XP milestone
            is_unlocked = await _check_xp_milestone(user_id, criteria, context)

        elif criteria['type'] == 'recovery':
            # Check recovery achievements (more complex)
            is_unlocked = await _check_recovery_achievement(user_id, criteria, context)

        elif criteria['type'] == 'streak_recovery':
            # Check if user started new streak after breaking one
            is_unlocked = await _check_streak_recovery(user_id, criteria, context)

        elif criteria['type'] == 'sustained_effort':
            # Check sustained completion rate over time
            is_unlocked = await _check_sustained_effort(user_id, criteria, context)

        # If unlocked, award it
        if is_unlocked:
            unlocked_data = {
                'achievement_id': achievement['id'],
                'achievement_key': achievement_key,
                'name': achievement['name'],
                'description': achievement['description'],
                'icon': achievement['icon'],
                'xp_reward': achievement['xp_reward'],
                'tier': achievement['tier'],
                'unlocked_at': datetime.now()
            }

            # Save to store
            mock_store.unlock_user_achievement(user_id, achievement['id'])

            newly_unlocked.append(unlocked_data)

            logger.info(
                f"User {user_id} unlocked achievement: {achievement_key} "
                f"({achievement['name']}) +{achievement['xp_reward']} XP"
            )

    return newly_unlocked


async def get_user_achievements(
    user_id: str,
    include_locked: bool = False
) -> Dict[str, any]:
    """
    Get user's achievements with progress

    Args:
        user_id: User's Telegram ID
        include_locked: Whether to include locked achievements with progress

    Returns:
        {
            'unlocked': [list of unlocked achievements],
            'locked': [list of locked achievements with progress] (if include_locked=True),
            'total_unlocked': int,
            'total_achievements': int,
            'total_xp_from_achievements': int
        }
    """
    # Get user's unlocked achievements
    user_achievements = mock_store.get_user_achievements(user_id)

    # Get all achievements for reference
    all_achievements = mock_store.get_all_achievements()
    achievement_map = {ach['id']: ach for ach in all_achievements}

    # Format unlocked achievements
    unlocked = []
    unlocked_ids = set()
    total_xp = 0

    for user_ach in user_achievements:
        if user_ach.get('unlocked_at'):
            achievement = achievement_map.get(user_ach['achievement_id'])
            if achievement:
                unlocked.append({
                    'achievement_key': achievement['achievement_key'],
                    'name': achievement['name'],
                    'description': achievement['description'],
                    'icon': achievement['icon'],
                    'category': achievement['category'],
                    'tier': achievement['tier'],
                    'xp_reward': achievement['xp_reward'],
                    'unlocked_at': user_ach['unlocked_at'],
                })
                unlocked_ids.add(user_ach['achievement_id'])
                total_xp += achievement['xp_reward']

    # Sort by unlock date (most recent first)
    unlocked.sort(key=lambda x: x['unlocked_at'], reverse=True)

    result = {
        'unlocked': unlocked,
        'total_unlocked': len(unlocked),
        'total_achievements': len(all_achievements),
        'total_xp_from_achievements': total_xp,
    }

    # Include locked achievements with progress if requested
    if include_locked:
        locked = []
        for achievement in all_achievements:
            if achievement['id'] not in unlocked_ids:
                # Calculate progress toward this achievement
                progress = await _calculate_achievement_progress(user_id, achievement)

                locked.append({
                    'achievement_key': achievement['achievement_key'],
                    'name': achievement['name'],
                    'description': achievement['description'],
                    'icon': achievement['icon'],
                    'category': achievement['category'],
                    'tier': achievement['tier'],
                    'xp_reward': achievement['xp_reward'],
                    'progress': progress,
                })

        # Sort by progress (closest to completion first)
        locked.sort(key=lambda x: x['progress']['percentage'], reverse=True)
        result['locked'] = locked

    return result


async def get_achievement_recommendations(user_id: str, limit: int = 3) -> List[Dict]:
    """
    Get achievement recommendations (closest to completion)

    Args:
        user_id: User's Telegram ID
        limit: Number of recommendations to return

    Returns:
        List of achievements close to completion with progress
    """
    # Get all achievements with progress
    achievements_data = await get_user_achievements(user_id, include_locked=True)

    if 'locked' not in achievements_data:
        return []

    # Filter to achievements with >50% progress
    close_to_completion = [
        ach for ach in achievements_data['locked']
        if ach['progress']['percentage'] >= 50
    ]

    # Return top N
    return close_to_completion[:limit]


# ============================================
# Helper Functions for Achievement Criteria
# ============================================

async def _check_completion_count(user_id: str, criteria: Dict, context: Dict) -> bool:
    """Check if user has completed enough activities"""
    required_count = criteria['value']
    domain = criteria.get('domain', 'any')

    # Get all XP transactions as proxy for completions
    transactions = mock_store.get_xp_transactions(user_id)

    if domain == 'any':
        return len(transactions) >= required_count
    else:
        # Filter by domain
        domain_transactions = [t for t in transactions if t['source_type'] == domain]
        return len(domain_transactions) >= required_count


async def _check_streak_achievement(user_id: str, criteria: Dict, context: Dict) -> bool:
    """Check if user has achieved required streak"""
    required_streak = criteria['value']
    domain = criteria.get('domain', 'any')

    # Get user's streaks
    streaks = mock_store.get_all_user_streaks(user_id)

    if domain == 'any':
        # Check if ANY streak meets the requirement
        return any(s['current_streak'] >= required_streak for s in streaks)
    else:
        # Check specific domain
        domain_streaks = [s for s in streaks if s['streak_type'] == domain]
        return any(s['current_streak'] >= required_streak for s in domain_streaks)


async def _check_perfect_period(user_id: str, criteria: Dict, context: Dict) -> bool:
    """Check if user had perfect completion for N days"""
    required_days = criteria['value']

    # This would require tracking daily completion rates
    # For now, return False (will implement when we add completion tracking)
    # TODO: Implement with reminder_completions table
    return False


async def _check_domain_count(user_id: str, criteria: Dict, context: Dict) -> bool:
    """Check domain-specific completion count"""
    required_count = criteria['value']
    domain = criteria['domain']

    # Get transactions for this domain
    transactions = mock_store.get_xp_transactions(user_id)
    domain_transactions = [t for t in transactions if t['source_type'] == domain]

    return len(domain_transactions) >= required_count


async def _check_level_milestone(user_id: str, criteria: Dict, context: Dict) -> bool:
    """Check if user reached level milestone"""
    required_level = criteria['value']

    # Get user's current level
    xp_data = mock_store.get_user_xp_data(user_id)
    current_level = xp_data['current_level']

    return current_level >= required_level


async def _check_xp_milestone(user_id: str, criteria: Dict, context: Dict) -> bool:
    """Check if user reached total XP milestone"""
    required_xp = criteria['value']

    # Get user's total XP
    xp_data = mock_store.get_user_xp_data(user_id)
    total_xp = xp_data['total_xp']

    return total_xp >= required_xp


async def _check_recovery_achievement(user_id: str, criteria: Dict, context: Dict) -> bool:
    """Check recovery achievements (bouncing back after drop)"""
    # This requires historical completion rate tracking
    # TODO: Implement when we have completion history
    return False


async def _check_streak_recovery(user_id: str, criteria: Dict, context: Dict) -> bool:
    """Check if user started new streak after breaking one"""
    required_new_streak = criteria['value']

    # Get all streaks
    streaks = mock_store.get_all_user_streaks(user_id)

    # Check if any streak has current > 0 and best > current (meaning they broke a streak)
    for streak in streaks:
        if streak['best_streak'] > streak['current_streak'] and streak['current_streak'] >= required_new_streak:
            return True

    return False


async def _check_sustained_effort(user_id: str, criteria: Dict, context: Dict) -> bool:
    """Check sustained completion rate over time"""
    # This requires historical completion tracking
    # TODO: Implement when we have daily completion data
    return False


async def _calculate_achievement_progress(user_id: str, achievement: Dict) -> Dict:
    """
    Calculate progress toward an achievement

    Returns:
        {
            'current': int,
            'required': int,
            'percentage': int,
            'description': str
        }
    """
    criteria = achievement['criteria']
    criteria_type = criteria['type']

    current = 0
    required = criteria.get('value', 0)

    if criteria_type == 'completion_count':
        transactions = mock_store.get_xp_transactions(user_id)
        domain = criteria.get('domain', 'any')
        if domain == 'any':
            current = len(transactions)
        else:
            current = len([t for t in transactions if t['source_type'] == domain])

    elif criteria_type == 'streak':
        streaks = mock_store.get_all_user_streaks(user_id)
        domain = criteria.get('domain', 'any')
        if domain == 'any':
            current = max((s['current_streak'] for s in streaks), default=0)
        else:
            domain_streaks = [s for s in streaks if s['streak_type'] == domain]
            current = max((s['current_streak'] for s in domain_streaks), default=0)

    elif criteria_type == 'domain_count':
        transactions = mock_store.get_xp_transactions(user_id)
        domain = criteria['domain']
        current = len([t for t in transactions if t['source_type'] == domain])

    elif criteria_type == 'level':
        xp_data = mock_store.get_user_xp_data(user_id)
        current = xp_data['current_level']

    elif criteria_type == 'total_xp':
        xp_data = mock_store.get_user_xp_data(user_id)
        current = xp_data['total_xp']

    elif criteria_type in ['perfect_period', 'recovery', 'streak_recovery', 'sustained_effort']:
        # These require more complex tracking
        current = 0
        required = 1

    percentage = min(100, int((current / required * 100)) if required > 0 else 0)

    return {
        'current': current,
        'required': required,
        'percentage': percentage,
        'description': f"{current}/{required}"
    }


def format_achievement_display(achievements_data: Dict) -> str:
    """
    Format achievements for Telegram display

    Args:
        achievements_data: Output from get_user_achievements()

    Returns:
        Formatted string for display
    """
    unlocked = achievements_data['unlocked']
    total_unlocked = achievements_data['total_unlocked']
    total_achievements = achievements_data['total_achievements']
    total_xp = achievements_data['total_xp_from_achievements']

    if total_unlocked == 0:
        return "🏆 No achievements unlocked yet. Keep tracking your health activities! 💪"

    lines = [
        f"🏆 YOUR ACHIEVEMENTS ({total_unlocked}/{total_achievements})",
        f"⭐ Total XP from achievements: {total_xp}\n"
    ]

    # Group by tier
    by_tier = {'platinum': [], 'gold': [], 'silver': [], 'bronze': []}
    for ach in unlocked:
        tier = ach['tier']
        if tier in by_tier:
            by_tier[tier].append(ach)

    # Display by tier
    tier_emoji = {
        'platinum': '💫',
        'gold': '🥇',
        'silver': '🥈',
        'bronze': '🥉'
    }

    for tier in ['platinum', 'gold', 'silver', 'bronze']:
        tier_achievements = by_tier[tier]
        if tier_achievements:
            lines.append(f"{tier_emoji[tier]} {tier.upper()}")
            for ach in tier_achievements:
                lines.append(f"{ach['icon']} {ach['name']} (+{ach['xp_reward']} XP)")
            lines.append("")

    return "\n".join(lines)


def format_achievement_unlock_message(achievement: Dict) -> str:
    """
    Format achievement unlock message for celebration

    Args:
        achievement: Achievement data from check_and_award_achievements()

    Returns:
        Formatted celebration message
    """
    tier_emoji = {
        'platinum': '💫',
        'gold': '🥇',
        'silver': '🥈',
        'bronze': '🥉'
    }

    tier_symbol = tier_emoji.get(achievement['tier'], '🏆')

    return f"""🎉 ACHIEVEMENT UNLOCKED! 🎉

{tier_symbol} {achievement['icon']} {achievement['name']} {tier_symbol}

{achievement['description']}

⭐ +{achievement['xp_reward']} XP Bonus!

Keep up the amazing work! 💪"""
