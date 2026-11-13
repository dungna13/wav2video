"""
Registry các module Prompt Đạo diễn/Biên kịch độc lập theo 13 mô hình kịch bản.

Mỗi mô hình nằm trong một tệp riêng (`abt.py`, `in_medias_res.py`, ..., `visual_math_essay.py`)
để có thể chỉnh sửa trực tiếp Beat Sheet, Hook, Twist, Outro hoặc Thinking Process
của từng mô hình mà không ảnh hưởng tới các mô hình khác.
"""

from __future__ import annotations

from types import ModuleType

from ._shared import render_model_prompt_template
from . import (
    abt,
    aida,
    bab,
    freytag_3_act,
    hook_retain_payoff,
    in_medias_res,
    myth_vs_reality,
    open_loops,
    pas,
    pixar_story_spine,
    rule_of_three,
    scqa,
    visual_math_essay,
)

ARCHITECT_PROMPT_MODULES: dict[str, ModuleType] = {
    "abt": abt,
    "in_medias_res": in_medias_res,
    "freytag_3_act": freytag_3_act,
    "pixar_story_spine": pixar_story_spine,
    "scqa": scqa,
    "hook_retain_payoff": hook_retain_payoff,
    "myth_vs_reality": myth_vs_reality,
    "open_loops": open_loops,
    "rule_of_three": rule_of_three,
    "pas": pas,
    "bab": bab,
    "aida": aida,
    "visual_math_essay": visual_math_essay,
}

ARCHITECT_PROMPT_TEMPLATES: dict[str, str] = {
    model_id: mod.PROMPT_TEMPLATE for model_id, mod in ARCHITECT_PROMPT_MODULES.items()
}


def get_architect_prompt_module(model_id: str) -> ModuleType:
    """Trả về module prompt độc lập tương ứng với `model_id` (mặc định fallback `abt`)."""
    key = (model_id or "abt").strip().lower()
    if key in ARCHITECT_PROMPT_MODULES:
        return ARCHITECT_PROMPT_MODULES[key]
    raise ValueError(
        f"Không tìm thấy module prompt cho mô hình '{model_id}'. "
        f"Hợp lệ: {', '.join(sorted(ARCHITECT_PROMPT_MODULES))}."
    )


def render_model_architect_prompt(
    model_id: str,
    *,
    user_request: str,
    intent_mode: str = "NO_HUMAN_BROLL",
    prompt_feedback: str = "",
    filtered_character_context: str = "",
    source_context: str = "",
    rationale: str = "",
    domain_expert_role: str = "",
    domain_expert_lens: str = "",
) -> str:
    """Render prompt từ module độc lập của `model_id`."""
    mod = get_architect_prompt_module(model_id)
    if not domain_expert_role and not domain_expert_lens:
        return mod.render_prompt(
            user_request=user_request,
            intent_mode=intent_mode,
            prompt_feedback=prompt_feedback,
            filtered_character_context=filtered_character_context,
            source_context=source_context,
            rationale=rationale,
        )
    return render_model_prompt_template(
        mod.PROMPT_TEMPLATE,
        model_id=mod.MODEL_ID,
        model_name=mod.MODEL_NAME,
        user_request=user_request,
        intent_mode=intent_mode,
        prompt_feedback=prompt_feedback,
        filtered_character_context=filtered_character_context,
        source_context=source_context,
        rationale=rationale,
        domain_expert_role=domain_expert_role,
        domain_expert_lens=domain_expert_lens,
    )


__all__ = [
    "ARCHITECT_PROMPT_MODULES",
    "ARCHITECT_PROMPT_TEMPLATES",
    "get_architect_prompt_module",
    "render_model_architect_prompt",
    "abt",
    "in_medias_res",
    "freytag_3_act",
    "pixar_story_spine",
    "scqa",
    "hook_retain_payoff",
    "myth_vs_reality",
    "open_loops",
    "rule_of_three",
    "pas",
    "bab",
    "aida",
]
