"""Dynamic system prompt generation based on user preferences"""


def generate_system_prompt(user_memory: dict) -> str:
    """
    Generate personalized system prompt based on user memory

    Args:
        user_memory: Dict with profile, preferences, patterns, food_history

    Returns:
        Personalized system prompt string
    """
    # Parse preferences from preferences.md (simplified parsing)
    prefs_text = user_memory.get("preferences", "")

    # Default settings
    brevity = "medium"
    tone = "friendly"
    coaching_style = "supportive"

    # TODO: Parse preferences from markdown more robustly
    if "Brevity: brief" in prefs_text:
        brevity = "brief"
    elif "Brevity: detailed" in prefs_text:
        brevity = "detailed"

    base_prompt = f"""You are an adaptive AI fitness and nutrition coach. You remember everything about each user and personalize your coaching style accordingly.

**Communication Style:**
- Brevity: {brevity} responses
- Tone: {tone} and conversational
- Coaching approach: {coaching_style}

**Your Capabilities:**
1. Analyze food photos to estimate calories and macros
2. Track custom metrics (sleep, mood, workouts, etc.)
3. Remember user goals and preferences
4. Provide personalized nutrition and fitness advice

**Context about this user:**
{user_memory.get("profile", "No profile yet")}

**Remember:** You adapt to the user's communication preferences and always maintain a helpful, motivating tone."""

    return base_prompt
