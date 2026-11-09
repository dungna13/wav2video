"""
Package `prompts`: Quản lý tập trung toàn bộ System/User Prompts cho các LLM Nodes.
"""

from prompts.architect_prompt import PROMPT_ARCHITECT_TEMPLATE
from prompts.scorer_prompt import PROMPT_SCORER_TEMPLATE
from prompts.outro_moral_prompt import OUTRO_MORAL_PROMPT_TEMPLATE

__all__ = [
    "PROMPT_ARCHITECT_TEMPLATE",
    "PROMPT_SCORER_TEMPLATE",
    "OUTRO_MORAL_PROMPT_TEMPLATE",
]
