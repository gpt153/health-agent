"""
Predefined tracker templates for common health tracking use cases.
Users can use these as starting points or create fully custom trackers.
"""
from typing import Dict, Any

TRACKER_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "period": {
        "name": "Period Tracking",
        "icon": "🩸",
        "color": "#FF6B9D",
        "category_type": "template",
        "description": "Track menstrual cycle, flow intensity, symptoms, and mood",
        "fields": {
            "flow": {
                "type": "rating",
                "label": "Flow intensity",
                "min_value": 1,
                "max_value": 5,
                "required": True,
                "description": "1=spotting, 2=light, 3=medium, 4=heavy, 5=very heavy"
            },
            "symptoms": {
                "type": "multiselect",
                "label": "Symptoms",
                "options": [
                    "cramps",
                    "headache",
                    "mood_swings",
                    "fatigue",
                    "bloating",
                    "breast_tenderness",
                    "acne",
                    "back_pain"
                ],
                "required": False
            },
            "mood": {
                "type": "rating",
                "label": "Mood",
                "min_value": 1,
                "max_value": 5,
                "required": False,
                "description": "1=very low, 3=neutral, 5=great"
            },
            "pain_level": {
                "type": "rating",
                "label": "Pain level",
                "min_value": 0,
                "max_value": 10,
                "required": False,
                "description": "0=no pain, 10=worst pain"
            }
        },
        "schedule": {
            "type": "daily",
            "time": "21:00",
            "days": [0, 1, 2, 3, 4, 5, 6],
            "message": "Time to log your period tracking! 🩸"
        }
    },

    "energy": {
        "name": "Energy Levels",
        "icon": "⚡",
        "color": "#FFD93D",
        "category_type": "template",
        "description": "Track daily energy levels and identify patterns",
        "fields": {
            "level": {
                "type": "rating",
                "label": "Energy level",
                "min_value": 1,
                "max_value": 10,
                "required": True,
                "description": "1=exhausted, 5=moderate, 10=highly energized"
            },
            "time_of_day": {
                "type": "single_select",
                "label": "Time of day",
                "options": ["morning", "midday", "afternoon", "evening", "night"],
                "required": True
            },
            "quality": {
                "type": "text",
                "label": "Notes",
                "required": False,
                "description": "Any factors affecting your energy?"
            }
        },
        "schedule": {
            "type": "daily",
            "time": "20:00",
            "days": [0, 1, 2, 3, 4, 5, 6],
            "message": "How's your energy today? ⚡"
        }
    },

    "symptoms": {
        "name": "Symptom Tracking",
        "icon": "🤒",
        "color": "#FF6B6B",
        "category_type": "template",
        "description": "Track health symptoms to identify triggers and patterns",
        "fields": {
            "symptom_type": {
                "type": "single_select",
                "label": "Symptom type",
                "options": [
                    "headache",
                    "nausea",
                    "dizziness",
                    "fatigue",
                    "digestive_issues",
                    "muscle_pain",
                    "skin_issues",
                    "other"
                ],
                "required": True
            },
            "severity": {
                "type": "rating",
                "label": "Severity",
                "min_value": 1,
                "max_value": 10,
                "required": True,
                "description": "1=mild, 5=moderate, 10=severe"
            },
            "duration": {
                "type": "duration",
                "label": "Duration",
                "required": False,
                "description": "How long did it last? (e.g., 30min, 2h)"
            },
            "triggers": {
                "type": "text",
                "label": "Possible triggers",
                "required": False,
                "description": "What might have caused it?"
            }
        }
    },

    "medication": {
        "name": "Medication Tracking",
        "icon": "💊",
        "color": "#4ECDC4",
        "category_type": "template",
        "description": "Track medication adherence and side effects",
        "fields": {
            "medication_name": {
                "type": "text",
                "label": "Medication name",
                "required": True
            },
            "dosage": {
                "type": "text",
                "label": "Dosage",
                "required": True,
                "description": "e.g., 50mg, 2 tablets"
            },
            "taken_time": {
                "type": "time",
                "label": "Time taken",
                "required": True
            },
            "taken": {
                "type": "boolean",
                "label": "Taken as prescribed?",
                "required": True
            },
            "side_effects": {
                "type": "text",
                "label": "Side effects",
                "required": False,
                "description": "Any side effects experienced?"
            }
        },
        "schedule": {
            "type": "daily",
            "time": "09:00",
            "days": [0, 1, 2, 3, 4, 5, 6],
            "message": "Don't forget your medication! 💊"
        }
    },

    "mood": {
        "name": "Mood Tracking",
        "icon": "😊",
        "color": "#95E1D3",
        "category_type": "template",
        "description": "Track daily mood and emotional well-being",
        "fields": {
            "mood_rating": {
                "type": "rating",
                "label": "Overall mood",
                "min_value": 1,
                "max_value": 10,
                "required": True,
                "description": "1=very low, 5=neutral, 10=excellent"
            },
            "emotions": {
                "type": "multiselect",
                "label": "Emotions felt",
                "options": [
                    "happy",
                    "sad",
                    "anxious",
                    "calm",
                    "stressed",
                    "motivated",
                    "frustrated",
                    "content"
                ],
                "required": False
            },
            "stress_level": {
                "type": "rating",
                "label": "Stress level",
                "min_value": 1,
                "max_value": 10,
                "required": False,
                "description": "1=very relaxed, 10=very stressed"
            },
            "notes": {
                "type": "text",
                "label": "What influenced your mood?",
                "required": False
            }
        },
        "schedule": {
            "type": "daily",
            "time": "21:00",
            "days": [0, 1, 2, 3, 4, 5, 6],
            "message": "How are you feeling today? 😊"
        }
    },

    "sleep_quality": {
        "name": "Sleep Quality",
        "icon": "😴",
        "color": "#6C5CE7",
        "category_type": "template",
        "description": "Track sleep quality and patterns (complements sleep quiz)",
        "fields": {
            "quality_rating": {
                "type": "rating",
                "label": "Sleep quality",
                "min_value": 1,
                "max_value": 10,
                "required": True,
                "description": "1=terrible, 5=okay, 10=excellent"
            },
            "refreshed": {
                "type": "boolean",
                "label": "Felt refreshed?",
                "required": True
            },
            "interruptions": {
                "type": "number",
                "label": "Times woken up",
                "min_value": 0,
                "required": False
            },
            "dreams": {
                "type": "boolean",
                "label": "Remember dreams?",
                "required": False
            },
            "notes": {
                "type": "text",
                "label": "Sleep notes",
                "required": False,
                "description": "Anything affecting your sleep?"
            }
        },
        "schedule": {
            "type": "daily",
            "time": "08:00",
            "days": [0, 1, 2, 3, 4, 5, 6],
            "message": "How did you sleep last night? 😴"
        }
    },

    "water_intake": {
        "name": "Water Intake",
        "icon": "💧",
        "color": "#3498DB",
        "category_type": "template",
        "description": "Track daily water consumption",
        "fields": {
            "amount_ml": {
                "type": "number",
                "label": "Amount (ml)",
                "min_value": 0,
                "max_value": 5000,
                "required": True,
                "unit": "ml"
            },
            "time_logged": {
                "type": "time",
                "label": "Time",
                "required": False
            }
        },
        "schedule": {
            "type": "daily",
            "time": "20:00",
            "days": [0, 1, 2, 3, 4, 5, 6],
            "message": "Track your water intake for today! 💧"
        }
    },

    "exercise": {
        "name": "Exercise Tracking",
        "icon": "🏃",
        "color": "#E74C3C",
        "category_type": "template",
        "description": "Track workouts and physical activity",
        "fields": {
            "exercise_type": {
                "type": "single_select",
                "label": "Exercise type",
                "options": [
                    "running",
                    "walking",
                    "cycling",
                    "strength_training",
                    "yoga",
                    "swimming",
                    "sports",
                    "other"
                ],
                "required": True
            },
            "duration_minutes": {
                "type": "number",
                "label": "Duration (minutes)",
                "min_value": 1,
                "max_value": 600,
                "required": True,
                "unit": "min"
            },
            "intensity": {
                "type": "rating",
                "label": "Intensity",
                "min_value": 1,
                "max_value": 10,
                "required": False,
                "description": "1=very light, 5=moderate, 10=maximum effort"
            },
            "notes": {
                "type": "text",
                "label": "Workout notes",
                "required": False
            }
        }
    }
}


def get_template(template_id: str) -> Dict[str, Any]:
    """Get a tracker template by ID"""
    return TRACKER_TEMPLATES.get(template_id)


def get_all_templates() -> Dict[str, Dict[str, Any]]:
    """Get all available tracker templates"""
    return TRACKER_TEMPLATES


def list_template_names() -> list[tuple[str, str, str]]:
    """Get list of (id, name, icon) for all templates"""
    return [
        (template_id, template["name"], template["icon"])
        for template_id, template in TRACKER_TEMPLATES.items()
    ]
