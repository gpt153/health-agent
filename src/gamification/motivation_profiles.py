"""
Motivation Profile System - Phase 3: Adaptive Intelligence

Detects user motivation styles and adapts messaging accordingly.

Based on behavioral psychology research:
- Achiever: Goal-oriented, competitive, milestone-focused
- Socializer: Community-driven, collaborative, sharing-oriented
- Explorer: Curious, variety-seeking, discovery-focused
- Completionist: Checklist-driven, systematic, progress-tracking

Detection uses interaction patterns, preferences, and activity history.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from src.gamification import mock_store
from src.gamification.xp_system import get_xp_history
from src.gamification.streak_system import get_user_streaks
from src.gamification.achievement_system import get_user_achievements

logger = logging.getLogger(__name__)


@dataclass
class MotivationProfile:
    """User's motivation profile"""
    user_id: str
    primary_type: str  # achiever, socializer, explorer, completionist
    secondary_type: Optional[str]  # Optional secondary motivation
    confidence: float  # 0.0-1.0 confidence in detection
    traits: Dict[str, float]  # All trait scores (achiever: 0.75, socializer: 0.3, etc.)
    detected_at: datetime
    last_updated: datetime


# Motivation type descriptions
MOTIVATION_TYPES = {
    'achiever': {
        'name': 'Achiever',
        'description': 'Goal-oriented and competitive, motivated by milestones and leveling up',
        'emoji': '🏆',
        'traits': [
            'Frequently checks XP and level status',
            'Completes activities to reach goals',
            'Asks about progress and rankings',
            'Achievement-focused language'
        ]
    },
    'socializer': {
        'name': 'Socializer',
        'description': 'Community-driven and collaborative, motivated by shared experiences',
        'emoji': '🤝',
        'traits': [
            'Shares progress with others',
            'Interested in group features',
            'Asks about other users',
            'Collaborative language'
        ]
    },
    'explorer': {
        'name': 'Explorer',
        'description': 'Curious and variety-seeking, motivated by discovering new features',
        'emoji': '🔍',
        'traits': [
            'Tries different health activities',
            'Asks about new features',
            'Experiments with categories',
            'Curious questions about system'
        ]
    },
    'completionist': {
        'name': 'Completionist',
        'description': 'Checklist-driven and systematic, motivated by completing all tasks',
        'emoji': '✅',
        'traits': [
            'Maintains consistent streaks',
            'Tracks all activities',
            'Asks about completion status',
            'Methodical activity patterns'
        ]
    }
}


async def detect_motivation_profile(user_id: str) -> MotivationProfile:
    """
    Detect user's motivation profile based on behavior patterns

    Analyzes:
    - Activity patterns (consistency, variety)
    - Feature usage (what they interact with)
    - Query patterns (what they ask about)
    - Achievement progress

    Args:
        user_id: Telegram user ID

    Returns:
        MotivationProfile with primary/secondary types and confidence
    """
    try:
        # Get user data
        transactions = mock_store.get_xp_transactions(user_id, limit=200)
        streaks = await get_user_streaks(user_id)
        achievements_data = await get_user_achievements(user_id)

        # Calculate trait scores
        trait_scores = {
            'achiever': 0.0,
            'socializer': 0.0,
            'explorer': 0.0,
            'completionist': 0.0
        }

        # ACHIEVER indicators
        # - Checks XP/level frequently (would be tracked by query history)
        # - Achievement unlock rate
        # - Level progression speed
        achievement_rate = achievements_data['total_unlocked'] / max(achievements_data['total_achievements'], 1)
        trait_scores['achiever'] += achievement_rate * 0.4  # Max 0.4

        # High XP accumulation
        from src.gamification import get_user_xp
        xp_data = await get_user_xp(user_id)
        if xp_data['total_xp'] > 500:
            trait_scores['achiever'] += 0.2
        elif xp_data['total_xp'] > 200:
            trait_scores['achiever'] += 0.1

        # SOCIALIZER indicators
        # - Would share progress (tracked in future)
        # - Asks about group features (tracked in future)
        # For now, default low score
        trait_scores['socializer'] += 0.1  # Baseline

        # EXPLORER indicators
        # - Variety of activity types
        activity_types = set(tx['source_type'] for tx in transactions)
        variety_score = len(activity_types) / 7.0  # 7 possible types
        trait_scores['explorer'] += variety_score * 0.5  # Max 0.5

        # Different streak types
        streak_types = set(s['streak_type'] for s in streaks)
        streak_variety = len(streak_types) / 7.0  # 7 possible streak types
        trait_scores['explorer'] += streak_variety * 0.3  # Max 0.3

        # COMPLETIONIST indicators
        # - Streak consistency
        if streaks:
            avg_streak = sum(s['current_streak'] for s in streaks) / len(streaks)
            if avg_streak >= 14:
                trait_scores['completionist'] += 0.4
            elif avg_streak >= 7:
                trait_scores['completionist'] += 0.2
            elif avg_streak >= 3:
                trait_scores['completionist'] += 0.1

        # Activity consistency (regular daily tracking)
        if transactions:
            # Count unique active days in last 30 days
            from datetime import date
            thirty_days_ago = date.today() - timedelta(days=30)
            recent_transactions = [
                tx for tx in transactions
                if tx['awarded_at'].date() >= thirty_days_ago
            ]
            unique_days = len(set(tx['awarded_at'].date() for tx in recent_transactions))
            consistency_rate = unique_days / 30.0
            trait_scores['completionist'] += consistency_rate * 0.4  # Max 0.4

        # Normalize scores (ensure they sum to reasonable range)
        total = sum(trait_scores.values())
        if total > 0:
            trait_scores = {k: v / total for k, v in trait_scores.items()}

        # Determine primary and secondary types
        sorted_traits = sorted(trait_scores.items(), key=lambda x: x[1], reverse=True)
        primary_type = sorted_traits[0][0]
        primary_score = sorted_traits[0][1]

        # Secondary type if score is close to primary (within 20%)
        secondary_type = None
        if len(sorted_traits) > 1:
            secondary_score = sorted_traits[1][1]
            if secondary_score >= primary_score * 0.6:  # Within 40%
                secondary_type = sorted_traits[1][0]

        # Confidence based on score separation
        confidence = min(primary_score * 2, 1.0)  # Scale to 0-1

        # If not enough data, default to balanced profile with low confidence
        if len(transactions) < 5:
            confidence = 0.3
            logger.info(f"Low activity count for {user_id}, defaulting to low confidence")

        profile = MotivationProfile(
            user_id=user_id,
            primary_type=primary_type,
            secondary_type=secondary_type,
            confidence=confidence,
            traits=trait_scores,
            detected_at=datetime.now(),
            last_updated=datetime.now()
        )

        logger.info(
            f"Detected motivation profile for {user_id}: "
            f"{primary_type} (confidence: {confidence:.2f})"
        )

        return profile

    except Exception as e:
        logger.error(f"Error detecting motivation profile: {e}", exc_info=True)
        # Return default profile
        return MotivationProfile(
            user_id=user_id,
            primary_type='achiever',  # Default
            secondary_type=None,
            confidence=0.2,
            traits={'achiever': 0.25, 'socializer': 0.25, 'explorer': 0.25, 'completionist': 0.25},
            detected_at=datetime.now(),
            last_updated=datetime.now()
        )


def get_motivational_message(
    profile: MotivationProfile,
    context: str,
    xp_earned: Optional[int] = None,
    streak_count: Optional[int] = None,
    achievement_name: Optional[str] = None
) -> str:
    """
    Generate personalized motivational message based on motivation profile

    Args:
        profile: User's motivation profile
        context: Message context (completion, milestone, encouragement)
        xp_earned: XP amount (optional)
        streak_count: Streak count (optional)
        achievement_name: Achievement name (optional)

    Returns:
        Personalized motivational message
    """
    motivation_type = profile.primary_type

    # Messages tailored to each motivation type
    messages = {
        'achiever': {
            'completion': [
                f"Great work! You earned {xp_earned} XP. Keep pushing toward your next goal! 🏆",
                f"Nice! +{xp_earned} XP brings you closer to the next level! 💪",
                f"Excellent! You're dominating your health goals! +{xp_earned} XP 🎯"
            ],
            'milestone': [
                f"🏆 Milestone reached! {streak_count}-day streak unlocked!",
                f"Achievement unlocked: {achievement_name}! You're crushing it! 🌟",
                f"New level reached! You're in the top tier now! 💫"
            ],
            'encouragement': [
                "You're so close to the next level! Keep going! 🎯",
                "Your progress is impressive! Let's hit that next milestone! 💪",
                "You're outperforming your goals! Keep the momentum! 🚀"
            ]
        },
        'socializer': {
            'completion': [
                f"Awesome! You earned {xp_earned} XP. Your commitment inspires others! 🤝",
                f"Great work! +{xp_earned} XP. Keep being an inspiration! 💙",
                f"Nice! Your consistency helps the whole community! +{xp_earned} XP ✨"
            ],
            'milestone': [
                f"Amazing! {streak_count}-day streak! Your dedication sets a great example! 🌟",
                f"You unlocked {achievement_name}! Share your success! 🎉",
                f"Incredible milestone! Your progress motivates everyone! 🤝"
            ],
            'encouragement': [
                "Your efforts make a difference! Keep it up! 💙",
                "You're setting a great example for others! 🌟",
                "Together we're building healthier habits! Keep going! 🤝"
            ]
        },
        'explorer': {
            'completion': [
                f"Interesting! You earned {xp_earned} XP from {context}. Try mixing things up! 🔍",
                f"Nice exploration! +{xp_earned} XP. Ever tried tracking something new? 🌟",
                f"Great! +{xp_earned} XP. There are more features to discover! 🗺️"
            ],
            'milestone': [
                f"You discovered a {streak_count}-day streak! What else can you explore? 🔍",
                f"Achievement unlocked: {achievement_name}! Check out other achievements! 🏆",
                f"New milestone! Want to try a different health domain? 🌟"
            ],
            'encouragement': [
                "Have you tried all the tracking categories? There's so much to explore! 🗺️",
                "Your curiosity is admirable! Keep discovering new ways to improve! 🔍",
                "Experiment with different activities - variety is great! 🌈"
            ]
        },
        'completionist': {
            'completion': [
                f"Perfect! ✅ Completed! +{xp_earned} XP. Your consistency is amazing!",
                f"Checked off! +{xp_earned} XP. You're on track with all your activities! ✅",
                f"Done! +{xp_earned} XP. Your systematic approach is paying off! 📋"
            ],
            'milestone': [
                f"✅ {streak_count}-day perfect streak! Your consistency is unmatched!",
                f"Achievement complete: {achievement_name}! Every box checked! 🎯",
                f"Milestone reached! You're systematically conquering all goals! 📊"
            ],
            'encouragement': [
                "Your consistency is impressive! Keep checking off those daily tasks! ✅",
                "You're on track! Maintain that perfect completion rate! 📋",
                "Your systematic approach is working perfectly! Keep it up! 🎯"
            ]
        }
    }

    # Get messages for motivation type
    type_messages = messages.get(motivation_type, messages['achiever'])
    context_messages = type_messages.get(context, type_messages['encouragement'])

    # Select message (for now, just use first one; could randomize)
    import random
    message = random.choice(context_messages)

    # If secondary type exists and confidence is moderate, blend messages
    if profile.secondary_type and profile.confidence < 0.7:
        # Could blend messages from both types (future enhancement)
        pass

    return message


def format_profile_display(profile: MotivationProfile) -> str:
    """
    Format motivation profile for display to user

    Args:
        profile: User's motivation profile

    Returns:
        Formatted profile description
    """
    primary_info = MOTIVATION_TYPES[profile.primary_type]
    emoji = primary_info['emoji']
    name = primary_info['name']
    description = primary_info['description']

    lines = [
        f"{emoji} **YOUR MOTIVATION PROFILE: {name}**",
        "",
        description,
        "",
        "**Your Traits:**"
    ]

    # Show trait scores
    for trait_type, score in sorted(profile.traits.items(), key=lambda x: x[1], reverse=True):
        trait_info = MOTIVATION_TYPES[trait_type]
        percentage = int(score * 100)
        bar_length = int(score * 20)
        bar = "▓" * bar_length + "░" * (20 - bar_length)
        lines.append(f"{trait_info['emoji']} {trait_info['name']}: {bar} {percentage}%")

    lines.append("")

    # Confidence indicator
    if profile.confidence >= 0.7:
        confidence_text = "High confidence - we know you well!"
    elif profile.confidence >= 0.4:
        confidence_text = "Moderate confidence - still learning about you"
    else:
        confidence_text = "Low confidence - help us understand you better by staying active!"

    lines.append(f"**Confidence:** {confidence_text}")

    lines.append("")
    lines.append("**What this means:**")

    # Add personalized insights
    if profile.primary_type == 'achiever':
        lines.append("• You're motivated by goals and milestones")
        lines.append("• We'll highlight your progress toward next level")
        lines.append("• Achievements and XP updates will keep you engaged")
    elif profile.primary_type == 'socializer':
        lines.append("• You're motivated by community and collaboration")
        lines.append("• Sharing your progress will boost your motivation")
        lines.append("• Group challenges (coming soon!) will be perfect for you")
    elif profile.primary_type == 'explorer':
        lines.append("• You're motivated by variety and discovery")
        lines.append("• We'll suggest new features to try")
        lines.append("• Experimenting with different activities will keep you engaged")
    elif profile.primary_type == 'completionist':
        lines.append("• You're motivated by consistency and completion")
        lines.append("• We'll help you maintain perfect streaks")
        lines.append("• Systematic tracking is your strength")

    if profile.secondary_type:
        secondary_info = MOTIVATION_TYPES[profile.secondary_type]
        lines.append(f"• You also have strong {secondary_info['name']} traits")

    return "\n".join(lines)


# Store motivation profiles in memory (would be database in production)
_motivation_profiles: Dict[str, MotivationProfile] = {}


async def get_or_detect_profile(user_id: str) -> MotivationProfile:
    """
    Get cached profile or detect new one

    Args:
        user_id: Telegram user ID

    Returns:
        User's motivation profile
    """
    # Check cache
    if user_id in _motivation_profiles:
        profile = _motivation_profiles[user_id]

        # Re-detect if profile is old (>7 days)
        if (datetime.now() - profile.last_updated).days > 7:
            logger.info(f"Profile for {user_id} is outdated, re-detecting")
            profile = await detect_motivation_profile(user_id)
            _motivation_profiles[user_id] = profile

        return profile

    # Detect new profile
    profile = await detect_motivation_profile(user_id)
    _motivation_profiles[user_id] = profile
    return profile


async def update_profile_from_interaction(user_id: str, interaction_type: str):
    """
    Update motivation profile based on user interaction

    Args:
        user_id: Telegram user ID
        interaction_type: Type of interaction (check_xp, ask_social, try_feature, etc.)
    """
    # This would update trait scores based on interactions
    # For now, just trigger re-detection periodically
    pass
