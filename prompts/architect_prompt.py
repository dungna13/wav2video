"""
Bộ điều phối Prompt cho Node `prompt_architect_node` — ĐẠO DIỄN PHIM TÀI LIỆU NGẮN (9:16).

Hỗ trợ định tuyến hình ảnh thật (`visual_source_type: "real_photo"` + `real_media_query`) cho địa danh,
nhân vật lịch sử, di tích, hiện vật và tư liệu gốc, bên cạnh `stock_video` và `ai_photo`.

Đã phân rã từng mô hình kịch bản (13 mô hình) thành các tệp độc lập trong `prompts/architect_prompts/`
(`abt.py`, `in_medias_res.py`, `freytag_3_act.py`, `pixar_story_spine.py`, `scqa.py`,
`visual_math_essay.py`, `hook_retain_payoff.py`, `myth_vs_reality.py`, `open_loops.py`,
`rule_of_three.py`, `pas.py`, `bab.py`, `aida.py`) kèm cấu phần dùng chung tại `architect_prompts/_shared.py`
để dễ bảo trì và tinh chỉnh riêng từng cấu trúc mà không ảnh hưởng các mô hình khác.
"""

from __future__ import annotations

from .architect_prompts import (
    ARCHITECT_PROMPT_MODULES,
    ARCHITECT_PROMPT_TEMPLATES,
    get_architect_prompt_module,
    render_model_architect_prompt,
)
from .narrative_models import select_domain_expert, select_optimal_narrative_model

# Giữ alias tương thích ngược cho caller import trực tiếp `PROMPT_ARCHITECT_TEMPLATE`
PROMPT_ARCHITECT_TEMPLATE = ARCHITECT_PROMPT_TEMPLATES["abt"]


def render_architect_prompt(
    user_request: str,
    intent_mode: str = "NO_HUMAN_BROLL",
    prompt_feedback: str = "",
    filtered_character_context: str = "",
    source_context: str = "",
    narrative_model: str = "auto",
    genre_hint: str = "",
    domain_expert: str = "auto",
) -> str:
    """Chọn mô hình kịch bản tối ưu (hoặc theo chỉ định) và kết xuất prompt từ tệp mô hình độc lập."""
    selection = select_optimal_narrative_model(
        user_request,
        source_context=source_context,
        genre_hint=genre_hint,
        preferred_model=narrative_model,
    )
    selected_id = selection["selected_model_id"]
    expert = select_domain_expert(
        user_request,
        source_context=source_context,
        genre_hint=genre_hint,
        narrative_model=selected_id,
        preferred_expert=domain_expert,
    )
    return render_model_architect_prompt(
        selected_id,
        user_request=user_request,
        intent_mode=intent_mode,
        prompt_feedback=prompt_feedback,
        filtered_character_context=filtered_character_context,
        source_context=source_context,
        rationale=selection["rationale"],
        domain_expert_role=expert["expert_role"],
        domain_expert_lens=expert["expert_lens"],
    )


__all__ = [
    "ARCHITECT_PROMPT_MODULES",
    "ARCHITECT_PROMPT_TEMPLATES",
    "PROMPT_ARCHITECT_TEMPLATE",
    "get_architect_prompt_module",
    "render_architect_prompt",
]
