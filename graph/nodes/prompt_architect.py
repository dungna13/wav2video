"""
NODE 2: `prompt_architect_node` — Đạo diễn kiêm biên kịch phim tài liệu ngắn.
Gọi LLM (prompt tại `prompts/architect_prompt.py`) để sinh: thể loại, `style_anchor_en`, danh sách CẢNH
(`narration_vn` + `image_prompt_en` + `stock_query_en` + `camera` + `overlay_keyword_vn`) và `claims_to_verify`.

Quy tắc: KHÔNG còn kịch bản dự phòng "giả vờ" khi LLM lỗi (trước đây sinh ra video lời chung chung không liên quan chủ đề).
Nếu LLM không trả được kịch bản hợp lệ sau vài lần thử -> báo lỗi rõ ràng để người dùng xử lý (key / mạng).
Từ danh sách cảnh, node suy ra 3 trường tương thích ngược (`hook_and_context_vn`, `deep_explanation_vn`, `outro_takeaway_vn`).
"""

from typing import Dict, List, Any

from prompts.architect_prompt import render_architect_prompt
from graph.llm_client import call_gemini_thinking_structured, ARCHITECT_GEMINI_SCHEMA
from graph.state import ChristianVideoState

VALID_CAMERAS = ["zoom_in", "zoom_out", "pan_left", "pan_right", "tilt_up", "tilt_down"]
LLM_ATTEMPTS = 2


def normalize_scenes(raw_scenes: Any) -> List[Dict[str, Any]]:
    """Làm sạch danh sách cảnh: bỏ cảnh rỗng, ép camera hợp lệ và không lặp liền kề."""
    scenes: List[Dict[str, Any]] = []
    for item in raw_scenes or []:
        if not isinstance(item, dict):
            continue
        narration = " ".join(str(item.get("narration_vn", "")).split())
        image_prompt = " ".join(str(item.get("image_prompt_en", "")).split())
        if not narration or not image_prompt:
            continue
        camera = str(item.get("camera", "")).strip().lower()
        if camera not in VALID_CAMERAS:
            camera = ""
        scenes.append(
            {
                "narration_vn": narration,
                "image_prompt_en": image_prompt,
                "stock_query_en": " ".join(str(item.get("stock_query_en", "")).split()),
                "camera": camera,
                "overlay_keyword_vn": " ".join(str(item.get("overlay_keyword_vn", "")).split()).upper(),
            }
        )

    prev = ""
    for i, sc in enumerate(scenes):
        if not sc["camera"] or sc["camera"] == prev:
            sc["camera"] = next(c for c in VALID_CAMERAS[i % 6 :] + VALID_CAMERAS[: i % 6] if c != prev)
        prev = sc["camera"]
    return scenes


def _split_script(scenes: List[Dict[str, Any]]):
    """Gom lời bình thành 3 phần (mở / thân / kết) cho các module cũ."""
    texts = [s["narration_vn"] for s in scenes]
    if len(texts) <= 2:
        return texts[0] if texts else "", " ".join(texts[1:]), ""
    return texts[0], " ".join(texts[1:-1]), texts[-1]


def prompt_architect_node(state: ChristianVideoState) -> Dict[str, Any]:
    user_request = state.get("user_request", "").strip()
    intent_mode = state.get("effective_intent_mode") or state.get("intent_mode") or "NO_HUMAN_BROLL"

    rendered_prompt = render_architect_prompt(
        user_request=user_request,
        intent_mode=intent_mode,
        prompt_feedback=state.get("prompt_feedback", ""),
        filtered_character_context=state.get("filtered_character_context", ""),
    )

    llm_json = None
    scenes: List[Dict[str, Any]] = []
    for attempt in range(1, LLM_ATTEMPTS + 1):
        llm_json = call_gemini_thinking_structured(
            prompt=rendered_prompt,
            response_schema=ARCHITECT_GEMINI_SCHEMA,
        )
        scenes = normalize_scenes((llm_json or {}).get("scenes"))
        if len(scenes) >= 4:
            break
        print(f" [Architect] Lần {attempt}/{LLM_ATTEMPTS}: LLM chưa trả kịch bản hợp lệ ({len(scenes)} cảnh).")

    if not llm_json or len(scenes) < 4:
        raise RuntimeError(
            "prompt_architect_node: LLM không trả được kịch bản >= 4 cảnh. Kiểm tra kết nối mạng, GEMINI_API_KEY "
            "(.env) hoặc FREE_LLM_ENDPOINT. Hệ thống KHÔNG dùng kịch bản dự phòng chung chung để tránh video lệch chủ đề."
        )

    topic_title = str(llm_json.get("topic_title") or user_request[:42]).strip()
    genre = str(llm_json.get("genre", "")).strip() or "history_culture"
    style_anchor = " ".join(str(llm_json.get("style_anchor_en", "")).split())
    music_mood = str(llm_json.get("music_mood", "")).strip()
    thinking_process = str(llm_json.get("thinking_process", "")).strip()
    story_moral = str(llm_json.get("story_moral", "")).strip() or f"{topic_title} #phimtailieu #kienthuc"
    claims = [str(c).strip() for c in (llm_json.get("claims_to_verify") or []) if str(c).strip()]

    hook_vn, deep_vn, outro_vn = _split_script(scenes)
    labels = [(s["overlay_keyword_vn"] or f"Cảnh {i + 1}") for i, s in enumerate(scenes)]
    total_words = sum(len(s["narration_vn"].split()) for s in scenes)

    print(
        f"[Node 2: prompt_architect_node] '{topic_title}' | genre={genre} | mode={intent_mode}\n"
        f"   ├─ Số cảnh / số từ   : {len(scenes)} cảnh / {total_words} từ\n"
        f"   ├─ Phong cách chung  : {style_anchor[:110]}\n"
        f"   └─ Cần kiểm chứng    : {claims}"
    )

    return {
        "topic_title": topic_title,
        "scripture_reference": topic_title,
        "retrieved_scripture": " ".join(s["narration_vn"] for s in scenes),
        "visual_archetype": genre,
        "visual_labels": labels,
        "rendered_architect_prompt": rendered_prompt,
        "thinking_process": thinking_process,
        "scene_action_prompt": scenes[0]["image_prompt_en"],
        "hook_and_context_vn": hook_vn,
        "deep_explanation_vn": deep_vn,
        "outro_takeaway_vn": outro_vn,
        "story_moral": story_moral,
        "new_characters": {},
        "genre": genre,
        "style_anchor_en": style_anchor,
        "music_mood": music_mood,
        "scenes": scenes,
        "claims_to_verify": claims,
    }
