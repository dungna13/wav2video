"""
NODE 3: `prompt_scorer_node` — Giám khảo kịch bản 2 lớp.
  Lớp 1 (tất định, 0 token): kiểm tra cứng bằng code — số cảnh, số từ, chữ số/ký hiệu (TTS đọc sai), từ cấm hình ảnh
          (chart/cartoon/...), hook yếu, sáo ngữ, camera lặp, vi phạm `intent_mode`.
  Lớp 2 (LLM critic, `prompts/scorer_prompt.py`): chấm hook / độ khớp hình-lời / mạch kể khi lớp 1 không có lỗi nặng.
Trước đây node này luôn trả điểm cố định 9.x nên không bao giờ chặn được kịch bản kém; nay phản hồi nêu đích danh cảnh lỗi
để `prompt_architect_node` viết lại đúng chỗ.
"""

import re
from typing import Dict, Any, List, Tuple

from config.settings import MIN_AVERAGE_SCORE, MAX_PROMPT_RETRIES
from prompts.scorer_prompt import render_scorer_prompt
from graph.llm_client import call_gemini_thinking_structured, SCORER_GEMINI_SCHEMA
from graph.state import ChristianVideoState

BANNED_VISUAL_TERMS = [
    "chart", "graph", "diagram", "infographic", "axis", "equation", "formula", "ui", "slide", "presentation",
    "cartoon", "anime", "pixar", "disney", "3d render", "illustration", "clipart", "vector", "neon",
    "fireflies", "magic particles", "caption", "watermark", "logo", "text overlay", "on-screen text",
]
HUMAN_WORDS = [
    "man", "men", "woman", "women", "people", "person", "human", "soldier", "soldiers", "crowd", "child", "children",
    "worker", "workers", "farmer", "hands", "hand", "face", "portrait", "figure", "silhouette", "pilot", "doctor",
    "student", "family", "villagers", "troops", "fighter", "fighters", "miner", "miners", "driver", "boy", "girl",
    "couple", "runner", "walker",
]
BAD_OPENERS = ("bạn có biết", "hôm nay", "trong video này", "hãy cùng", "xin chào", "chào mừng", "chào các bạn", "chào mọi người")
CLICHES = ["hành trình", "hạt mầm", "ánh sáng cuối", "cuộc sống là", "hãy luôn", "mỗi chúng ta", "bài học đắt giá"]
BANNED_ABBREV_PATTERNS = (
    r"\btp\.?\s*hcm\b",
    r"\bkm/h\b",
    r"\bm/s\b",
    r"\bvd\b",
    r"\bv\.v\.",
    r"\busd\b",
    r"\bvnd\b",
)
VALID_GENRES = frozenset({
    "history_war", "history_culture", "science_nature", "economics_business",
    "psychology_philosophy", "true_story_crime", "tech_future", "lifestyle_motivation",
})
VALID_MUSIC_MOODS = frozenset({
    "tense_epic", "solemn_cinematic", "wonder_ambient", "driving_modern",
    "reflective_piano", "suspense_dark", "uplifting_soft",
})
VALID_CAMERAS = frozenset({"zoom_in", "zoom_out", "pan_left", "pan_right", "tilt_up", "tilt_down"})


def _has_word(text: str, words: List[str]) -> bool:
    low = text.lower()
    return any(re.search(rf"\b{re.escape(w)}\b", low) for w in words)


def rule_check(
    scenes: List[Dict[str, Any]],
    intent_mode: str,
    genre: str = "",
    music_mood: str = "",
    style_anchor_en: str = "",
) -> Tuple[float, List[str], List[str]]:
    """Trả về (điểm 1-10, lỗi nặng, lỗi nhẹ)."""
    hard: List[str] = []
    soft: List[str] = []
    n = len(scenes)
    total_words = sum(len(s["narration_vn"].split()) for s in scenes)

    if genre and genre not in VALID_GENRES:
        soft.append(f"genre '{genre}' chưa nằm trong 8 thể loại chuẩn.")
    if music_mood and music_mood not in VALID_MUSIC_MOODS:
        soft.append(f"music_mood '{music_mood}' chưa nằm trong 7 mood chuẩn.")
    if style_anchor_en:
        sw = len(style_anchor_en.split())
        if sw < 20 or sw > 55:
            soft.append(f"style_anchor_en có {sw} từ (nên 30–45 từ).")

    if n < 6 or n > 10:
        hard.append(f"Số cảnh = {n}, cần 7–9 cảnh.")
    elif n < 7 or n > 9:
        soft.append(f"Số cảnh = {n}, nên 7–9.")
    if total_words < 110 or total_words > 220:
        hard.append(f"Tổng lời bình {total_words} từ, cần 140–190 từ (video 50–65 giây).")
    elif total_words < 135 or total_words > 195:
        soft.append(f"Tổng lời bình {total_words} từ, nên 140–190.")

    human_scenes = 0
    for i, s in enumerate(scenes, 1):
        narr, img = s["narration_vn"], s["image_prompt_en"]
        stock_q = str(s.get("stock_query_en", "")).strip()
        overlay = str(s.get("overlay_keyword_vn", "")).strip()
        cam = str(s.get("camera", "")).strip()
        nw, iw = len(narr.split()), len(img.split())
        if nw < 6 or nw > 30:
            soft.append(f"Cảnh {i}: lời bình {nw} từ, cần 8–24 từ/cảnh.")
        if re.search(r"\d|[%$€₫&#@+=/*]", narr):
            soft.append(f"Cảnh {i}: có chữ số/ký hiệu trong lời bình — viết bằng chữ để TTS đọc đúng.")
        if any(re.search(pat, narr, flags=re.IGNORECASE) for pat in BANNED_ABBREV_PATTERNS):
            soft.append(f"Cảnh {i}: chứa từ viết tắt/đơn vị (km/h, TP.HCM, USD...) — viết thành chữ để TTS đọc chuẩn.")
        if iw < 14 or iw > 70:
            hard.append(f"Cảnh {i}: image_prompt_en {iw} từ, cần 22–40 từ mô tả MỘT ảnh cụ thể.")
        hit = [t for t in BANNED_VISUAL_TERMS if re.search(rf"\b{re.escape(t)}\b", img.lower())]
        if hit:
            hard.append(f"Cảnh {i}: image_prompt_en chứa từ cấm {hit}; phải là ảnh chụp tài liệu chân thực.")
        for c in CLICHES:
            if c in narr.lower():
                soft.append(f"Cảnh {i}: sáo ngữ '{c}' — thay bằng chi tiết cụ thể.")
        if cam and cam not in VALID_CAMERAS:
            soft.append(f"Cảnh {i}: camera '{cam}' không hợp lệ.")
        if stock_q:
            sq_words = len(stock_q.split())
            if sq_words < 2 or sq_words > 5:
                soft.append(f"Cảnh {i}: stock_query_en có {sq_words} từ (nên 2–4 từ tiếng Anh).")
        if overlay and len(overlay.split()) > 5:
            soft.append(f"Cảnh {i}: overlay_keyword_vn dài hơn 5 từ ('{overlay}').")
        has_human = _has_word(img, HUMAN_WORDS)
        human_scenes += int(has_human)
        if intent_mode == "NO_HUMAN_BROLL" and has_human:
            hard.append(f"Cảnh {i}: chế độ NO_HUMAN_BROLL nhưng ảnh có người; đổi sang vật thể/địa điểm.")

    if intent_mode != "NO_HUMAN_BROLL" and n and human_scenes / n < 0.6:
        hard.append(f"Chế độ có người nhưng chỉ {human_scenes}/{n} cảnh có người (cần ≥ 60%).")

    if scenes:
        hook = scenes[0]["narration_vn"]
        if len(hook.split()) > 16:
            soft.append(f"Hook dài {len(hook.split())} từ, cần ≤ 14 từ và gây sốc/tò mò.")
        if hook.lower().startswith(BAD_OPENERS):
            hard.append("Hook mở bằng câu cấm ('Bạn có biết', 'Hôm nay', chào hỏi...).")
    for i in range(1, n):
        if scenes[i]["camera"] == scenes[i - 1]["camera"]:
            soft.append(f"Cảnh {i}-{i + 1}: camera lặp liền kề.")

    score = max(1.0, 10.0 - 1.5 * len(hard) - 0.4 * len(soft))
    return round(score, 2), hard, soft


def _scenes_block(scenes: List[Dict[str, Any]]) -> str:
    return "\n".join(
        f"[Cảnh {i}] camera={s.get('camera', '')} | stock={s.get('stock_query_en', '')}\n   LỜI: {s['narration_vn']}\n   ẢNH: {s['image_prompt_en']}"
        for i, s in enumerate(scenes, 1)
    )


def prompt_scorer_node(state: ChristianVideoState) -> Dict[str, Any]:
    scenes = state.get("scenes") or []
    mode = state.get("effective_intent_mode") or state.get("intent_mode") or "NO_HUMAN_BROLL"
    retry_count = state.get("retry", 0)

    rule_score, hard, soft = rule_check(
        scenes,
        mode,
        genre=str(state.get("genre", "")).strip(),
        music_mood=str(state.get("music_mood", "")).strip(),
        style_anchor_en=str(state.get("style_anchor_en", "")).strip(),
    )
    hook = visual = story = rule_score
    critic_feedback = ""
    critic_used = False

    rendered = render_scorer_prompt(
        user_request=state.get("user_request", ""),
        intent_mode=mode,
        genre=state.get("genre", ""),
        topic_title=state.get("topic_title", ""),
        style_anchor_en=state.get("style_anchor_en", ""),
        scenes_block=_scenes_block(scenes),
    )

    if not hard:
        critic = call_gemini_thinking_structured(
            prompt=rendered,
            response_schema=SCORER_GEMINI_SCHEMA,
            system_instruction="Bạn là biên tập viên phim tài liệu ngắn khắt khe. Trả về DUY NHẤT 1 JSON Object theo schema.",
        )
        if critic and "visual_match_score" in critic:
            try:
                hook = round(0.5 * rule_score + 0.5 * float(critic["hook_score"]), 2)
                visual = round(0.5 * rule_score + 0.5 * float(critic["visual_match_score"]), 2)
                story = round(0.5 * rule_score + 0.5 * float(critic["story_score"]), 2)
                critic_feedback = str(critic.get("feedback_for_rewrite", "")).strip()
                critic_used = True
            except (TypeError, ValueError):
                pass

    weighted_avg = round(0.30 * hook + 0.35 * visual + 0.35 * story, 2)
    pass_val = (not hard) and weighted_avg >= MIN_AVERAGE_SCORE and visual >= MIN_AVERAGE_SCORE

    feedback_lines = hard + soft
    if critic_feedback:
        feedback_lines.append(critic_feedback)
    feedback = " | ".join(feedback_lines)

    print(
        f"[Node 3: prompt_scorer_node] Điểm: {weighted_avg}/10 (Hook={hook}, Khớp hình-lời={visual}, Mạch kể={story}) "
        f"| LLM critic={'có' if critic_used else 'không'} | lỗi nặng={len(hard)} nhẹ={len(soft)} | Pass={pass_val}"
    )
    if not pass_val and feedback:
        print(f"   └─ Phản hồi gửi lại Architect: {feedback[:400]}")

    return {
        "rendered_scorer_prompt": rendered,
        "rag_faithfulness_score": story,
        "cinematic_quality_score": visual,
        "theological_moral_score": hook,
        "average_score": weighted_avg,
        "pass_validation": pass_val,
        "prompt_feedback": "" if pass_val else feedback,
        "retry": retry_count + 1,
    }


def should_retry_prompt(state: ChristianVideoState) -> str:
    if state.get("pass_validation", False):
        return "media_generator_node"
    if state.get("retry", 0) >= MAX_PROMPT_RETRIES:
        return "media_generator_node"
    return "prompt_architect_node"
