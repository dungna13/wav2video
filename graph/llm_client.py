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
        "thinking_process": {"type": "STRING"},
        "style_anchor_en": {"type": "STRING"},
        "music_mood": {"type": "STRING"},
        "scenes": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "narration_vn": {"type": "STRING"},
                    "image_prompt_en": {"type": "STRING"},
                    "stock_query_en": {"type": "STRING"},
                    "camera": {"type": "STRING"},
                    "overlay_keyword_vn": {"type": "STRING"},
                },
                "required": ["narration_vn", "image_prompt_en", "stock_query_en", "camera"],
            },
        },
        "story_moral": {"type": "STRING"},
        "claims_to_verify": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": [
        "topic_title",
        "genre",
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
        "scene_narration_vn": {"type": "STRING"},
        "outro_reflection_vn": {"type": "STRING"},
        "closing_prayer_vn": {"type": "STRING"},
    },
    "required": [
        "scene_narration_vn",
        "outro_reflection_vn",
        "closing_prayer_vn",
    ],
}


def _extract_json_object(raw_text: str) -> Optional[Dict[str, Any]]:
    """Trích xuất JSON an toàn từ chuỗi phản hồi của LLM."""
    if not raw_text:
        return None
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return None
    return None


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
        candidate_models = [GEMINI_MODEL]
        for fallback_m in ["gemini-3.1-flash-lite-preview", "gemini-3-flash-preview", "gemini-2.5-flash"]:
            if fallback_m not in candidate_models:
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

    # Gọi Free LLM Reasoning Endpoint (OpenAI-compatible `openai-fast`) hoàn toàn miễn phí
    if FREE_LLM_ENDPOINT:
        required_keys = response_schema.get("required", [])
        schema_hint = (
            f"\nReturn ONLY a single valid JSON object containing keys: {required_keys}. "
            f"Nested arrays/objects described in the prompt (e.g. `scenes`) must be included in full. "
            f"Keep reasoning brief and output valid JSON immediately."
        )
        for model_name in [FREE_LLM_MODEL, "openai"] if FREE_LLM_MODEL != "openai" else ["openai"]:
            try:
                oa_payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system_instruction + schema_hint},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": GEMINI_TEMPERATURE,
                    "max_tokens": 8000,
                }
                resp = requests.post(FREE_LLM_ENDPOINT, json=oa_payload, timeout=FREE_LLM_TIMEOUT)
                if resp.status_code != 200:
                    print(f" [Free LLM {model_name}] HTTP {resp.status_code}: {resp.text[:160]}")
                    continue
                data = resp.json()
                choice = data["choices"][0]
                msg = choice["message"]
                content = msg.get("content") or ""
                reasoning = msg.get("reasoning") or ""
                parsed = _extract_json_object(content) or _extract_json_object(reasoning)
                if parsed:
                    if reasoning and not parsed.get("thinking_process"):
                        parsed["thinking_process"] = reasoning[:350]
                    print(f"[LLM Thinking ({model_name})] Đã suy luận & thiết kế kịch bản thành công!")
                    return parsed
                print(
                    f" [Free LLM {model_name}] Không có JSON hợp lệ (finish_reason={choice.get('finish_reason')}, "
                    f"content={len(content)} ký tự, reasoning={len(reasoning)} ký tự)."
                )
            except Exception as e:
                print(f" [Free LLM {model_name}] {type(e).__name__}: {str(e)[:140]}")
                continue
        print(" [LLM] Endpoint miễn phí lỗi/quá tải. Khuyến nghị: điền GEMINI_API_KEY (AIza...) vào .env để ổn định.")

    return None
