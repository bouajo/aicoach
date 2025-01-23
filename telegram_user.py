import os
import logging
import asyncio
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from dotenv import load_dotenv

from database import get_user, create_or_update_user
from openai_agent import ask_coach_response, propose_regime_intermittent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
PHONE_NUMBER = os.getenv("TELEGRAM_PHONE_NUMBER", "")

SESSION_NAME = "telegram_user_session"

# On va définir quelques états possibles
STATE_INIT = "init"
STATE_WAITING_INTRO = "waiting_intro"
STATE_COLLECTING_DETAILS = "collecting_details"
STATE_DISCUSSION = "discussion"

# Explication:
# 1) init => On salue l'utilisateur
# 2) waiting_intro => On attend qu'il réponde à "Présentez-vous (prénom, âge, taille, poids actuel, poids idéal)"
# 3) collecting_details => On stocke les infos, on lui dit "Ok enchanté..."
# 4) discussion => On utilise ask_coach_response pour tout le reste.

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

@client.on(events.NewMessage(incoming=True))
async def handle_incoming(event):
    if not event.is_private:
        return  # ignore group messages

    sender = await event.get_sender()
    user_id = f"tg_{sender.id}"
    user_text = event.raw_text.strip()

    # Récup ou init user
    user_record = get_user(user_id)
    if not user_record:
        user_record = create_or_update_user(user_id, {
            "conversation_state": STATE_INIT,
            "user_details": {}
        })

    state = user_record.get("conversation_state", STATE_INIT)
    user_details = user_record.get("user_details", {})

    try:
        # LOGIQUE D'ÉTAT
        if state == STATE_INIT:
            # On salue et on demande direct la présentation
            create_or_update_user(user_id, {"conversation_state": STATE_WAITING_INTRO})
            await event.respond(
                "Bonjour ! Pour mieux te connaître, peux-tu te présenter (prénom, âge, taille, poids actuel, poids idéal) ?"
            )

        elif state == STATE_WAITING_INTRO:
            # On suppose que l'utilisateur a donné en une seule phrase "Pamela, 30 ans, 1.65m, 70kg, objectif 60kg"
            # On stocke ce texte brut
            user_details["intro_brute"] = user_text
            create_or_update_user(user_id, {
                "conversation_state": STATE_COLLECTING_DETAILS,
                "user_details": user_details
            })

            # Réponse chaleureuse
            await event.respond(
                "Ok merci, enchanté de te rencontrer ! Moi c’est Eric. On se tutoie ? "
                "Super, je vais t’aider à atteindre ton objectif. Parle-moi un peu de tes expériences de régimes passés."
            )

        elif state == STATE_COLLECTING_DETAILS:
            # On peut stocker l'historique de régimes dans user_details
            user_details["historique_regimes"] = user_text
            create_or_update_user(user_id, {
                "conversation_state": STATE_DISCUSSION,
                "user_details": user_details
            })

            # On passe à la discussion libre avec GPT
            # On envoie la question "Ok, on va voir comment on peut t'aider..."
            ai_reply = await ask_coach_response(user_id, "J’ai bien noté ton historique de régimes.")
            await event.respond(ai_reply)

        else:
            # STATE_DISCUSSION
            # Si l'utilisateur mentionne un mot-clé "plan" ou "régime", on propose un plan
            lower_text = user_text.lower()
            if "plan" in lower_text or "régime" in lower_text:
                plan_response = await propose_regime_intermittent(user_id, user_text, user_details)
                await event.respond(plan_response)
            else:
                # Sinon, on continue la conversation coach
                ai_reply = await ask_coach_response(user_id, user_text)
                await event.respond(ai_reply)

    except Exception as e:
        logger.error(f"Erreur handle_incoming: {e}")
        await event.respond("Oups, j'ai rencontré un problème interne. Réessaie plus tard.")

async def main():
    await client.start(phone=PHONE_NUMBER)
    if not await client.is_user_authorized():
        try:
            await client.run_until_disconnected()
        except SessionPasswordNeededError:
            pwd = input("Vous avez activé la vérification en deux étapes. Entrez votre mot de passe : ")
            await client.sign_in(password=pwd)

    logger.info("Telegram user session started. Listening for messages...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
