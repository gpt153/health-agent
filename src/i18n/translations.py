"""
Sleep quiz translations for multi-language support.

Uses simple dictionary approach for MVP. For production, consider
migrating to babel/gettext with .po/.mo files.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Translation dictionaries: language_code -> {key: translated_string}
TRANSLATIONS: Dict[str, Dict[str, Any]] = {
    "en": {
        # Quiz questions
        "quiz_welcome": "😴 **Good morning! Let's log your sleep**\n\nThis takes about 60 seconds.\n\nReady? Let's start!",
        "q1_bedtime": "**Q1/8: What time did you get into bed?**\n\nUse ⬆️⬇️ to adjust time",
        "q2_latency": "**Q2/8: How long did it take you to fall asleep?**",
        "q3_wake_time": "**Q3/8: What time did you wake up this morning?**\n\nUse ⬆️⬇️ to adjust time",
        "q4_wakings": "**Q4/8: Did you wake up during the night?**",
        "q5_quality": "**Q5/8: How would you rate your sleep quality?**\n\n😫 1-2 = Terrible\n😐 5-6 = Okay\n😊 9-10 = Excellent",
        "q6_phone": "**Q6/8: Did you use your phone/screen while in bed?**",
        "q6_duration": "**For how long?**",
        "q7_disruptions": "**Q7/8: What disrupted your sleep?** (Select all that apply)",
        "q8_alertness": "**Q8/8: How tired/alert do you feel RIGHT NOW?**\n\n😴 1-2 = Exhausted\n😐 5-6 = Normal\n⚡ 9-10 = Wide awake",

        # Button labels
        "btn_confirm": "✅ Confirm",
        "btn_yes": "✅ Yes",
        "btn_no": "❌ No",
        "btn_done": "✅ Done",
        "latency_less_15": "Less than 15 min",
        "latency_15_30": "15-30 min",
        "latency_30_60": "30-60 min",
        "latency_60_plus": "More than 1 hour",
        "wakings_no": "No",
        "wakings_1_2": "Yes, 1-2 times",
        "wakings_3_plus": "Yes, 3+ times",
        "phone_dur_less_15": "< 15 min",
        "phone_dur_15_30": "15-30 min",
        "phone_dur_30_60": "30-60 min",
        "phone_dur_60_plus": "1+ hour",
        "disruption_noise": "🔊 Noise",
        "disruption_light": "💡 Light",
        "disruption_temp": "🌡️ Temperature",
        "disruption_stress": "😰 Stress/worry",
        "disruption_dream": "😱 Bad dream",
        "disruption_pain": "🤕 Pain",

        # Confirmations
        "confirmed_latency": "✅ Sleep latency: {minutes} minutes",
        "confirmed_wakings": "✅ Night wakings: {count} times",
        "confirmed_quality": "✅ Quality rating: {emoji} {rating}/10",
        "confirmed_phone_no": "✅ Noted: No phone usage",
        "confirmed_phone_duration": "✅ Phone usage: {minutes} minutes",

        # Summary
        "summary_title": "✅ **Sleep Logged!**",
        "summary_bedtime": "🛏️ **Bedtime:** {time}",
        "summary_latency": "😴 **Fell asleep:** {minutes} min",
        "summary_wake": "⏰ **Woke up:** {time}",
        "summary_total": "⏱️ **Total sleep:** {hours}h {minutes}m",
        "summary_quality": "🌙 **Quality:** {emoji} {rating}/10",
        "summary_phone": "📱 **Phone usage:** {usage}",
        "summary_alertness": "😌 **Alertness:** {rating}/10",
        "summary_tip": "💡 **Tip:** You got {hours}h {minutes}m of sleep. Aim for 8-10h for optimal health!",

        # Settings
        "settings_title": "⚙️ **Sleep Quiz Settings**",
        "settings_enabled": "Quiz Status: {status}",
        "settings_time": "Scheduled Time: {time} ({timezone})",
        "settings_language": "Language: {language}",
        "settings_prompt": "What would you like to change?",
        "btn_toggle_quiz": "{icon} {action} Daily Quiz",
        "btn_change_time": "🕐 Change Time",
        "btn_change_language": "🌐 Change Language",
        "btn_view_patterns": "📊 View Patterns",
        "btn_back": "◀️ Back",
        "settings_updated": "✅ Settings updated!",

        # Cancel
        "quiz_cancelled": "Sleep quiz cancelled. You can start again with /sleep_quiz",
    },

    "sv": {
        # Swedish translations
        "quiz_welcome": "😴 **God morgon! Låt oss logga din sömn**\n\nDetta tar ungefär 60 sekunder.\n\nRedo? Låt oss börja!",
        "q1_bedtime": "**F1/8: Vilken tid gick du till sängs?**\n\nAnvänd ⬆️⬇️ för att justera tiden",
        "q2_latency": "**F2/8: Hur lång tid tog det att somna?**",
        "q3_wake_time": "**F3/8: Vilken tid vaknade du i morse?**\n\nAnvänd ⬆️⬇️ för att justera tiden",
        "q4_wakings": "**F4/8: Vaknade du under natten?**",
        "q5_quality": "**F5/8: Hur skulle du bedöma din sömnkvalitet?**\n\n😫 1-2 = Fruktansvärt\n😐 5-6 = Okej\n😊 9-10 = Utmärkt",
        "q6_phone": "**F6/8: Använde du telefon/skärm i sängen?**",
        "q6_duration": "**Hur länge?**",
        "q7_disruptions": "**F7/8: Vad störde din sömn?** (Välj alla som gäller)",
        "q8_alertness": "**F8/8: Hur trött/pigg känner du dig JUST NU?**\n\n😴 1-2 = Utmattad\n😐 5-6 = Normal\n⚡ 9-10 = Klarvaken",

        "btn_confirm": "✅ Bekräfta",
        "btn_yes": "✅ Ja",
        "btn_no": "❌ Nej",
        "btn_done": "✅ Klar",
        "latency_less_15": "Mindre än 15 min",
        "latency_15_30": "15-30 min",
        "latency_30_60": "30-60 min",
        "latency_60_plus": "Mer än 1 timme",
        "wakings_no": "Nej",
        "wakings_1_2": "Ja, 1-2 gånger",
        "wakings_3_plus": "Ja, 3+ gånger",
        "phone_dur_less_15": "< 15 min",
        "phone_dur_15_30": "15-30 min",
        "phone_dur_30_60": "30-60 min",
        "phone_dur_60_plus": "1+ timme",
        "disruption_noise": "🔊 Ljud",
        "disruption_light": "💡 Ljus",
        "disruption_temp": "🌡️ Temperatur",
        "disruption_stress": "😰 Stress/oro",
        "disruption_dream": "😱 Mardröm",
        "disruption_pain": "🤕 Smärta",

        "confirmed_latency": "✅ Insomning: {minutes} minuter",
        "confirmed_wakings": "✅ Nattliga uppvaknanden: {count} gånger",
        "confirmed_quality": "✅ Kvalitetsbetyg: {emoji} {rating}/10",
        "confirmed_phone_no": "✅ Noterat: Ingen telefonanvändning",
        "confirmed_phone_duration": "✅ Telefonanvändning: {minutes} minuter",

        "summary_title": "✅ **Sömn Loggad!**",
        "summary_bedtime": "🛏️ **Sänggående:** {time}",
        "summary_latency": "😴 **Somnade:** {minutes} min",
        "summary_wake": "⏰ **Vaknade:** {time}",
        "summary_total": "⏱️ **Total sömn:** {hours}h {minutes}m",
        "summary_quality": "🌙 **Kvalitet:** {emoji} {rating}/10",
        "summary_phone": "📱 **Telefonanvändning:** {usage}",
        "summary_alertness": "😌 **Pigghet:** {rating}/10",
        "summary_tip": "💡 **Tips:** Du sov {hours}h {minutes}m. Sikta på 8-10h för optimal hälsa!",

        "settings_title": "⚙️ **Inställningar för Sömnquiz**",
        "settings_enabled": "Status: {status}",
        "settings_time": "Schemalagd tid: {time} ({timezone})",
        "settings_language": "Språk: {language}",
        "settings_prompt": "Vad vill du ändra?",
        "btn_toggle_quiz": "{icon} {action} Dagligt Quiz",
        "btn_change_time": "🕐 Ändra Tid",
        "btn_change_language": "🌐 Ändra Språk",
        "btn_view_patterns": "📊 Visa Mönster",
        "btn_back": "◀️ Tillbaka",
        "settings_updated": "✅ Inställningar uppdaterade!",

        "quiz_cancelled": "Sömnquiz avbrutet. Du kan starta igen med /sleep_quiz",
    },

    "es": {
        # Spanish translations
        "quiz_welcome": "😴 **¡Buenos días! Registremos tu sueño**\n\nEsto toma unos 60 segundos.\n\n¿Listo? ¡Empecemos!",
        "q1_bedtime": "**P1/8: ¿A qué hora te acostaste?**\n\nUsa ⬆️⬇️ para ajustar la hora",
        "q2_latency": "**P2/8: ¿Cuánto tiempo tardaste en dormirte?**",
        "q3_wake_time": "**P3/8: ¿A qué hora te despertaste esta mañana?**\n\nUsa ⬆️⬇️ para ajustar la hora",
        "q4_wakings": "**P4/8: ¿Te despertaste durante la noche?**",
        "q5_quality": "**P5/8: ¿Cómo calificarías la calidad de tu sueño?**\n\n😫 1-2 = Terrible\n😐 5-6 = Regular\n😊 9-10 = Excelente",
        "q6_phone": "**P6/8: ¿Usaste tu teléfono/pantalla en la cama?**",
        "q6_duration": "**¿Por cuánto tiempo?**",
        "q7_disruptions": "**P7/8: ¿Qué interrumpió tu sueño?** (Selecciona todas las que apliquen)",
        "q8_alertness": "**P8/8: ¿Qué tan cansado/alerta te sientes AHORA MISMO?**\n\n😴 1-2 = Agotado\n😐 5-6 = Normal\n⚡ 9-10 = Muy despierto",

        "btn_confirm": "✅ Confirmar",
        "btn_yes": "✅ Sí",
        "btn_no": "❌ No",
        "btn_done": "✅ Listo",
        "latency_less_15": "Menos de 15 min",
        "latency_15_30": "15-30 min",
        "latency_30_60": "30-60 min",
        "latency_60_plus": "Más de 1 hora",
        "wakings_no": "No",
        "wakings_1_2": "Sí, 1-2 veces",
        "wakings_3_plus": "Sí, 3+ veces",
        "phone_dur_less_15": "< 15 min",
        "phone_dur_15_30": "15-30 min",
        "phone_dur_30_60": "30-60 min",
        "phone_dur_60_plus": "1+ hora",
        "disruption_noise": "🔊 Ruido",
        "disruption_light": "💡 Luz",
        "disruption_temp": "🌡️ Temperatura",
        "disruption_stress": "😰 Estrés/preocupación",
        "disruption_dream": "😱 Pesadilla",
        "disruption_pain": "🤕 Dolor",

        "confirmed_latency": "✅ Latencia de sueño: {minutes} minutos",
        "confirmed_wakings": "✅ Despertares nocturnos: {count} veces",
        "confirmed_quality": "✅ Calificación de calidad: {emoji} {rating}/10",
        "confirmed_phone_no": "✅ Anotado: Sin uso de teléfono",
        "confirmed_phone_duration": "✅ Uso de teléfono: {minutes} minutos",

        "summary_title": "✅ **¡Sueño Registrado!**",
        "summary_bedtime": "🛏️ **Hora de acostarse:** {time}",
        "summary_latency": "😴 **Te dormiste:** {minutes} min",
        "summary_wake": "⏰ **Te despertaste:** {time}",
        "summary_total": "⏱️ **Sueño total:** {hours}h {minutes}m",
        "summary_quality": "🌙 **Calidad:** {emoji} {rating}/10",
        "summary_phone": "📱 **Uso de teléfono:** {usage}",
        "summary_alertness": "😌 **Alerta:** {rating}/10",
        "summary_tip": "💡 **Consejo:** Dormiste {hours}h {minutes}m. ¡Apunta a 8-10h para una salud óptima!",

        "settings_title": "⚙️ **Configuración del Quiz de Sueño**",
        "settings_enabled": "Estado: {status}",
        "settings_time": "Hora programada: {time} ({timezone})",
        "settings_language": "Idioma: {language}",
        "settings_prompt": "¿Qué te gustaría cambiar?",
        "btn_toggle_quiz": "{icon} {action} Quiz Diario",
        "btn_change_time": "🕐 Cambiar Hora",
        "btn_change_language": "🌐 Cambiar Idioma",
        "btn_view_patterns": "📊 Ver Patrones",
        "btn_back": "◀️ Atrás",
        "settings_updated": "✅ ¡Configuración actualizada!",

        "quiz_cancelled": "Quiz de sueño cancelado. Puedes empezar de nuevo con /sleep_quiz",
    },
}


def get_user_language(telegram_user) -> str:
    """
    Detect user's language from Telegram user object.

    Args:
        telegram_user: Telegram User object with language_code attribute

    Returns:
        Language code (e.g., 'en', 'sv', 'es'). Defaults to 'en' if unsupported.
    """
    if not telegram_user or not hasattr(telegram_user, 'language_code'):
        return 'en'

    lang_code = telegram_user.language_code or 'en'

    # Return language if we have translations, else English
    if lang_code in TRANSLATIONS:
        return lang_code

    logger.info(f"Unsupported language '{lang_code}', falling back to English")
    return 'en'


def t(key: str, lang: str = 'en', **kwargs) -> str:
    """
    Translate a key to the specified language with optional formatting.

    Args:
        key: Translation key (e.g., 'quiz_welcome', 'q1_bedtime')
        lang: Language code (defaults to 'en')
        **kwargs: Format arguments for string formatting

    Returns:
        Translated and formatted string. Falls back to English if key not found.

    Examples:
        t('quiz_welcome', lang='sv')
        t('confirmed_latency', lang='es', minutes=15)
        t('summary_quality', lang='en', emoji='😊', rating=9)
    """
    # Get translation dictionary for language (fallback to English)
    lang_dict = TRANSLATIONS.get(lang, TRANSLATIONS['en'])

    # Get translated string (fallback to English key if not found)
    translated = lang_dict.get(key, TRANSLATIONS['en'].get(key, f"[MISSING: {key}]"))

    # Format with kwargs if provided
    if kwargs:
        try:
            return translated.format(**kwargs)
        except KeyError as e:
            logger.error(f"Translation formatting error for key '{key}': {e}")
            return translated

    return translated


def get_supported_languages() -> list[str]:
    """Return list of supported language codes"""
    return list(TRANSLATIONS.keys())
