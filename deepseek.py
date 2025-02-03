"""
deepseek.py
Minimal integration with DeepSeek. We have two methods:
1) detect_language - short prompt to guess the language from the user's text
2) chat_completion - general text completion
"""

import os
import logging
import json
import httpx
from dotenv import load_dotenv
from typing import List, Dict, Any

load_dotenv()
logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY is not set in .env")

API_BASE = "https://api.deepseek.com/v1"

LANGUAGE_SYSTEM_PROMPT = """You are a language detection expert.
Read the user message and respond ONLY with a valid 2-letter language code (e.g., 'en', 'fr', 'ar', etc.).
If uncertain, default to 'en'.
"""

async def detect_language(text: str) -> str:
    """Return the 2-letter language code for the user's text."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": LANGUAGE_SYSTEM_PROMPT},
                    {"role": "user", "content": text}
                ],
                "temperature": 0.1,
                "max_tokens": 10
            }
            headers = {
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            }
            resp = await client.post(f"{API_BASE}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            # The model's reply
            reply = data["choices"][0]["message"]["content"].strip().lower()
            # Just in case the model output is messy
            return reply[:2]  # e.g. 'en'
    except Exception as e:
        logger.error(f"Language detection error: {e}")
        return "en"

async def chat_completion(system_prompt: str, user_message: str) -> str:
    """
    General chat completion (for summarizing or generating messages).
    We'll keep it minimal.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.7,
                "max_tokens": 200
            }
            headers = {
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            }
            resp = await client.post(f"{API_BASE}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"Chat completion error: {e}")
        return "I'm sorry, something went wrong."
