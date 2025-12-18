"""Voice transcription using OpenAI Whisper"""
import logging
from pathlib import Path
import openai
from src.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)


async def transcribe_voice(voice_file_path: str) -> str:
    """
    Transcribe voice note using OpenAI Whisper API

    Args:
        voice_file_path: Path to the voice file (OGG format from Telegram)

    Returns:
        Transcribed text

    Raises:
        Exception: If transcription fails
    """
    try:
        logger.info(f"Transcribing voice file: {voice_file_path}")

        with open(voice_file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )

        logger.info(f"Transcription successful: {transcript[:100]}...")
        return transcript

    except Exception as e:
        logger.error(f"Voice transcription failed: {e}", exc_info=True)
        raise Exception(f"Failed to transcribe voice note: {str(e)}")
