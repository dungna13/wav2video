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

import re
from typing import Any

from .architect_prompts import (
    ARCHITECT_PROMPT_MODULES,
    ARCHITECT_PROMPT_TEMPLATES,
    get_architect_prompt_module,
    render_model_architect_prompt,
)
from .narrative_models import select_domain_expert, select_optimal_narrative_model

# ── 7 MÔ HÌNH GIAO DIỆN THỊ GIÁC CHUẨN (VISUAL UI PARADIGMS) ──
VISUAL_UI_MODELS: dict[str, dict[str, str]] = {
    "manim_dark_mode": {
        "name": "Manim Dark-Mode (Visual Math Essay)",
        "broll_hint": "3blue1brown style animation 4k, equations visualization",
        "style_rule": "Nền đen mờ, lưới tọa độ mảnh, đồ họa hình học tối giản, điểm nhấn vàng hổ phách.",
    },
    "frameless_glassmorphism": {
        "name": "Frameless Glassmorphism (Liquid Crystal)",
        "broll_hint": "futuristic 3d data visualization 4k, glowing neural network, high tech abstract",
        "style_rule": "Thủy tinh pha lê 3D trong suốt, ánh sáng cực quang, vi mạch công nghệ cao.",
    },
    "editorial_mixed_media": {
        "name": "Editorial Collage / Mixed-Media Documentary",
        "broll_hint": "archival documentary footage, vintage newspaper map zoom, investigative journalism 4k",
        "style_rule": "Tư liệu báo giấy, bản đồ vệ tinh, ảnh phóng sự lưu trữ chân thực.",
    },
    "neo_brutalism_wireframe": {
        "name": "Neo-Brutalism & Bold Wireframe",
        "broll_hint": "cybersecurity code terminal screen 4k, wireframe network dark neon",
        "style_rule": "Đường viền sắc nét, phông chữ monospace/code, tương phản neon kỹ thuật.",
    },
    "swiss_minimal_typography": {
        "name": "Swiss Minimal Typography (Bauhaus)",
        "broll_hint": "minimalist architecture shadow light 4k, philosophical atmospheric slow motion",
        "style_rule": "Tối giản hai màu đối lập, khoảng trống âm thoáng đãng, trang trọng triết lý.",
    },
    "cyberpunk_terminal_hud": {
        "name": "Cyberpunk / Sci-Fi Terminal HUD",
        "broll_hint": "semiconductor microchip sci-fi hud 4k, futuristic robot laboratory",
        "style_rule": "Giao diện console, radar vector neon xanh, đường quét quang học.",
    },
    "vintage_archival_sepia": {
        "name": "Vintage Paper & Archival Sepia",
        "broll_hint": "ancient ruins archaeological excavation 4k, antique manuscript museum footage",
        "style_rule": "Tông màu sepia/nâu đất hoài niệm, cổ thư, di tích văn minh cổ đại.",
    },
}

ANTI_ABRUPT_ENDING_RULES = (
    "1. Peak–End Rule (Kahneman): Câu cuối cùng phải là câu chốt đắt giá và quyền lực nhất, không tóm tắt thừa.\n"
    "2. Zeigarnik Closed Loop (Loewenstein): Trả lời dứt khoát câu hỏi/nghịch lý đã mở ở Hook (Cảnh 1); TUYỆT ĐỐI KHÔNG bỏ lửng hay mở thêm loop dữ kiện mới ở cảnh cuối.\n"
    "3. Bookend Callback: Gợi nhắc lại chính hình ảnh hoặc ẩn dụ mở đầu ở tầm nhận thức sâu sắc hơn.\n"
    "4. Catharsis & Denouement: Hạ nhịp lắng đọng, khẳng định hệ quả sâu sắc (tránh rao giảng đạo đức sáo rỗng)."
)


def select_visual_ui_model(
    topic: str,
    narrative_model: str = "",
    expert_id: str = "",
) -> dict[str, str]:
    """Chọn trường phái thị giác tối ưu dựa trên chủ đề, mô hình tự sự và chuyên gia."""
    t_low = (topic or "").lower()
    if narrative_model == "visual_math_essay" or expert_id == "mathematician" or any(
        k in t_low for k in ("toán", "số pi", "fibonacci", "giải tích", "hình học", "thuật toán")
    ) or re.search(r"\bpi\b", t_low):
        key = "manim_dark_mode"
    elif any(k in t_low for k in ("hacker", "an ninh mạng", "cyber", "mã nguồn", "lập trình")):
        key = "neo_brutalism_wireframe"
    elif any(k in t_low for k in ("chip", "bán dẫn", "robot", "tình báo số", "cyberpunk")):
        key = "cyberpunk_terminal_hud"
    elif any(k in t_low for k in ("ai ", "trí tuệ nhân tạo", "fintech", "big data", "tỷ đô", "tài chính")):
        key = "frameless_glassmorphism"
    elif any(k in t_low for k in ("cổ đại", "lăng mộ", "tần thủy hoàng", "kim tự tháp", "khảo cổ", "stonehenge", "hóa thạch")):
        key = "vintage_archival_sepia"
    elif any(k in t_low for k in ("triết học", "tâm lý", "chủ nghĩa", "lãnh đạo", "nhân sinh")):
        key = "swiss_minimal_typography"
    else:
        key = "editorial_mixed_media"
    info = dict(VISUAL_UI_MODELS[key])
    info["id"] = key
    return info

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
    "ANTI_ABRUPT_ENDING_RULES",
    "PROMPT_ARCHITECT_TEMPLATE",
    "VISUAL_UI_MODELS",
    "get_architect_prompt_module",
    "render_architect_prompt",
    "select_visual_ui_model",
]
