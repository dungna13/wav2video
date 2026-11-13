"""
Bộ kiểm tra tất định (Deterministic Validator) & tiện ích xử lý JSON cho `ai_orchestrator`.

Chạy TRƯỚC LLM Critic trong `prompt_scorer_node` để bắt các lỗi có thể đo bằng code
(số cảnh, số từ, chữ số/ký hiệu TTS, từ cấm RULE #2/#3/#5, lặp camera, intent_mode)
tránh tốn chi phí gọi LLM khi kịch bản vi phạm quy tắc cứng.
"""

from __future__ import annotations

import copy
import json
import re
from typing import Any

from .narrative_models import VALID_NARRATIVE_MODELS

VALID_GENRES = frozenset({
    "history_war",
    "history_culture",
    "science_nature",
    "economics_business",
    "psychology_philosophy",
    "true_story_crime",
    "tech_future",
    "lifestyle_motivation",
})

VALID_MUSIC_MOODS = frozenset({
    "tense_epic",
    "solemn_cinematic",
    "wonder_ambient",
    "driving_modern",
    "reflective_piano",
    "suspense_dark",
    "uplifting_soft",
})

VALID_CAMERAS = frozenset({
    "zoom_in",
    "zoom_out",
    "pan_left",
    "pan_right",
    "tilt_up",
    "tilt_down",
})

VALID_SFX_CUES = frozenset({
    "none",
    "low_thud",
    "subtle_whoosh",
    "camera_click",
    "wind_swell",
    "deep_sub_drop",
    "heartbeat_pulse",
    "clock_tick_stop",
})

VALID_VOCAL_DELIVERIES = frozenset({
    "punch_urgent",
    "normal_story",
    "whisper_suspense",
    "solemn_slow",
})

VALID_VOICE_PROFILES = frozenset({
    "nam_tram_am",
    "nu_hoat_ngon",
    "nu_truyen_cam",
    "ai_hai_huoc",
})

VALID_BGM_ALIGNMENTS = frozenset({
    "empathetic",
    "anempathetic",
})

VALID_BGM_ENERGIES = frozenset({
    "low",
    "rise",
    "peak",
    "drop",
    "calm",
})

VALID_VISUAL_SOURCE_TYPES = frozenset({
    "real_photo",
    "stock_video",
    "ai_photo",
})

BANNED_HOOK_OPENERS = (
    "bạn có biết",
    "hôm nay",
    "trong video này",
    "hãy cùng khám phá",
    "xin chào",
    "chào mừng",
)

BANNED_CLICHES_VN = (
    "hành trình",
    "hạt mầm",
    "ánh sáng cuối đường hầm",
    "cuộc sống là",
    "hãy luôn",
    "mỗi chúng ta",
    "bài học đắt giá",
)

BANNED_IMAGE_TERMS_EN = (
    "chart",
    "graph",
    "diagram",
    "infographic",
    "axis",
    "equation",
    "formula",
    "ui",
    "slide",
    "presentation",
    "cartoon",
    "anime",
    "pixar",
    "disney",
    "3d render",
    "illustration",
    "clipart",
    "vector",
    "neon glow",
    "magic particles",
    "fireflies",
    "text",
    "caption",
    "watermark",
    "logo",
)

VISUAL_ESSAY_ALLOWED_IMAGE_TERMS_EN = frozenset({
    "chart",
    "graph",
    "diagram",
    "axis",
    "equation",
    "formula",
    "vector",
})

BANNED_HUMAN_TERMS_EN = (
    "person",
    "people",
    "man",
    "men",
    "woman",
    "women",
    "soldier",
    "soldiers",
    "crowd",
    "human",
    "child",
    "children",
    "worker",
    "workers",
    "face",
    "portrait",
)

BANNED_ABBREV_PATTERNS = (
    r"\btp\.?\s*hcm\b",
    r"\bkm/h\b",
    r"\bm/s\b",
    r"\bvd\b",
    r"\bv\.v\.",
    r"\busd\b",
    r"\bvnd\b",
)

_DIGIT_RE = re.compile(r"\d")
_SYMBOL_RE = re.compile(r"[%$€₫@#+=/*]")
_NON_VIET_CHAR_RE = re.compile(r"\b\w*[wzjfWZJF]\w*\b")
_UPPER_ACRONYM_RE = re.compile(r"\b[A-Z]{2,}\b")


def _count_words(text: str) -> int:
    return len([w for w in text.strip().split() if w and w not in ("--", "—", "...")])


def _find_word_matches(text: str, terms: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [
        term
        for term in terms
        if re.search(r"\b" + re.escape(term) + r"\b", lowered)
    ]


def parse_llm_json(raw_text: str) -> dict[str, Any]:
    """Tách và parse JSON object hợp lệ từ output của LLM (kể cả khi có markdown fence)."""
    cleaned = raw_text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned, flags=re.IGNORECASE)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    else:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            cleaned = cleaned[start : end + 1]
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("LLM output JSON must be an object.")
    return data


def build_full_image_prompt(image_prompt_en: str, style_anchor_en: str) -> str:
    """Gắn `style_anchor_en` vào `image_prompt_en` của từng cảnh theo RULE #6."""
    scene_part = image_prompt_en.strip().rstrip(",.")
    anchor_part = style_anchor_en.strip().lstrip(",.")
    if not anchor_part:
        return scene_part
    if not scene_part:
        return anchor_part
    return f"{scene_part}, {anchor_part}"


def apply_refined_narrations(
    script_data: dict[str, Any],
    refined_data: dict[str, Any],
) -> dict[str, Any]:
    """Cập nhật `narration_vn`, `subtitle_vn` và `story_moral` sau khi chạy `outro_moral_prompt`."""
    updated = copy.deepcopy(script_data)
    scenes = updated.get("scenes", [])
    for item in refined_data.get("refined_narrations", []):
        idx = int(item.get("scene_index", 0)) - 1
        text = str(item.get("narration_vn", "")).strip()
        sub = str(item.get("subtitle_vn", "")).strip()
        if 0 <= idx < len(scenes):
            if text:
                scenes[idx]["narration_vn"] = text
            if sub:
                scenes[idx]["subtitle_vn"] = sub
    new_moral = str(refined_data.get("story_moral", "")).strip()
    if new_moral:
        updated["story_moral"] = new_moral
    return updated


def validate_script_deterministic(
    script_data: dict[str, Any],
    intent_mode: str = "NO_HUMAN_BROLL",
) -> dict[str, Any]:
    """Kiểm tra toàn bộ rule tất định trên JSON kịch bản và trả về báo cáo lỗi."""
    errors: list[str] = []
    warnings: list[str] = []

    required_keys = (
        "topic_title",
        "genre",
        "style_anchor_en",
        "music_mood",
        "scenes",
        "story_moral",
        "claims_to_verify",
    )
    for key in required_keys:
        if key not in script_data:
            errors.append(f"Thiếu trường bắt buộc `{key}`.")

    genre = str(script_data.get("genre", "")).strip()
    if genre and genre not in VALID_GENRES:
        errors.append(f"`genre` không hợp lệ: '{genre}'.")

    music_mood = str(script_data.get("music_mood", "")).strip()
    if music_mood and music_mood not in VALID_MUSIC_MOODS:
        errors.append(f"`music_mood` không hợp lệ: '{music_mood}'.")

    voice_profile = str(script_data.get("voice_profile", "")).strip()
    if voice_profile and voice_profile not in VALID_VOICE_PROFILES:
        errors.append(f"`voice_profile` không hợp lệ: '{voice_profile}'.")

    bgm_alignment = str(script_data.get("bgm_alignment", "")).strip()
    if bgm_alignment and bgm_alignment not in VALID_BGM_ALIGNMENTS:
        errors.append(f"`bgm_alignment` không hợp lệ: '{bgm_alignment}'.")

    narrative_model = str(script_data.get("narrative_model", "")).strip()
    if narrative_model:
        if narrative_model not in VALID_NARRATIVE_MODELS:
            errors.append(f"`narrative_model` không hợp lệ: '{narrative_model}'.")
    else:
        warnings.append("Thiếu trường `narrative_model` (khuyến nghị chỉ định rõ mô hình kịch bản).")

    style_anchor = str(script_data.get("style_anchor_en", ""))
    style_words = _count_words(style_anchor)
    if style_words < 30 or style_words > 45:
        warnings.append(
            f"`style_anchor_en` có {style_words} từ (chuẩn RULE #6: 30–45 từ)."
        )
    style_lower = style_anchor.lower()
    if not any(tok in style_lower for tok in ("lower third", "captions", "upper-center", "negative space")):
        warnings.append(
            "`style_anchor_en` thiếu chỉ dẫn bố cục safe-zone 9:16 (chừa 1/3 dưới cho phụ đề)."
        )

    scenes = script_data.get("scenes")
    if not isinstance(scenes, list):
        errors.append("`scenes` phải là một danh sách (list).")
        return {
            "passed": False,
            "errors": errors,
            "warnings": warnings,
            "stats": {
                "scene_count": 0,
                "total_narration_words": 0,
                "narrative_model": narrative_model or "unspecified",
            },
            "feedback_for_rewrite": " | ".join(errors[:5]),
        }

    scene_count = len(scenes)
    if scene_count < 8 or scene_count > 10:
        errors.append(f"Số cảnh là {scene_count} (bắt buộc 8–10 cảnh).")

    total_narration_words = 0
    overlay_count = 0
    sfx_count = 0
    short_twist_count = 0
    prev_camera = ""
    prev_opener_words: tuple[str, ...] = ()

    for idx, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            errors.append(f"Cảnh {idx}: không phải JSON object hợp lệ.")
            continue

        narration = str(scene.get("narration_vn", "")).strip()
        subtitle = str(scene.get("subtitle_vn", "")).strip()
        image_prompt = str(scene.get("image_prompt_en", "")).strip()
        stock_query = str(scene.get("stock_query_en", "")).strip()
        camera = str(scene.get("camera", "")).strip()
        overlay = str(scene.get("overlay_keyword_vn", "")).strip()
        sfx_cue = str(scene.get("sfx_cue", "none")).strip() or "none"

        n_words = _count_words(narration)
        total_narration_words += n_words

        if not subtitle:
            warnings.append(f"Cảnh {idx}: thiếu `subtitle_vn` cho hiển thị màn hình.")

        if idx == 1:
            if n_words < 6 or n_words > 11:
                errors.append(f"Cảnh 1 (Hook): có {n_words} từ (bắt buộc 6–11 từ).")
            lower_hook = narration.lower()
            for opener in BANNED_HOOK_OPENERS:
                if lower_hook.startswith(opener):
                    errors.append(
                        f"Cảnh 1 (Hook): mở đầu cấm '{opener}' (vi phạm RULE #3)."
                    )
        elif idx == scene_count:
            if n_words < 10 or n_words > 14:
                warnings.append(
                    f"Cảnh {idx} (Kết): có {n_words} từ (khuyến nghị 10–14 từ để chốt dứt khoát)."
                )
        else:
            if 7 <= n_words <= 12:
                short_twist_count += 1
            elif n_words < 7 or n_words > 20:
                warnings.append(
                    f"Cảnh {idx}: `narration_vn` có {n_words} từ (khuyến nghị 13–20 từ, hoặc 7–12 từ cho Twist)."
                )

        if _DIGIT_RE.search(narration):
            errors.append(
                f"Cảnh {idx}: `narration_vn` chứa chữ số (vi phạm RULE #5 TTS)."
            )
        if _SYMBOL_RE.search(narration):
            errors.append(
                f"Cảnh {idx}: `narration_vn` chứa ký hiệu cấm TTS (% $ / + = ...)."
            )
        for abbr_pat in BANNED_ABBREV_PATTERNS:
            if re.search(abbr_pat, narration, flags=re.IGNORECASE):
                errors.append(
                    f"Cảnh {idx}: `narration_vn` chứa từ viết tắt/đơn vị cấm ({abbr_pat})."
                )
        acronyms = _UPPER_ACRONYM_RE.findall(narration)
        if acronyms:
            errors.append(
                f"Cảnh {idx}: `narration_vn` chứa từ viết tắt in hoa {', '.join(acronyms)} (vi phạm RULE #5 TTS)."
            )
        non_viet = _NON_VIET_CHAR_RE.findall(narration)
        if non_viet:
            warnings.append(
                f"Cảnh {idx}: nghi ngờ có từ tiếng Anh chưa phiên âm: {', '.join(non_viet)}."
            )

        lower_nar = narration.lower()
        for cliche in BANNED_CLICHES_VN:
            if cliche in lower_nar:
                warnings.append(
                    f"Cảnh {idx}: chứa sáo ngữ '{cliche}' (RULE #5)."
                )

        img_words = _count_words(image_prompt)
        if img_words < 22 or img_words > 40:
            warnings.append(
                f"Cảnh {idx}: `image_prompt_en` có {img_words} từ (chuẩn 22–40 từ)."
            )

        banned_imgs = _find_word_matches(image_prompt, BANNED_IMAGE_TERMS_EN)
        if narrative_model == "visual_math_essay":
            banned_imgs = [
                term for term in banned_imgs if term not in VISUAL_ESSAY_ALLOWED_IMAGE_TERMS_EN
            ]
        if banned_imgs:
            errors.append(
                f"Cảnh {idx}: `image_prompt_en` chứa từ cấm RULE #2: {', '.join(banned_imgs)}."
            )

        if intent_mode == "NO_HUMAN_BROLL":
            human_hits = _find_word_matches(image_prompt, BANNED_HUMAN_TERMS_EN)
            if human_hits:
                errors.append(
                    f"Cảnh {idx}: vi phạm `NO_HUMAN_BROLL` (có người: {', '.join(human_hits)})."
                )

        if camera not in VALID_CAMERAS:
            errors.append(f"Cảnh {idx}: `camera` không hợp lệ '{camera}'.")
        elif camera == prev_camera:
            errors.append(
                f"Cảnh {idx}: `camera` '{camera}' bị lặp lại liền kề với Cảnh {idx - 1}."
            )
        prev_camera = camera

        stock_words = _count_words(stock_query)
        if stock_words < 2 or stock_words > 4:
            warnings.append(
                f"Cảnh {idx}: `stock_query_en` có {stock_words} từ (chuẩn 2–4 từ)."
            )

        if overlay:
            overlay_count += 1
            if _count_words(overlay) > 3:
                warnings.append(
                    f"Cảnh {idx}: `overlay_keyword_vn` dài hơn 3 từ ('{overlay}')."
                )

        if sfx_cue not in VALID_SFX_CUES:
            errors.append(f"Cảnh {idx}: `sfx_cue` không hợp lệ '{sfx_cue}'.")
        elif sfx_cue != "none":
            sfx_count += 1

        bgm_energy = str(scene.get("bgm_energy", "")).strip()
        if bgm_energy and bgm_energy not in VALID_BGM_ENERGIES:
            errors.append(f"Cảnh {idx}: `bgm_energy` không hợp lệ '{bgm_energy}'.")

        vocal_delivery = str(scene.get("vocal_delivery", "")).strip()
        if vocal_delivery and vocal_delivery not in VALID_VOCAL_DELIVERIES:
            errors.append(f"Cảnh {idx}: `vocal_delivery` không hợp lệ '{vocal_delivery}'.")

        visual_source_type = str(scene.get("visual_source_type", "")).strip()
        real_media_query = str(scene.get("real_media_query", "")).strip()
        if visual_source_type and visual_source_type not in VALID_VISUAL_SOURCE_TYPES:
            errors.append(
                f"Cảnh {idx}: `visual_source_type` không hợp lệ '{visual_source_type}'."
            )
        if visual_source_type == "real_photo" and not real_media_query:
            warnings.append(
                f"Cảnh {idx}: `visual_source_type` là 'real_photo' nhưng thiếu `real_media_query`."
            )

        if overlay and sfx_cue != "none" and n_words > 18:
            warnings.append(
                f"Cảnh {idx}: vừa có `overlay_keyword_vn`, `sfx_cue` và câu dài {n_words} từ (>18) dễ gây quá tải nhận thức LC4MP."
            )

        clean_words = [re.sub(r"[^\wÀ-ỹ]", "", w.lower()) for w in narration.split() if re.sub(r"[^\wÀ-ỹ]", "", w.lower())]
        opener_words = tuple(clean_words[:2])
        if idx > 1 and len(opener_words) == 2 and opener_words == prev_opener_words:
            warnings.append(
                f"Cảnh {idx}: mở đầu lặp khung từ '{' '.join(opener_words)}' giống Cảnh {idx - 1} (dễ mòn tai)."
            )
        prev_opener_words = opener_words

        inner_text = narration[:-1] if len(narration) > 1 else narration
        if n_words >= 18 and not any(sep in inner_text for sep in (",", ";", ":", "--", "—", "...", "?", "!")):
            warnings.append(
                f"Cảnh {idx}: câu dài {n_words} từ thiếu dấu ngắt hơi giữa câu (nên thêm ',' hoặc '--' cho TTS)."
            )

    if short_twist_count == 0:
        warnings.append(
            "Thiếu biến thiên nhịp câu: chưa có cảnh Twist ngắn gắt (7–12 từ) ở giữa phim."
        )

    if overlay_count > 4:
        warnings.append(
            f"Có {overlay_count} cảnh gắn `overlay_keyword_vn` (khuyến nghị chỉ 3–4 cảnh neo để tránh rối mắt)."
        )

    if sfx_count > 3:
        warnings.append(
            f"Có {sfx_count} cảnh gắn `sfx_cue` (khuyến nghị chỉ 2–3 điểm chuyển nhịp)."
        )

    if total_narration_words < 130 or total_narration_words > 185:
        errors.append(
            f"Tổng số từ `narration_vn` là {total_narration_words} (bắt buộc 130–185 từ)."
        )

    passed = len(errors) == 0
    feedback = " | ".join(errors[:5]) if errors else ""

    return {
        "passed": passed,
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "scene_count": scene_count,
            "total_narration_words": total_narration_words,
            "style_anchor_words": style_words,
            "narrative_model": narrative_model or "unspecified",
        },
        "feedback_for_rewrite": feedback,
    }


def format_scenes_for_scorer(script_data: dict[str, Any]) -> str:
    """Định dạng danh sách cảnh thành `{scenes_block}` truyền vào `render_scorer_prompt`."""
    lines: list[str] = []
    for idx, scene in enumerate(script_data.get("scenes", []), start=1):
        lines.append(
            f"Cảnh {idx}:\n"
            f"  - narration_vn: {scene.get('narration_vn', '')}\n"
            f"  - subtitle_vn: {scene.get('subtitle_vn', '')}\n"
            f"  - image_prompt_en: {scene.get('image_prompt_en', '')}\n"
            f"  - stock_query_en: {scene.get('stock_query_en', '')}\n"
            f"  - visual_source_type: {scene.get('visual_source_type', '')}\n"
            f"  - real_media_query: {scene.get('real_media_query', '')}\n"
            f"  - camera: {scene.get('camera', '')}\n"
            f"  - overlay_keyword_vn: {scene.get('overlay_keyword_vn', '')}\n"
            f"  - sfx_cue: {scene.get('sfx_cue', 'none')}\n"
            f"  - bgm_energy: {scene.get('bgm_energy', 'calm')}"
        )
    return "\n".join(lines)


def format_scenes_for_outro_moral(script_data: dict[str, Any]) -> str:
    """Định dạng danh sách lời bình thành `{scenes_narration_block}` cho `render_outro_moral_prompt`."""
    lines: list[str] = []
    for idx, scene in enumerate(script_data.get("scenes", []), start=1):
        lines.append(
            f"Cảnh {idx}:\n"
            f"  - narration_vn: {scene.get('narration_vn', '')}\n"
            f"  - subtitle_vn: {scene.get('subtitle_vn', '')}"
        )
    return "\n".join(lines)
