"""
Service for language detection using DeepSeek.
"""

import logging
import json
from typing import Dict, Any
from deepseek_agent import call_deepseek

logger = logging.getLogger(__name__)

LANGUAGE_DETECTION_PROMPT = """You are a universal language detection expert. Analyze the following text and determine:
1. The language being used
2. The ISO 639-1 two-letter language code
3. The confidence level of your detection

Return your analysis as a JSON object with the following structure:
{{
    "language_name": "string",  // Full name of the language
    "language_code": "string",  // ISO 639-1 two-letter code
    "confidence": float,        // Confidence level (0-1)
    "is_rtl": boolean          // Whether it's a right-to-left language
}}

Text to analyze: {text}

Respond ONLY with the JSON object, no other text."""

async def detect_language(text: str) -> Dict[str, Any]:
    """
    Detect the language of the given text using DeepSeek.
    
    Args:
        text: Text to analyze
        
    Returns:
        Dict containing language details:
        - language_name: Full name of the language
        - language_code: ISO 639-1 two-letter code
        - confidence: Detection confidence (0-1)
        - is_rtl: Whether it's a right-to-left language
    """
    try:
        # Prepare the messages for DeepSeek
        system_prompt = LANGUAGE_DETECTION_PROMPT.format(text=text)
        
        # Get language analysis from DeepSeek
        response = await call_deepseek(
            system_prompt=system_prompt,
            user_messages=[],
            temperature=0.1  # Low temperature for more precise detection
        )
        
        try:
            # Parse the JSON response
            result = json.loads(response)
            
            # Validate required fields
            required_fields = ["language_name", "language_code", "confidence", "is_rtl"]
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Missing required field: {field}")
            
            # Log the detection details
            logger.info(
                f"Language detected: {result['language_name']} "
                f"({result['language_code']}) with "
                f"{result['confidence']*100:.1f}% confidence"
            )
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse language detection response: {response}")
            # Return English as fallback
            return {
                "language_name": "English",
                "language_code": "en",
                "confidence": 1.0,
                "is_rtl": False
            }
        
    except Exception as e:
        logger.error(f"Error detecting language: {e}", exc_info=True)
        # Return English as fallback
        return {
            "language_name": "English",
            "language_code": "en",
            "confidence": 1.0,
            "is_rtl": False
        }

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
