"""Unit tests for sleep quiz translations"""
import pytest
from src.i18n.translations import t, get_supported_languages, get_user_language, TRANSLATIONS


def test_english_translation():
    """Test basic English translation"""
    result = t('quiz_welcome', lang='en')
    assert '😴' in result
    assert 'Good morning' in result


def test_swedish_translation():
    """Test Swedish translation"""
    result = t('quiz_welcome', lang='sv')
    assert '😴' in result
    assert 'God morgon' in result


def test_spanish_translation():
    """Test Spanish translation"""
    result = t('quiz_welcome', lang='es')
    assert '😴' in result
    assert 'Buenos días' in result


def test_fallback_to_english():
    """Test fallback for unsupported language"""
    result = t('quiz_welcome', lang='fr')  # French not supported
    assert 'Good morning' in result  # Falls back to English


def test_missing_key_fallback():
    """Test fallback for missing translation key"""
    result = t('nonexistent_key', lang='en')
    assert '[MISSING: nonexistent_key]' in result


def test_format_arguments():
    """Test translation with format arguments"""
    result = t('confirmed_latency', lang='en', minutes=15)
    assert '15 minutes' in result


def test_format_arguments_swedish():
    """Test Swedish translation with format arguments"""
    result = t('confirmed_latency', lang='sv', minutes=15)
    assert '15 minuter' in result


def test_supported_languages():
    """Test getting list of supported languages"""
    languages = get_supported_languages()
    assert 'en' in languages
    assert 'sv' in languages
    assert 'es' in languages


def test_all_keys_present_in_all_languages():
    """Ensure all translation keys exist in all supported languages"""
    en_keys = set(TRANSLATIONS['en'].keys())

    for lang_code, translations in TRANSLATIONS.items():
        if lang_code == 'en':
            continue

        lang_keys = set(translations.keys())
        missing_keys = en_keys - lang_keys

        assert not missing_keys, f"Language '{lang_code}' is missing keys: {missing_keys}"


def test_all_translations_have_format_placeholders():
    """Ensure translations with format args have correct placeholders"""
    # Keys that require format arguments
    format_keys = {
        'confirmed_latency': ['minutes'],
        'confirmed_wakings': ['count'],
        'confirmed_quality': ['emoji', 'rating'],
        'confirmed_phone_duration': ['minutes'],
        'summary_bedtime': ['time'],
        'summary_latency': ['minutes'],
        'summary_wake': ['time'],
        'summary_total': ['hours', 'minutes'],
        'summary_quality': ['emoji', 'rating'],
        'summary_phone': ['usage'],
        'summary_alertness': ['rating'],
        'summary_tip': ['hours', 'minutes'],
    }

    for lang_code, translations in TRANSLATIONS.items():
        for key, required_args in format_keys.items():
            if key in translations:
                text = translations[key]
                for arg in required_args:
                    assert f'{{{arg}}}' in text, \
                        f"Language '{lang_code}', key '{key}' missing placeholder '{{{arg}}}'"


def test_get_user_language_with_valid_user():
    """Test language detection from valid Telegram user"""
    class MockUser:
        def __init__(self, lang):
            self.language_code = lang

    user_en = MockUser('en')
    assert get_user_language(user_en) == 'en'

    user_sv = MockUser('sv')
    assert get_user_language(user_sv) == 'sv'


def test_get_user_language_fallback():
    """Test language detection fallback to English"""
    class MockUser:
        def __init__(self, lang):
            self.language_code = lang

    user_fr = MockUser('fr')  # Unsupported language
    assert get_user_language(user_fr) == 'en'


def test_get_user_language_with_none():
    """Test language detection with None user"""
    assert get_user_language(None) == 'en'


def test_get_user_language_without_language_code():
    """Test language detection with user missing language_code"""
    class MockUser:
        pass

    user = MockUser()
    assert get_user_language(user) == 'en'
