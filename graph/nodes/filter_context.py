"""
NODE 1: `filter_context_node` (Python thuần - 0 Token)
Chuẩn bị ngữ cảnh nhân vật (nếu có) và khởi tạo trạng thái cho Chủ đề (`user_request`).
"""

import re
from typing import Dict, List, Any
from graph.state import ChristianVideoState


def filter_context_node(state: ChristianVideoState) -> Dict[str, Any]:
    user_req = state.get("user_request", "").strip()
    user_req_lower = user_req.lower()
    existing_registry = state.get("characters", {}) or {}

    detected_chars: List[str] = []
    matched_traits: List[str] = []
    matched_ref_urls: List[str] = []

    for char_key, profile in existing_registry.items():
        saved_aliases = profile.get("aliases", [])
        all_patterns = [re.escape(char_key)] + [re.escape(a.lower()) for a in saved_aliases]
        if any(re.search(rf"(?<!\w){pat}(?!\w)", user_req_lower) for pat in all_patterns):
            detected_chars.append(char_key)
            matched_traits.append(f"- {char_key}: {profile['visual_traits']}")
            if profile.get("reference_image_url"):
                matched_ref_urls.append(profile["reference_image_url"])

    filtered_context_str = "\n   ".join(matched_traits) if matched_traits else "Video giải thích trực quan (Không cố định nhân vật)."

    print(
        f"[Node 1: filter_context_node] Topic: '{user_req}' | Nhân vật kế thừa: {len(matched_traits)}"
    )

    return {
        "detected_characters": detected_chars,
        "filtered_character_context": filtered_context_str,
        "known_reference_urls": matched_ref_urls,
        "retry": 0,
        "prompt_feedback": "",
    }
