"""
Package `prompts`: Quản lý tập trung toàn bộ System/User Prompts, 13 Mô hình Kịch bản,
14 Chuyên gia Miền (Domain Experts) & Bộ kiểm định tất định (`deterministic_validator`).
"""

from prompts.angle_miner_prompt import PROMPT_ANGLE_MINER_TEMPLATE, render_angle_miner_prompt
from prompts.architect_prompt import (
    ARCHITECT_PROMPT_MODULES,
    ARCHITECT_PROMPT_TEMPLATES,
    PROMPT_ARCHITECT_TEMPLATE,
    get_architect_prompt_module,
    render_architect_prompt,
)
from prompts.deterministic_validator import (
    build_full_image_prompt,
    format_scenes_for_outro_moral,
    format_scenes_for_scorer,
    parse_llm_json,
    validate_script_deterministic,
)
from prompts.narrative_models import (
    CORE_COGNITIVE_PRINCIPLES,
    DOMAIN_EXPERTS,
    NARRATIVE_MODELS,
    VALID_NARRATIVE_MODELS,
    classify_topic_and_expert,
    format_models_catalog_for_prompt,
    render_model_beat_sheet_block,
    select_domain_expert,
    select_optimal_narrative_model,
)
from prompts.outro_moral_prompt import OUTRO_MORAL_PROMPT_TEMPLATE, render_outro_moral_prompt
from prompts.scorer_prompt import PROMPT_SCORER_TEMPLATE, render_scorer_prompt

__all__ = [
    "ARCHITECT_PROMPT_MODULES",
    "ARCHITECT_PROMPT_TEMPLATES",
    "PROMPT_ARCHITECT_TEMPLATE",
    "PROMPT_SCORER_TEMPLATE",
    "OUTRO_MORAL_PROMPT_TEMPLATE",
    "PROMPT_ANGLE_MINER_TEMPLATE",
    "get_architect_prompt_module",
    "render_architect_prompt",
    "render_scorer_prompt",
    "render_outro_moral_prompt",
    "render_angle_miner_prompt",
    "CORE_COGNITIVE_PRINCIPLES",
    "DOMAIN_EXPERTS",
    "NARRATIVE_MODELS",
    "VALID_NARRATIVE_MODELS",
    "classify_topic_and_expert",
    "format_models_catalog_for_prompt",
    "render_model_beat_sheet_block",
    "select_domain_expert",
    "select_optimal_narrative_model",
    "build_full_image_prompt",
    "format_scenes_for_outro_moral",
    "format_scenes_for_scorer",
    "parse_llm_json",
    "validate_script_deterministic",
]
