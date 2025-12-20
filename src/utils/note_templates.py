"""Note templates for reminder completions"""


def get_note_templates(reminder_message: str) -> list[str]:
    """
    Get context-aware note templates based on reminder type

    Args:
        reminder_message: The reminder's message text

    Returns:
        List of quick note template strings
    """
    message_lower = reminder_message.lower()

    # Medication/supplements
    if any(kw in message_lower for kw in ['medication', 'medicine', 'pill', 'supplement', 'vitamin', 'drug']):
        return [
            "✅ No issues",
            "😵 Felt dizzy",
            "🤢 Nauseous",
            "😴 Drowsy",
            "⚡ Energized",
            "💊 Side effects noted"
        ]

    # Blood pressure
    if any(kw in message_lower for kw in ['blood pressure', 'bp', 'pressure']):
        return [
            "120/80 - Normal",
            "130/85 - Slightly elevated",
            "140/90 - High",
            "110/70 - Low",
            "📊 Recorded in log"
        ]

    # Exercise/fitness
    if any(kw in message_lower for kw in ['exercise', 'workout', 'walk', 'run', 'gym', 'yoga', 'fitness']):
        return [
            "💪 Great workout!",
            "😊 Easy session",
            "😅 Tough but finished",
            "🤕 Modified - injury",
            "⏱️ 30 min",
            "⏱️ 60 min"
        ]

    # Water/hydration
    if any(kw in message_lower for kw in ['water', 'hydrat', 'drink']):
        return [
            "💧 8 glasses",
            "💧 4 glasses",
            "💧 2 glasses",
            "☕ Coffee counted",
            "🥤 With electrolytes"
        ]

    # Sleep
    if any(kw in message_lower for kw in ['sleep', 'bed', 'rest']):
        return [
            "😴 7-8 hours",
            "😴 6-7 hours",
            "😴 5-6 hours",
            "😴 <5 hours",
            "😊 Well rested",
            "😫 Poor quality"
        ]

    # Generic templates
    return [
        "✅ Completed as planned",
        "⏰ Did it early",
        "⏰ Did it late",
        "💯 Felt great",
        "😊 Good enough"
    ]
