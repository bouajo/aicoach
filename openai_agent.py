import os
import logging
from typing import Dict, List, Any
import openai
import json
from dotenv import load_dotenv

from database import get_user, update_user_summary

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY", "")
logger = logging.getLogger(__name__)

########################
# In-memory data
########################
CONVERSATIONS: Dict[str, List[Dict[str, str]]] = {}

########################
# PROMPTS
########################

# Prompt principal du coach Eric, 100% en français
COACH_PROMPT = """
Tu t’appelles Eric, tu as 50 ans, tu es un coach en perte de poids reconnu et tu t’exprimes en français exclusivement.
Tu as aidé des centaines de personnes à atteindre leur poids idéal. Ton style est chaleureux, empathique et engageant.

**Objectif** :
1) Demander d’abord à la personne de se présenter rapidement (prénom, âge, taille, poids actuel, poids idéal) en une seule question.
2) Réagir avec chaleur (ex: “Ok merci, enchanté de te rencontrer Pamela ! Moi, c’est Eric. On se tutoie ? ...”).
3) Poser des questions sur son historique de régimes (quel(s) régime(s), résultats obtenus, pourquoi ça n’a pas marché).
4) Proposer ensuite un plan de régime intermittent, basé sur ces principes :
   - 2 repas/jour (déjeuner et dîner avant 20h) + éventuellement un goûter léger (fruit).
   - Boire ~2,5L d’eau/jour, pas pendant les repas, pas juste avant de se coucher.
   - Manger 1/3 de protéines et 2/3 de légumes, limiter les aliments trop riches en glucides (ex. maïs, patate douce).
   - Fromage le midi uniquement, etc.
5) Vérifier si la personne est d’accord avec ce plan, ou si elle a des restrictions (végétarien, allergies, etc.), et t’adapter en conséquence.

**Style** :
- Toujours chaleureux, empathique, maximum 2 questions par message.
- Pas de mention du fait que tu es un modèle IA, tu es Eric, coach humain.
- Tu t’exprimes toujours en français.

Maintenant, à chaque fois que tu rédiges une réponse, suis ce style et ces étapes.
"""

########################
# GPT Helpers
########################

async def _call_gpt(
    system_prompt: str,
    user_messages: List[Dict[str, str]],
    temperature=0.7,
    max_tokens=300
) -> str:
    """
    Appel asynchrone à l'API OpenAI pour générer une réponse.
    system_prompt : instructions pour GPT
    user_messages : historique des derniers messages (role="user"/"assistant")
    """
    try:
        messages_for_gpt = [{"role": "system", "content": system_prompt}] + user_messages
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=messages_for_gpt,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message["content"]
    except Exception as e:
        logger.error(f"Erreur d'appel GPT: {e}")
        return "Désolé, j’ai rencontré un problème en générant la réponse."

def _add_msg(user_id: str, role: str, content: str):
    """Stocker un message (user ou assistant) dans un historique en mémoire."""
    if user_id not in CONVERSATIONS:
        CONVERSATIONS[user_id] = []
    CONVERSATIONS[user_id].append({"role": role, "content": content})

def _recent_msgs(user_id: str, limit: int = 5) -> List[Dict[str, str]]:
    """Récupérer les N derniers messages du user."""
    if user_id not in CONVERSATIONS:
        return []
    return CONVERSATIONS[user_id][-limit:]

def _summary_from_convo(messages: List[Dict[str, str]]) -> str:
    """
    Faire un mini résumé en concaténant les 3 derniers messages "user".
    """
    user_texts = [m["content"] for m in messages if m["role"] == "user"]
    last3 = user_texts[-3:]
    return " | ".join(last3)

def update_user_conversation_summary(user_id: str):
    """Mettre à jour la conversation_summary en DB."""
    from database import update_user_summary
    recent_messages = CONVERSATIONS.get(user_id, [])
    summary = _summary_from_convo(recent_messages)
    update_user_summary(user_id, {"summary": summary})

########################
# Fonctions d'entrée
########################

async def ask_coach_response(user_id: str, user_text: str) -> str:
    """
    Appel principal : envoie un message user_text à GPT (avec COACH_PROMPT), récupère la réponse d'Eric.
    """
    try:
        # Stockage du message user
        _add_msg(user_id, "user", user_text)
        recent_messages = _recent_msgs(user_id, limit=5)

        # Appel GPT
        assistant_reply = await _call_gpt(
            system_prompt=COACH_PROMPT,
            user_messages=recent_messages,
            temperature=0.7,
            max_tokens=300
        )

        # Stockage de la réponse d'Eric
        _add_msg(user_id, "assistant", assistant_reply)

        # Mettre à jour le résumé dans la DB
        update_user_conversation_summary(user_id)

        return assistant_reply
    except Exception as e:
        logger.error(f"Erreur dans ask_coach_response: {e}")
        return "Je suis désolé, j'ai rencontré un problème."

async def propose_regime_intermittent(user_id: str, user_text: str, user_details: dict) -> str:
    """
    Si l'utilisateur veut qu'on propose un plan/régime, 
    on peut re-demander au GPT un résumé du plan basé sur COACH_PROMPT.
    """
    try:
        # On ajoute un message user simili: "Donne-moi un plan détaillé"
        _add_msg(user_id, "user", user_text)

        # Re-appel GPT (Eric) pour générer un plan plus "focus".
        # On peut inclure user_details dans user_messages
        detail_str = json.dumps(user_details, ensure_ascii=False)
        user_messages = _recent_msgs(user_id, limit=5)
        # On rajoute un message "context" style "voici le profil"
        user_messages.append({
            "role": "user",
            "content": f"Voici mon profil: {detail_str}. Peux-tu me proposer un régime intermittent adapté ?"
        })

        plan_text = await _call_gpt(
            system_prompt=COACH_PROMPT,
            user_messages=user_messages,
            temperature=0.7,
            max_tokens=400
        )

        _add_msg(user_id, "assistant", plan_text)
        update_user_conversation_summary(user_id)
        return plan_text
    except Exception as e:
        logger.error(f"Erreur dans propose_regime_intermittent: {e}")
        return "Je suis désolé, je n'arrive pas à proposer un plan maintenant."
