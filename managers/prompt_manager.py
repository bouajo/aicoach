from data.models import ConversationState
from prompts import introduction, diet_plan, follow_up

class PromptManager:
    def __init__(self):
        self.prompts = {
            ConversationState.INTRODUCTION: introduction.INTRODUCTION_PROMPT,
            ConversationState.COLLECTING_DATA: diet_plan.DIET_PLAN_PROMPT,
            ConversationState.FOLLOW_UP: follow_up.FOLLOW_UP_PROMPT
        }
    
    def get_prompt(self, state: ConversationState, context: dict = None) -> str:
        """Version corrigée avec gestion de contexte"""
        base_prompt = self.prompts.get(state, "")
        return self._add_context(base_prompt, context)
    
    def _add_context(self, prompt: str, context: dict) -> str:
        if not context:
            return prompt
        return f"{prompt}\n\nCONTEXTE UTILISATEUR:\n{self._format_context(context)}"
    
    def _format_context(self, context: dict) -> str:
        formatted_context = []
        
        # Format user data
        if 'user_data' in context:
            user_data = context['user_data']
            formatted_context.extend([
                f"- Prénom: {user_data.get('first_name', 'Non renseigné')}",
                f"- Âge: {user_data.get('age', 'Non renseigné')}",
                f"- Taille: {user_data.get('height', 'Non renseigné')} cm",
                f"- Poids actuel: {user_data.get('current_weight', 'Non renseigné')} kg",
                f"- Objectif: {user_data.get('target_weight', 'Non renseigné')} kg",
                f"- Date cible: {user_data.get('target_date', 'Non renseigné')}"
            ])
        
        # Format conversation history
        if 'history' in context and context['history']:
            formatted_context.append("\nHISTORIQUE RÉCENT:")
            for msg in context['history'][-3:]:
                formatted_context.append(f"- {msg.role}: {msg.content}")
        
        return "\n".join(formatted_context)