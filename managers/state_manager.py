from data.models import ConversationState

class StateManager:
    def __init__(self):
        self.transitions = {
            ConversationState.INTRODUCTION: ConversationState.COLLECTING_DATA,
            ConversationState.COLLECTING_DATA: ConversationState.DIET_PLANNING,
            ConversationState.DIET_PLANNING: ConversationState.ACTIVE_COACHING,
            ConversationState.ACTIVE_COACHING: ConversationState.FOLLOW_UP
        }
    
    def get_next_state(self, current_state: ConversationState) -> ConversationState:
        return self.transitions.get(current_state, current_state)