"""Default markdown templates for user memory files"""

PROFILE_TEMPLATE = """# User Profile

## Physical Stats
- Age:
- Height (cm):
- Current Weight (kg):
- Target Weight (kg):

## Goals
- Primary Goal:
- Timeline:

## Notes
"""

PREFERENCES_TEMPLATE = """# Communication Preferences

## Style
- Brevity: medium  # brief, medium, detailed
- Tone: friendly  # friendly, formal, casual
- Humor: yes  # yes, no
- Coaching Style: supportive  # supportive, analytical, tough_love

## Features
- Daily Summary: no
- Proactive Check-ins: no
- Timezone: UTC  # IANA timezone (e.g., America/New_York, Europe/London, Asia/Tokyo)

## Notes
"""

PATTERNS_TEMPLATE = """# Behavioral Patterns

## Observed Patterns
(This will be updated automatically based on your interactions)

## Food Preferences
- Likes:
- Dislikes:
- Allergies/Restrictions:

## Exercise Patterns
- Typical workout days:
- Preferred activities:

## Notes
"""

FOOD_HISTORY_TEMPLATE = """# Recent Food History

(Your recent food logs will appear here)
"""

VISUAL_PATTERNS_TEMPLATE = """# Visual Pattern Memory

## Known Foods & Items
(When you teach me what something looks like, I'll remember it here)

### Examples:
- **My protein shaker**: Clear plastic bottle with white liquid, contains 30g whey protein, ~150 calories
- **My meal prep containers**: Black plastic containers with white lids, usually contain chicken and rice

## Notes
This helps me recognize your specific foods and containers better over time.
"""
