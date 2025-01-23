from data.models import ConversationState
from prompts import introduction, diet_plan

class PromptManager:
    def __init__(self):
        self.templates = {
            ConversationState.INTRODUCTION: introduction.INTRODUCTION_PROMPT,
            ConversationState.DIET_PLANNING: diet_plan.DIET_PLAN_PROMPT
        }
    
    def get_prompt(self, state: ConversationState, context: dict = None) -> str:
        base_prompt = self.templates.get(state, "")
        return self._hydrate_prompt(base_prompt, context)
    
    def _hydrate_prompt(self, prompt: str, context: dict) -> str:
        if not context:
            return prompt
        return prompt.format(**context)