"""
Module kết nối LLM Thinking để lên kịch bản từ A-Z cho mọi Chủ đề (Topic):
1. Nếu `GEMINI_API_KEY` hợp lệ (bắt đầu bằng `AIza...`), gọi trực tiếp Google Gemini 2.5 Flash Thinking API với `responseSchema`.
2. Nếu `GEMINI_API_KEY` chưa hợp lệ hoặc bị lỗi, tự động gọi **Free LLM Reasoning API (`https://text.pollinations.ai/openai`, model `openai-fast`)**
   để LLM thật sự suy luận (`reasoning`) và viết kịch bản JSON chặt chẽ từ A-Z (Nhân vật + Bối cảnh + 4 Phân cảnh 2x2 + Lời bình) cho bất kỳ Topic nào.
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
)

# =====================================================================
# 1. KHAI BÁO NATIVE `responseSchema` CHO ARCHITECT & SCORER
# =====================================================================
ARCHITECT_GEMINI_SCHEMA: Dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "topic_title": {"type": "STRING"},
        "thinking_process": {"type": "STRING"},
        "visual_archetype": {"type": "STRING"},
        "visual_labels": {"type": "ARRAY", "items": {"type": "STRING"}},
        "scene_action_prompt": {"type": "STRING"},
        "hook_and_context_vn": {"type": "STRING"},
        "deep_explanation_vn": {"type": "STRING"},
        "outro_takeaway_vn": {"type": "STRING"},
        "story_moral": {"type": "STRING"},
        "new_characters": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "key_name": {"type": "STRING"},
                    "aliases": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "visual_traits": {"type": "STRING"},
                },
                "required": ["key_name", "aliases", "visual_traits"],
            },
        },
    },
    "required": [
        "topic_title",
        "thinking_process",
        "visual_archetype",
        "visual_labels",
        "scene_action_prompt",
        "hook_and_context_vn",
        "deep_explanation_vn",
        "outro_takeaway_vn",
        "story_moral",
        "new_characters",
    ],
}

SCORER_GEMINI_SCHEMA: Dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "rag_faithfulness_score": {"type": "NUMBER"},
        "cinematic_quality_score": {"type": "NUMBER"},
        "theological_moral_score": {"type": "NUMBER"},
        "average_score": {"type": "NUMBER"},
        "pass_validation": {"type": "BOOLEAN"},
        "feedback_for_rewrite": {"type": "STRING"},
    },
    "required": [
        "rag_faithfulness_score",
        "cinematic_quality_score",
        "theological_moral_score",
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
        "Bạn là Đạo diễn Phim Hoạt hình Điện ảnh 3D (Pixar / Makoto Shinkai Style) và Biên kịch Short Video. "
        "Hãy suy luận chặt chẽ và trả về DUY NHẤT 1 JSON Object hợp lệ theo đúng schema yêu cầu."
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
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        generation_config: Dict[str, Any] = {
            "temperature": GEMINI_TEMPERATURE,
            "topP": 0.85,
            "responseMimeType": "application/json",
            "responseSchema": response_schema,
        }
        if "2.5" in GEMINI_MODEL and GEMINI_THINKING_BUDGET > 0:
            generation_config["thinkingConfig"] = {"thinkingBudget": GEMINI_THINKING_BUDGET}

        payload = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": generation_config,
        }
        try:
            resp = requests.post(url, json=payload, timeout=35)
            resp.raise_for_status()
            data = resp.json()
            parts = data["candidates"][0]["content"]["parts"]
            parsed = _extract_json_object(parts[-1]["text"])
            if parsed:
                print(f"[LLM Thinking] Đã sinh JSON từ Gemini ({GEMINI_MODEL})")
                return parsed
        except Exception as e:
            print(f" [Gemini API Info] Chuyển sang Free LLM Reasoning API do: {e}")

    # Gọi Free LLM Reasoning Endpoint (OpenAI-compatible `openai-fast`) hoàn toàn miễn phí
    if FREE_LLM_ENDPOINT:
        required_keys = response_schema.get("required", [])
        schema_hint = (
            f"\nReturn ONLY a single valid JSON object containing keys: {required_keys}. "
            f"Keep reasoning brief and output valid JSON immediately."
        )
        for model_name in ["openai-fast", "openai"]:
            try:
                oa_payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system_instruction + schema_hint},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": GEMINI_TEMPERATURE,
                }
                resp = requests.post(FREE_LLM_ENDPOINT, json=oa_payload, timeout=45)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                msg = data["choices"][0]["message"]
                content = msg.get("content") or ""
                reasoning = msg.get("reasoning") or ""
                parsed = _extract_json_object(content) or _extract_json_object(reasoning)
                if parsed:
                    if reasoning and not parsed.get("thinking_process"):
                        parsed["thinking_process"] = reasoning[:350]
                    print(f"[LLM Thinking ({model_name})] Đã suy luận & thiết kế kịch bản thành công!")
                    return parsed
            except Exception as e:
                continue
        print(" [LLM Info] Endpoint miễn phí đang bận -> Kích hoạt Kiến trúc sư Kịch bản 4 Cảnh Nội bộ.")

    return None
