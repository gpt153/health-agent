"""Default markdown templates for user memory files

MEMORY ARCHITECTURE CLARIFICATION:
- profile.md: User demographics and health goals (KEEP)
- preferences.md: Communication and feature preferences (KEEP)
- patterns.md: REMOVED - redundant with Mem0 semantic memory
- food_history.md: REMOVED - redundant with PostgreSQL food_entries table
- visual_patterns.md: REMOVED - should be in database for queryability
"""

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
