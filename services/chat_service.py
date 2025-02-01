# file: services/chat_service.py

import logging
from typing import Tuple, Dict, Any
from data.models import UserProfile
from data.database import db
from services.conversation_service import conversation_service
from services.ai_service import ai_service
from deepseek_agent import summarize_text

logger = logging.getLogger(__name__)

class ChatService:
    async def process_message(self, user_id: str, message: str) -> Tuple[str, Dict[str, Any]]:
        """
        Process the user's message according to the new approach:
          1) If user does not exist -> create + introduction in English
          2) If user exists -> check conversation_state and fill required data
          3) Summarize each user answer
        Returns: (response_to_send, updated_user_profile)
        """
        # 1) Check if user exists
        profile_data = await db.get_user_profile(user_id)
        if not profile_data:
            # Create a brand new user
            new_profile = {
                "user_id": user_id,
                "conversation_state": "introduction",
                "language": "en",  # default to English
            }
            await db.update_user_profile(user_id, new_profile)

            # Save user's message to conversation history
            await conversation_service.add_message(user_id, "user", message)

            # Respond with introduction in English
            intro_text = (
                "Hi I'm Edgar, I'm your coach specialized in diet and nutrition. "
                "I'd love to help you achieve your health goals!\n\n"
                "First, let's pick a language. "
                "Which language would you prefer to use going forward? (English or French?)"
            )
            # Save assistant response
            await conversation_service.add_message(user_id, "assistant", intro_text)

            return intro_text, new_profile

        # If user exists, let's update the conversation
        # Store the user's incoming message
        await conversation_service.add_message(user_id, "user", message)

        # Summarize the user's answer (using new function in deepseek_agent)
        short_summary = await summarize_text(
            question=f"(Previous state: {profile_data.get('conversation_state')})",
            user_answer=message
        )
        # Store the summary in DB as a separate message for reference
        await conversation_service.add_message(user_id, "summary", short_summary)

        # 2) We have a user profile, let's manage conversation states step by step
        conversation_state = profile_data.get("conversation_state", "introduction")
        language = profile_data.get("language", "en")  # default fallback

        # Helper to respond in the user's chosen language (simple approach)
        def t(msg_en: str, msg_fr: str) -> str:
            return msg_fr if language == "fr" else msg_en

        # Next response to user
        response = ""

        # --- INTRODUCTION: user picks language
        if conversation_state == "introduction":
            chosen_lang = message.lower().strip()
            if "french" in chosen_lang or "fr" in chosen_lang:
                language = "fr"
            else:
                # If not sure, default to English
                language = "en"

            # Update user
            await db.update_user_profile(user_id, {"language": language, "conversation_state": "collecting_name"})
            response = t(
                "Great, we'll continue in English. What's your first name?",
                "Parfait, nous allons continuer en français. Quel est votre prénom ?"
            )

        # --- COLLECT NAME
        elif conversation_state == "collecting_name":
            # Save user name
            if len(message.strip()) < 2:
                response = t("That doesn't seem like a valid name. Please try again.", 
                             "Ce prénom ne semble pas valide. Réessayez s'il vous plaît.")
                return response, profile_data
            await db.update_user_profile(user_id, {
                "first_name": message.strip(),
                "conversation_state": "collecting_age"
            })
            response = t(
                f"Nice to meet you, {message.strip()}! How old are you?",
                f"Ravi de vous rencontrer, {message.strip()}! Quel âge avez-vous ?"
            )

        # --- COLLECT AGE
        elif conversation_state == "collecting_age":
            try:
                age_val = int(message.strip())
            except:
                response = t("Please enter a valid number for your age.", 
                             "Veuillez entrer un âge valide (nombre).")
                return response, profile_data

            if age_val < 12 or age_val > 100:
                response = t("Please enter an age between 12 and 100.", 
                             "Veuillez entrer un âge entre 12 et 100 ans.")
                return response, profile_data

            await db.update_user_profile(user_id, {
                "age": age_val,
                "conversation_state": "collecting_current_weight"
            })
            response = t(
                "Got it. What's your current weight in kg?",
                "Parfait. Quel est votre poids actuel en kg ?"
            )

        # --- COLLECT CURRENT WEIGHT
        elif conversation_state == "collecting_current_weight":
            try:
                w_val = float(message.strip())
            except:
                response = t("Please enter a valid number for your weight.", 
                             "Veuillez entrer un poids valide.")
                return response, profile_data

            if w_val < 30 or w_val > 300:
                response = t("Please enter a weight between 30 and 300 kg.", 
                             "Veuillez saisir un poids entre 30 et 300 kg.")
                return response, profile_data

            await db.update_user_profile(user_id, {
                "current_weight": w_val,
                "conversation_state": "collecting_goal_weight"
            })
            response = t(
                "Thanks. What is your goal weight (in kg)?",
                "Merci. Quel est votre objectif de poids (en kg) ?"
            )

        # --- COLLECT GOAL WEIGHT
        elif conversation_state == "collecting_goal_weight":
            try:
                g_val = float(message.strip())
            except:
                response = t("Please enter a valid number for your goal weight.", 
                             "Veuillez entrer un poids cible valide.")
                return response, profile_data

            if g_val < 30 or g_val > 300:
                response = t("Please enter a goal weight between 30 and 300 kg.", 
                             "Veuillez entrer un objectif de poids entre 30 et 300 kg.")
                return response, profile_data

            await db.update_user_profile(user_id, {
                "target_weight": g_val,
                "conversation_state": "collecting_timeline"
            })
            response = t(
                "Great. In how many weeks (or by which date) do you want to reach that goal?",
                "Très bien. Dans combien de semaines (ou à quelle date) souhaitez-vous atteindre cet objectif ?"
            )

        # --- COLLECT TIMELINE
        elif conversation_state == "collecting_timeline":
            # We won't do heavy validation here; just store it
            timeline_str = message.strip()
            # E.g. "12 weeks" or "2024-06-30"
            await db.update_user_profile(user_id, {
                "target_date": timeline_str,
                "conversation_state": "summary_ready"
            })
            response = t(
                "Great! Let me summarize what I have so far...",
                "Parfait ! Laissez-moi résumer les informations recueillies..."
            )

        # --- SHOW SUMMARY, THEN ASK NEXT QUESTIONS
        elif conversation_state == "summary_ready":
            # Show summary of user data
            profile_data = await db.get_user_profile(user_id) or {}
            name = profile_data.get("first_name")
            age = profile_data.get("age")
            cw = profile_data.get("current_weight")
            gw = profile_data.get("target_weight")
            td = profile_data.get("target_date")

            summary_text = t(
                f"""
Here is what I have for you, {name}:
- Age: {age}
- Current weight: {cw} kg
- Goal weight: {gw} kg
- Target timeline: {td}

Now I'd like to know more about your background. For example: Where do you live? Do you exercise?
""",
                f"""
Voici ce que j'ai pour vous, {name} :
- Âge : {age}
- Poids actuel : {cw} kg
- Poids cible : {gw} kg
- Délai pour l'objectif : {td}

J'aimerais en savoir plus sur vous. Par exemple : où habitez-vous ? Faites-vous du sport ?
"""
            )

            await db.update_user_profile(user_id, {"conversation_state": "extra_questions"})
            response = summary_text

        # --- EXTRA QUESTIONS: every user answer is summarized and stored
        else:
            # Here, we can just keep the conversation open-ended
            # Example question: "Any other details you'd like to share?"
            # The user can continue chatting, we keep summarizing
            response = t(
                "Thanks for that! Anything else you'd like to share or any questions? (Type 'done' to finish).",
                "Merci pour ces informations ! Avez-vous autre chose à ajouter ou des questions ? (Tapez 'fin' pour terminer)."
            )

            # If the user types "done" (or "fin"), you might finalize
            if message.lower().strip() in ("done", "fin"):
                response = t(
                    "Understood. We'll keep these details on file and move forward with your plan soon!",
                    "Très bien. Nous allons conserver ces informations et élaborer votre plan sous peu!"
                )
                # You could update conversation state to "finished" or keep it as is
                await db.update_user_profile(user_id, {"conversation_state": "finished"})

        # 3) Save the final response from the assistant to the DB
        await conversation_service.add_message(user_id, "assistant", response)

        # Return the response and the updated user profile
        updated_profile = await db.get_user_profile(user_id) or {}
        return response, updated_profile


# Create a single global instance
chat_service = ChatService()
