"""
Module kết nối LLM Thinking để lên kịch bản từ A-Z cho mọi Chủ đề (Topic):
1. Nếu `GEMINI_API_KEY` hợp lệ (bắt đầu bằng `AIza...`), gọi trực tiếp Google Gemini 2.5 Flash Thinking API với `responseSchema`.
2. Nếu `GEMINI_API_KEY` chưa hợp lệ hoặc bị lỗi, tự động gọi **Free LLM Reasoning API (`https://text.pollinations.ai/openai`, model `openai-fast`)**
   để LLM thật sự suy luận (`reasoning`) và viết kịch bản JSON chặt chẽ từ A-Z (thể loại + phong cách + danh sách cảnh lời bình/ảnh/camera) cho bất kỳ Topic nào.
"""

import re
import json
import socket
import requests
from typing import Dict, Any, Optional


def _has_network() -> bool:
    try:
        socket.gethostbyname("text.pollinations.ai")
        return True
    except Exception:
        return False


from config.settings import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_TEMPERATURE,
    GEMINI_THINKING_BUDGET,
    FREE_LLM_ENDPOINT,
    FREE_LLM_MODEL,
    FREE_LLM_TIMEOUT,
)

# =====================================================================
# 1. KHAI BÁO NATIVE `responseSchema` CHO ARCHITECT & SCORER
# =====================================================================
ARCHITECT_GEMINI_SCHEMA: Dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "topic_title": {"type": "STRING"},
        "genre": {"type": "STRING"},
        "narrative_model": {"type": "STRING"},
        "narrative_model_reason": {"type": "STRING"},
        "thinking_process": {"type": "STRING"},
        "style_anchor_en": {"type": "STRING"},
        "music_mood": {"type": "STRING"},
        "voice_profile": {"type": "STRING"},
        "bgm_alignment": {"type": "STRING"},
        "scenes": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "narration_vn": {"type": "STRING"},
                    "subtitle_vn": {"type": "STRING"},
                    "visual_source_type": {"type": "STRING"},
                    "real_media_query": {"type": "STRING"},
                    "image_prompt_en": {"type": "STRING"},
                    "stock_query_en": {"type": "STRING"},
                    "camera": {"type": "STRING"},
                    "overlay_keyword_vn": {"type": "STRING"},
                    "sfx_cue": {"type": "STRING"},
                    "bgm_energy": {"type": "STRING"},
                    "vocal_delivery": {"type": "STRING"},
                },
                "required": ["narration_vn", "subtitle_vn", "image_prompt_en", "stock_query_en", "camera"],
            },
        },
        "closing_takeaway": {"type": "STRING"},
        "story_moral": {"type": "STRING"},
        "claims_to_verify": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": [
        "topic_title",
        "genre",
        "narrative_model",
        "narrative_model_reason",
        "thinking_process",
        "style_anchor_en",
        "scenes",
        "story_moral",
    ],
}

SCORER_GEMINI_SCHEMA: Dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "hook_score": {"type": "NUMBER"},
        "visual_match_score": {"type": "NUMBER"},
        "story_score": {"type": "NUMBER"},
        "average_score": {"type": "NUMBER"},
        "pass_validation": {"type": "BOOLEAN"},
        "feedback_for_rewrite": {"type": "STRING"},
    },
    "required": [
        "hook_score",
        "visual_match_score",
        "story_score",
        "average_score",
        "pass_validation",
        "feedback_for_rewrite",
    ],
}

OUTRO_MORAL_GEMINI_SCHEMA: Dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "refined_narrations": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "scene_index": {"type": "INTEGER"},
                    "narration_vn": {"type": "STRING"},
                    "subtitle_vn": {"type": "STRING"},
                },
                "required": ["scene_index", "narration_vn", "subtitle_vn"],
            },
        },
        "story_moral": {"type": "STRING"},
    },
    "required": [
        "refined_narrations",
        "story_moral",
    ],
}

ANGLE_MINER_GEMINI_SCHEMA: Dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "book_title": {"type": "STRING"},
        "angles": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "angle_title": {"type": "STRING"},
                    "user_request_for_architect": {"type": "STRING"},
                    "hook_idea_vn": {"type": "STRING"},
                    "recommended_genre": {"type": "STRING"},
                    "recommended_intent_mode": {"type": "STRING"},
                    "recommended_narrative_model": {"type": "STRING"},
                    "model_selection_reason": {"type": "STRING"},
                    "key_evidence_quote": {"type": "STRING"},
                },
                "required": [
                    "angle_title",
                    "user_request_for_architect",
                    "hook_idea_vn",
                    "recommended_genre",
                    "recommended_intent_mode",
                    "recommended_narrative_model",
                    "key_evidence_quote",
                ],
            },
        },
    },
    "required": ["book_title", "angles"],
}


def _extract_json_object(raw_text: str) -> Optional[Dict[str, Any]]:
    """Trích xuất JSON an toàn từ chuỗi phản hồi của LLM (hỗ trợ markdown, trailing commas, unwrap nested)."""
    if not raw_text:
        return None
    text = raw_text.strip()

    # 1. Tìm khối ```json ... ``` hoặc ``` ... ```
    m_block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if m_block:
        candidate = m_block.group(1).strip()
        try:
            res = json.loads(candidate)
            if isinstance(res, dict):
                return _unwrap_scenes_if_nested(res)
        except Exception:
            cleaned = re.sub(r",\s*([\]\}])", r"\1", candidate)
            try:
                res = json.loads(cleaned)
                if isinstance(res, dict):
                    return _unwrap_scenes_if_nested(res)
            except Exception:
                pass

    # 2. Thử parse trực tiếp toàn bộ chuỗi
    try:
        res = json.loads(text)
        if isinstance(res, dict):
            return _unwrap_scenes_if_nested(res)
    except Exception:
        pass

    # 3. Tìm vùng ngoặc nhọn lớn nhất { ... }
    m_brace = re.search(r"(\{[\s\S]*\})", text)
    if m_brace:
        candidate = m_brace.group(1).strip()
        try:
            res = json.loads(candidate)
            if isinstance(res, dict):
                return _unwrap_scenes_if_nested(res)
        except Exception:
            cleaned = re.sub(r",\s*([\]\}])", r"\1", candidate)
            try:
                res = json.loads(cleaned)
                if isinstance(res, dict):
                    return _unwrap_scenes_if_nested(res)
            except Exception:
                pass

    # 4. Tìm mảng [ ... ] nếu LLM trả về trực tiếp danh sách cảnh
    m_arr = re.search(r"(\[[\s\S]*\])", text)
    if m_arr:
        candidate = m_arr.group(1).strip()
        try:
            arr = json.loads(candidate)
            if isinstance(arr, list) and arr and isinstance(arr[0], dict):
                return {"scenes": arr}
        except Exception:
            cleaned = re.sub(r",\s*([\]\}])", r"\1", candidate)
            try:
                arr = json.loads(cleaned)
                if isinstance(arr, list) and arr and isinstance(arr[0], dict):
                    return {"scenes": arr}
            except Exception:
                pass

    return None


def _unwrap_scenes_if_nested(data: Dict[str, Any]) -> Dict[str, Any]:
    """Tự động unwrap nếu LLM lồng mảng scenes vào trong object con."""
    if data.get("scenes") or data.get("angles"):
        return data
    for k in ["storyboard", "data", "result", "video", "output"]:
        if isinstance(data.get(k), dict) and (data[k].get("scenes") or data[k].get("angles")):
            return data[k]
    for k in ["scene_list", "scenelist", "shots", "segments"]:
        if isinstance(data.get(k), list):
            data["scenes"] = data[k]
            return data
    return data


def call_gemini_thinking_structured(
    prompt: str,
    response_schema: Dict[str, Any],
    system_instruction: str = (
        "Bạn là Đạo diễn kiêm Biên kịch phim tài liệu ngắn 9:16 (phong cách Vox / Thư Viện Lịch Sử), viết cho người xem trưởng thành. "
        "Tuân thủ nghiêm các RULE trong prompt, tự kiểm tra checklist rồi trả về DUY NHẤT 1 JSON Object hợp lệ theo schema."
    ),
) -> Optional[Dict[str, Any]]:
    """
    1. Thử gọi Google Gemini 2.5 Flash Thinking nếu `GEMINI_API_KEY` bắt đầu bằng `AIza`.
    2. Tự động gọi Free LLM Reasoning API (`https://text.pollinations.ai/openai`, model `openai-fast`)
       với timeout đủ cho quá trình `reasoning` (Thinking) hoàn tất.
    """
    if not _has_network():
        return None

    if GEMINI_API_KEY and GEMINI_API_KEY.startswith("AIza"):
        candidate_models = []
        for fallback_m in [GEMINI_MODEL, "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-3-flash-preview", "gemini-3.1-flash-lite-preview"]:
            if fallback_m and fallback_m not in candidate_models:
                candidate_models.append(fallback_m)

        for model_name in candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
            generation_config: Dict[str, Any] = {
                "temperature": GEMINI_TEMPERATURE,
                "topP": 0.85,
                "responseMimeType": "application/json",
                "responseSchema": response_schema,
            }
            if "2.5" in model_name and GEMINI_THINKING_BUDGET > 0:
                generation_config["thinkingConfig"] = {"thinkingBudget": GEMINI_THINKING_BUDGET}

            payload = {
                "systemInstruction": {"parts": [{"text": system_instruction}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": generation_config,
            }
            try:
                resp = requests.post(url, json=payload, timeout=45)
                if resp.status_code == 200:
                    data = resp.json()
                    parts = data["candidates"][0]["content"]["parts"]
                    parsed = _extract_json_object(parts[-1]["text"])
                    if parsed:
                        print(f"[LLM Thinking] Đã sinh JSON từ Gemini ({model_name})")
                        return parsed
                else:
                    print(f" [Gemini {model_name}] HTTP {resp.status_code} ({resp.text[:120]}) -> Thử model dự phòng...")
            except Exception as e:
                print(f" [Gemini {model_name}] Lỗi: {e} -> Thử model dự phòng...")
                continue

    # Gọi Free LLM Reasoning Endpoint (OpenAI-compatible) với danh sách dự phòng đa mô hình
    if FREE_LLM_ENDPOINT:
        required_keys = response_schema.get("required", [])
        schema_hint = (
            f"\nIMPORTANT: Return ONLY a single valid JSON object containing keys: {required_keys}. "
            f"All nested scenes and prompts must be fully populated. Output raw JSON only, no markdown, no explanation outside JSON."
        )
        # Danh sách mô hình miễn phí thử lần lượt để đảm bảo luôn có kết quả
        candidate_free_models = [FREE_LLM_MODEL] if FREE_LLM_MODEL else []
        for m in ["qwen", "openai-fast", "mistral", "openai", "gemini"]:
            if m not in candidate_free_models:
                candidate_free_models.append(m)

        for model_name in candidate_free_models:
            try:
                oa_payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system_instruction + schema_hint},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"},
                    "max_tokens": 4000,
                }
                resp = requests.post(FREE_LLM_ENDPOINT, json=oa_payload, timeout=min(FREE_LLM_TIMEOUT, 60))
                if resp.status_code != 200:
                    print(f" [Free LLM {model_name}] HTTP {resp.status_code}: {resp.text[:120]}")
                    continue
                data = resp.json()
                choice = data["choices"][0]
                msg = choice["message"]
                content = msg.get("content") or ""
                reasoning = msg.get("reasoning") or ""
                parsed = _extract_json_object(content) or _extract_json_object(reasoning)
                if parsed and (parsed.get("scenes") or parsed.get("angles") or parsed.get("sections")):
                    if reasoning and not parsed.get("thinking_process"):
                        parsed["thinking_process"] = reasoning[:350]
                    print(f"[LLM Thinking ({model_name})] Đã suy luận & thiết kế kịch bản thành công!")
                    return parsed
                print(
                    f" [Free LLM {model_name}] JSON chưa hợp lệ (content={len(content)} chars, reasoning={len(reasoning)} chars) -> Thử model tiếp theo..."
                )
            except Exception as e:
                print(f" [Free LLM {model_name}] {type(e).__name__} -> Thử model tiếp theo...")
                continue
        print(" [LLM] Tất cả Free LLM endpoint đang quá tải.")

    return None
