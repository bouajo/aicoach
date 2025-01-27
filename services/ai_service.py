"""
Service for handling AI model interactions.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from enum import Enum
from openai import AsyncOpenAI
from managers import prompt_manager

logger = logging.getLogger(__name__)

class AIProvider(str, Enum):
    DEEPSEEK = "deepseek"

class AIService:
    def __init__(self):
        # Initialisation du client DeepSeek
        self.deepseek_client = AsyncOpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )
        
        # Configuration par défaut
        self.default_provider = AIProvider.DEEPSEEK
        self.model_configs = {
            AIProvider.DEEPSEEK: {
                "model": "deepseek-chat",
                "temperature": 0.7,
                "max_tokens": 300
            }
        }

    async def get_response(
        self,
        prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        provider: Optional[AIProvider] = None,
        **kwargs
    ) -> str:
        """
        Obtient une réponse du modèle AI.
        
        Args:
            prompt: Prompt système
            conversation_history: Historique optionnel de la conversation
            provider: Fournisseur AI à utiliser (toujours DeepSeek)
            **kwargs: Arguments supplémentaires pour l'appel API
            
        Returns:
            Réponse générée
        """
        try:
            messages = [{"role": "system", "content": prompt}]
            
            if conversation_history:
                messages.extend(conversation_history)

            return await self._call_deepseek(messages, **kwargs)

        except Exception as e:
            logger.error(f"Error getting AI response: {str(e)}")
            return "Désolé, j'ai rencontré un problème technique. Veuillez réessayer."

    async def _call_deepseek(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Appelle l'API DeepSeek."""
        try:
            config = self.model_configs[AIProvider.DEEPSEEK].copy()
            config.update(kwargs)
            
            response = await self.deepseek_client.chat.completions.create(
                messages=messages,
                **config
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"DeepSeek API error: {str(e)}")
            raise

# Instance globale du service
ai_service = AIService()