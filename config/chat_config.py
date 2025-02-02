"""
Configuration settings for the chat service.
"""

from typing import Dict, Any

# Number of messages to keep before generating a summary
MESSAGES_BEFORE_SUMMARY = 5

# Supported languages and their configurations
SUPPORTED_LANGUAGES = {
    "en": {
        "code": "en",
        "name": "English",
        "native_name": "English",
        "flag": "🇬🇧",
        "is_rtl": False
    },
    "fr": {
        "code": "fr",
        "name": "French",
        "native_name": "Français",
        "flag": "🇫🇷",
        "is_rtl": False
    },
    "es": {
        "code": "es",
        "name": "Spanish",
        "native_name": "Español",
        "flag": "🇪🇸",
        "is_rtl": False
    },
    "ar": {
        "code": "ar",
        "name": "Arabic",
        "native_name": "العربية",
        "flag": "🇸🇦",
        "is_rtl": True
    },
    "it": {
        "code": "it",
        "name": "Italian",
        "native_name": "Italiano",
        "flag": "🇮🇹",
        "is_rtl": False
    }
}

def get_welcome_message(lang_code: str) -> str:
    """Generate welcome message in the specified language."""
    # Build language options string
    lang_options = "\n".join(
        f"{i+1}. {lang['native_name']} {lang['flag']}"
        for i, lang in enumerate(SUPPORTED_LANGUAGES.values())
    )
    
    messages = {
        "en": f"👋 Hello! I'm Eric 2.0, your AI Diet Coach. I can help you with nutrition advice and meal planning. What language would you prefer to communicate in?\n\n{lang_options}",
        "fr": f"👋 Bonjour! Je suis Eric 2.0, votre Coach Diététique IA. Je peux vous aider avec des conseils nutritionnels et la planification des repas. Dans quelle langue préférez-vous communiquer?\n\n{lang_options}",
        "es": f"👋 ¡Hola! Soy Eric 2.0, tu Coach de Dieta IA. Puedo ayudarte con consejos nutricionales y planificación de comidas. ¿En qué idioma prefieres comunicarte?\n\n{lang_options}",
        "ar": f"👋 مرحباً! أنا إريك 2.0، مدرب التغذية الخاص بك. يمكنني مساعدتك في نصائح التغذية وتخطيط الوجبات. بأي لغة تفضل التواصل؟\n\n{lang_options}",
        "it": f"👋 Ciao! Sono Eric 2.0, il tuo Coach Dietetico AI. Posso aiutarti con consigli nutrizionali e pianificazione dei pasti. In quale lingua preferisci comunicare?\n\n{lang_options}"
    }
    return messages.get(lang_code, messages["en"])

def get_language_confirmation(lang_code: str) -> str:
    """Get language confirmation message in the specified language."""
    messages = {
        "en": "Great! I'll communicate with you in English. To help you better, could you tell me your name?",
        "fr": "Parfait ! Je communiquerai avec vous en français. Pour mieux vous aider, pourriez-vous me dire votre nom ?",
        "es": "¡Excelente! Me comunicaré contigo en español. Para ayudarte mejor, ¿podrías decirme tu nombre?",
        "ar": "رائع! سأتواصل معك باللغة العربية. لمساعدتك بشكل أفضل، هل يمكنك إخباري باسمك؟",
        "it": "Perfetto! Comunicherò con te in italiano. Per aiutarti meglio, potresti dirmi il tuo nome?"
    }
    return messages.get(lang_code, messages["en"])

def get_error_message(lang_code: str) -> str:
    """Get error message in the specified language."""
    messages = {
        "en": "I apologize, but I encountered an error. Please try again.",
        "fr": "Je m'excuse, mais j'ai rencontré une erreur. Veuillez réessayer.",
        "es": "Me disculpo, pero encontré un error. Por favor, inténtalo de nuevo.",
        "ar": "أعتذر، لكنني واجهت خطأ. يرجى المحاولة مرة أخرى.",
        "it": "Mi scuso, ma ho riscontrato un errore. Per favore riprova."
    }
    return messages.get(lang_code, messages["en"])

# Language selection mapping
LANGUAGE_SELECTION_MAP = {str(i+1): lang["code"] for i, lang in enumerate(SUPPORTED_LANGUAGES.values())}

# Validation settings
VALIDATION_RULES = {
    "age": {
        "min": 10,
        "max": 100
    },
    "height_cm": {
        "min": 100,
        "max": 250
    },
    "weight": {
        "min": 30,
        "max": 300
    },
    "name_min_length": 2
}

# DeepSeek settings
DEEPSEEK_SETTINGS = {
    "default_temperature": 0.7,
    "max_tokens": 1000,
    "summarization_prompt": "Summarize the user's recent messages, focusing on their diet progress and concerns"
} 