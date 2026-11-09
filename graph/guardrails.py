"""
Tầng Python Guardrails (0 tốn token):
Kiểm soát và chỉnh sửa cứng kết quả đầu ra của Gemini Thinking trước khi chuyển sang Node tiếp theo:
  1. Cắt bỏ mọi từ khóa hiện đại/sai lịch sử (`FORBIDDEN_MODERN_TERMS`).
  2. Khóa cứng độ dài `scene_action_prompt` <= `MAX_SCENE_PROMPT_WORDS` (60 từ).
  3. Khóa cứng độ dài `visual_traits` <= `MAX_VISUAL_TRAITS_WORDS` (30 từ).
  4. Lọc bỏ các nhân vật đã có sẵn trong `state["characters"]` nếu Gemini vô tình liệt kê lại vào `new_characters`.
  5. Đảm bảo `story_moral` luôn đính kèm địa chỉ câu Kinh Thánh (`{scripture_reference}`).
"""

import re
import unicodedata
from typing import Dict, List, Any

from config.settings import (
    MAX_SCENE_PROMPT_WORDS,
    MAX_VISUAL_TRAITS_WORDS,
    FORBIDDEN_MODERN_TERMS,
)
from graph.state import (
    PromptArchitectOutput,
    NewCharacterItemSchema,
    CharacterProfile,
)


def to_ascii_slug(name: str) -> str:
    """Chuẩn hóa tên tiếng Việt có dấu sang `key_name` không dấu."""
    s = name.lower().replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"[^a-z0-9\s_]", "", s)
    return re.sub(r"[\s_]+", "_", s.strip())


def enforce_architect_guardrails(
    output: PromptArchitectOutput,
    scripture_reference: str,
    existing_registry: Dict[str, CharacterProfile],
) -> PromptArchitectOutput:
    """
    Hậu kiểm cứng bằng Python cho đầu ra của Node 3 (`prompt_architect_node`).
    Đảm bảo kết quả không bao giờ lệch khỏi khung quy định.
    """
    # 1. Xóa các từ khóa hiện đại bị cấm trong `scene_action_prompt`
    clean_scene = output.scene_action_prompt.strip()
    for bad_word in FORBIDDEN_MODERN_TERMS:
        clean_scene = re.sub(rf"(?i)\b{re.escape(bad_word)}\b", "", clean_scene)
    clean_scene = re.sub(r"\s+", " ", clean_scene).strip()

    # 2. Nếu thiếu từ khóa bối cảnh thế kỷ thứ 1, tự động neo vào đầu/cuối nếu còn chỗ
    if not any(kw in clean_scene.lower() for kw in ["1st-century", "judea", "galilee", "temple", "biblical"]):
        clean_scene = f"In 1st-century Judea, {clean_scene}"

    # 3. Khóa cứng giới hạn <= 60 từ cho `scene_action_prompt`
    scene_words = clean_scene.split()
    if len(scene_words) > MAX_SCENE_PROMPT_WORDS:
        clean_scene = " ".join(scene_words[:MAX_SCENE_PROMPT_WORDS]).rstrip(",;:") + "."

    # 4. Đảm bảo `story_moral` luôn chứa địa chỉ Kinh Thánh gốc (`{scripture_reference}`)
    clean_moral = output.story_moral.strip()
    if scripture_reference.lower() not in clean_moral.lower() and not re.search(r"\d+:\d+", clean_moral):
        clean_moral = clean_moral.rstrip(".") + f" ({scripture_reference})."

    # 5. Lọc `new_characters`: Loại bỏ nhân vật đã khóa trong `existing_registry` và giới hạn `visual_traits` <= 30 từ
    existing_keys = {k.lower() for k in existing_registry.keys()}
    existing_slugs = {
        v.get("key_name", to_ascii_slug(k)).lower()
        for k, v in existing_registry.items()
    }

    sanitized_new_chars: List[NewCharacterItemSchema] = []
    for item in output.new_characters:
        slug = to_ascii_slug(item.key_name)
        aliases_lower = [a.lower().strip() for a in item.aliases]

        # Nếu nhân vật đã tồn tại trong Registry -> Bỏ qua không tạo lại!
        if slug in existing_slugs or any(a in existing_keys for a in aliases_lower):
            continue

        # Khóa cứng `visual_traits` dưới 30 từ
        trait_words = item.visual_traits.strip().split()
        if len(trait_words) > MAX_VISUAL_TRAITS_WORDS:
            short_traits = " ".join(trait_words[:MAX_VISUAL_TRAITS_WORDS]).rstrip(",;:")
        else:
            short_traits = " ".join(trait_words)

        sanitized_new_chars.append(
            NewCharacterItemSchema(
                key_name=slug,
                aliases=item.aliases if item.aliases else [slug],
                visual_traits=short_traits,
            )
        )

    return PromptArchitectOutput(
        thinking_process=output.thinking_process.strip(),
        scene_action_prompt=clean_scene,
        story_moral=clean_moral,
        new_characters=sanitized_new_chars,
    )

