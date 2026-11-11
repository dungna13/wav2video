"""
Package `prompts`: Quản lý tập trung toàn bộ System/User Prompts & 12 Mô hình Kịch bản.
"""

from prompts.angle_miner_prompt import PROMPT_ANGLE_MINER_TEMPLATE, render_angle_miner_prompt
from prompts.architect_prompt import PROMPT_ARCHITECT_TEMPLATE, render_architect_prompt
from prompts.narrative_models import (
    CORE_COGNITIVE_PRINCIPLES,
    NARRATIVE_MODELS,
    VALID_NARRATIVE_MODELS,
    format_models_catalog_for_prompt,
    render_model_beat_sheet_block,
    select_optimal_narrative_model,
)
from prompts.outro_moral_prompt import OUTRO_MORAL_PROMPT_TEMPLATE, render_outro_moral_prompt
from prompts.scorer_prompt import PROMPT_SCORER_TEMPLATE, render_scorer_prompt

__all__ = [
    "PROMPT_ARCHITECT_TEMPLATE",
    "PROMPT_SCORER_TEMPLATE",
    "OUTRO_MORAL_PROMPT_TEMPLATE",
    "PROMPT_ANGLE_MINER_TEMPLATE",
    "render_architect_prompt",
    "render_scorer_prompt",
    "render_outro_moral_prompt",
    "render_angle_miner_prompt",
    "CORE_COGNITIVE_PRINCIPLES",
    "NARRATIVE_MODELS",
    "VALID_NARRATIVE_MODELS",
    "format_models_catalog_for_prompt",
    "render_model_beat_sheet_block",
    "select_optimal_narrative_model",
]
