"""Direct answer extraction from patterns.md for common questions"""
import re
from typing import Optional


def extract_direct_answer(query: str, patterns_content: str) -> Optional[str]:
    """
    Extract direct answers from patterns.md for common questions
    Returns the answer as a string to inject into the prompt, or None
    """
    query_lower = query.lower()

    # Training days question
    if any(word in query_lower for word in ['gymmar', 'träna', 'training', 'workout']):
        match = re.search(r'Training days?: ([^\n]+)', patterns_content, re.IGNORECASE)
        if match:
            return f"DIRECT ANSWER FROM YOUR PATTERNS: {match.group(1)}"

    # Sleep/wake time questions
    if any(word in query_lower for word in ['sömn', 'sleep', 'vaknar', 'wake', 'sänggåendetid', 'bedtime', 'lägger mig', 'lägger dig']):
        answers = []
        wake_match = re.search(r'Vaknar kl (\d+:\d+)|wake.*?(\d+:\d+)', patterns_content, re.IGNORECASE)
        if wake_match:
            time = wake_match.group(1) or wake_match.group(2)
            answers.append(f"Du vaknar kl {time}")

        bed_match = re.search(r'Sänggåendetid kl (\d+:\d+)|[Bb]edtime.*?(\d+:\d+)', patterns_content, re.IGNORECASE)
        if bed_match:
            time = bed_match.group(1) or bed_match.group(2)
            answers.append(f"Sänggåendetid kl {time}")

        if answers:
            return "DIRECT ANSWER FROM YOUR PATTERNS: " + "; ".join(answers)

    # Coffee consumption questions
    if any(word in query_lower for word in ['kaffe', 'coffee']):
        match = re.search(r'(?:kaffe|coffee).*?(\d+)\s*(?:koppar|cups?)', patterns_content, re.IGNORECASE)
        if match:
            return f"DIRECT ANSWER FROM YOUR PATTERNS: Du dricker {match.group(1)} koppar kaffe"
        # If no specific amount found, check for any mention
        if 'kaffe' in patterns_content.lower() or 'coffee' in patterns_content.lower():
            # Extract any line mentioning coffee
            for line in patterns_content.split('\n'):
                if 'kaffe' in line.lower() or 'coffee' in line.lower():
                    return f"DIRECT ANSWER FROM YOUR PATTERNS: {line.strip()}"

    # Injection schedule questions
    if any(word in query_lower for word in ['injektion', 'injection', 'sprut']):
        # Extract injection schedule section
        match = re.search(r'## Injection Schedule(.*?)(?=\n##|\Z)', patterns_content, re.DOTALL | re.IGNORECASE)
        if match:
            schedule = match.group(1).strip()
            # Simplify for today
            from datetime import datetime
            weekday = datetime.now().strftime('%A')  # Monday, Tuesday, etc.

            return f"DIRECT ANSWER FROM YOUR INJECTION SCHEDULE:\n{schedule}\n\nToday is {weekday}."

    return None
