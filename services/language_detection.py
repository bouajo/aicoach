"""
Service for language detection using DeepSeek.
"""

import logging
from typing import Dict, Any
from deepseek_agent import call_deepseek

logger = logging.getLogger(__name__)

LANGUAGE_INFO = {
    "fr": {
        "language_code": "fr",
        "language_name": "French",
        "is_rtl": False,
        "native_name": "Français"
    },
    "en": {
        "language_code": "en",
        "language_name": "English",
        "is_rtl": False,
        "native_name": "English"
    },
    "es": {
        "language_code": "es",
        "language_name": "Spanish",
        "is_rtl": False,
        "native_name": "Español"
    },
    "ar": {
        "language_code": "ar",
        "language_name": "Arabic",
        "is_rtl": True,
        "native_name": "العربية"
    },
    "it": {
        "language_code": "it",
        "language_name": "Italian",
        "is_rtl": False,
        "native_name": "Italiano"
    }
}

async def detect_language(text: str) -> Dict[str, Any]:
    """
    Detect the language of a text using DeepSeek.
    
    Args:
        text: Text to analyze
        
    Returns:
        Dict with language information
    """
    try:
        system_prompt = """
        You are a language detection expert. Analyze the following text and determine its language.
        Respond ONLY with the 2-letter language code (en, fr, es, ar, it).
        If unsure or if the language is not in the list, respond with 'en'.
        """
        
        response = await call_deepseek(
            system_prompt=system_prompt,
            user_messages=[{"role": "user", "content": text}],
            temperature=0.1
        )
        
        # Clean up response and get language code
        lang_code = response.strip().lower()[:2]
        
        # Get language info or default to English
        return LANGUAGE_INFO.get(lang_code, LANGUAGE_INFO["en"])
        
    except Exception as e:
        logger.error(f"Error detecting language: {e}", exc_info=True)
        return LANGUAGE_INFO["en"]

async def get_language_details(text: str) -> Dict[str, Any]:
    """
    Get detailed language information for the given text.
    
    Args:
        text: Text to analyze
        
    Returns:
        Dictionary containing language details:
        - language_name: Full name of the language
        - language_code: ISO 639-1 two-letter code
        - confidence: Detection confidence (0-1)
        - is_rtl: Whether it's a right-to-left language
    """
    try:
        response = await call_deepseek(
            system_prompt=LANGUAGE_DETECTION_PROMPT.format(text=text),
            user_messages=[],
            temperature=0.1
        )
        
        result = json.loads(response)
        return result
        
    except Exception as e:
        logger.error(f"Error getting language details: {e}", exc_info=True)
        return {
            "language_name": "English",
            "language_code": "en",
            "confidence": 1.0,
            "is_rtl": False
        }
