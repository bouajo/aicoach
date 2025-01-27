"""
User simulator for testing conversation flows.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from data.models import ConversationState
from managers import flow_manager, state_manager
from services.conversation_service import conversation_service

logger = logging.getLogger(__name__)

class UserSimulator:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.conversation_history: List[Dict[str, str]] = []
        self.current_state = ConversationState.INTRODUCTION
        self.user_data: Dict[str, Any] = {
            "conversation_state": self.current_state.value
        }

    async def simulate_conversation(self, responses: Dict[str, str]) -> None:
        """
        Simule une conversation complète avec des réponses prédéfinies.
        
        Args:
            responses: Dictionnaire des réponses par type de question
                Ex: {"first_name": "Jean", "age": "30", "height": "175"}
        """
        try:
            while True:
                # Obtient la prochaine question attendue
                next_field = flow_manager._get_next_expected_field(self.current_state, self.user_data)
                if not next_field:
                    logger.info(f"Simulation completed for state {self.current_state}")
                    if self.current_state == ConversationState.ACTIVE_COACHING:
                        break
                    continue

                field_name, field_description = next_field
                
                # Récupère la réponse prédéfinie
                response = responses.get(field_name)
                if not response:
                    logger.warning(f"No predefined response for {field_name}")
                    break

                # Simule l'envoi du message
                logger.info(f"User sending: {response}")
                await self.send_message(response)
                
                # Petit délai pour simuler une interaction réelle
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error in simulation: {str(e)}", exc_info=True)

    async def send_message(self, message: str) -> Optional[str]:
        """
        Simule l'envoi d'un message utilisateur.
        
        Args:
            message: Message à envoyer
            
        Returns:
            Réponse du bot ou None en cas d'erreur
        """
        try:
            # Traitement du message
            new_data, error_msg, can_transition = flow_manager.process_user_input(
                self.current_state,
                self.user_data,
                message
            )

            if error_msg:
                logger.warning(f"Validation error: {error_msg}")
                return error_msg

            # Mise à jour des données
            if new_data:
                self.user_data.update(new_data)
                logger.info(f"Updated user data: {new_data}")

            # Gestion de la transition d'état
            if can_transition:
                new_state = state_manager.get_next_state(
                    self.current_state,
                    self.user_data,
                    message
                )
                if new_state != self.current_state:
                    logger.info(f"State transition: {self.current_state} -> {new_state}")
                    self.current_state = new_state
                    self.user_data['conversation_state'] = new_state.value

            # Enregistrement du message
            await conversation_service.add_message(self.user_id, "user", message)
            
            # Obtention de la réponse
            next_question = flow_manager.get_next_question(self.current_state, self.user_data)
            if next_question:
                logger.info(f"Bot response: {next_question}")
                await conversation_service.add_message(self.user_id, "assistant", next_question)
                return next_question

            return "Simulation completed for current state"

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return None

    def get_conversation_summary(self) -> Dict[str, Any]:
        """
        Retourne un résumé de la conversation simulée.
        
        Returns:
            Dictionnaire contenant le résumé de la conversation
        """
        return {
            "user_id": self.user_id,
            "final_state": self.current_state.value,
            "collected_data": self.user_data,
            "timestamp": datetime.utcnow().isoformat()
        }

# Exemple d'utilisation
async def run_simulation():
    simulator = UserSimulator("test_user_1")
    test_responses = {
        "first_name": "Jean",
        "age": "30",
        "height": "175",
        "current_weight": "80",
        "target_weight": "75",
        "target_date": "décembre 2024"
    }
    await simulator.simulate_conversation(test_responses)
    print(simulator.get_conversation_summary()) 