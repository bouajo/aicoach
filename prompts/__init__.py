"""
Package prompts: contient les templates de prompts pour différentes phases de la conversation.
"""

from .introduction import get_introduction_prompt, get_data_collection_prompt
from .diet_plan import get_diet_plan_prompt
from .follow_up import get_progress_check_prompt, get_adjustment_prompt

__all__ = [
    'get_introduction_prompt',
    'get_data_collection_prompt',
    'get_diet_plan_prompt',
    'get_progress_check_prompt',
    'get_adjustment_prompt'
] 