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
from prompts.narrative_models import VALID_NARRATIVE_MODELS
from prompts.scorer_prompt import render_scorer_prompt
from graph.book_rag import compute_groundedness_local
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
VALID_SFX_CUES = frozenset({
    "none", "low_thud", "subtle_whoosh", "camera_click", "wind_swell",
    "deep_sub_drop", "heartbeat_pulse", "clock_tick_stop",
})


def _has_word(text: str, words: List[str]) -> bool:
    low = text.lower()
    return any(re.search(rf"\b{re.escape(w)}\b", low) for w in words)


def rule_check(
    scenes: List[Dict[str, Any]],
    intent_mode: str,
    genre: str = "",
    music_mood: str = "",
    style_anchor_en: str = "",
    narrative_model: str = "",
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
    if narrative_model and narrative_model not in VALID_NARRATIVE_MODELS:
        soft.append(f"narrative_model '{narrative_model}' chưa nằm trong 13 mô hình chuẩn.")
    if style_anchor_en:
        sw = len(style_anchor_en.split())
        if sw < 20 or sw > 55:
            soft.append(f"style_anchor_en có {sw} từ (nên 30–45 từ).")
        sl = style_anchor_en.lower()
        if not any(tok in sl for tok in ("lower third", "captions", "upper-center", "negative space")):
            soft.append("style_anchor_en thiếu chỉ dẫn safe-zone 9:16 (chừa 1/3 dưới thoáng tối cho phụ đề).")

    if n < 6 or n > 11:
        hard.append(f"Số cảnh = {n}, cần 8–10 cảnh.")
    elif n < 8 or n > 10:
        soft.append(f"Số cảnh = {n}, nên 8–10.")
    if total_words < 105 or total_words > 215:
        hard.append(f"Tổng lời bình {total_words} từ, cần 130–185 từ (video 45–60 giây).")
    elif total_words < 130 or total_words > 185:
        soft.append(f"Tổng lời bình {total_words} từ, nên 130–185.")

    human_scenes = 0
    overlay_count = 0
    sfx_count = 0
    short_twist_count = 0

    for i, s in enumerate(scenes, 1):
        narr, img = s["narration_vn"], s["image_prompt_en"]
        sub = str(s.get("subtitle_vn", "")).strip()
        stock_q = str(s.get("stock_query_en", "")).strip()
        overlay = str(s.get("overlay_keyword_vn", "")).strip()
        cam = str(s.get("camera", "")).strip()
        sfx = str(s.get("sfx_cue", "none") or "none").strip()
        nw, iw = len(narr.split()), len(img.split())
        if not sub:
            soft.append(f"Cảnh {i}: thiếu subtitle_vn cho hiển thị màn hình.")
        if 1 < i < n and 7 <= nw <= 12:
            short_twist_count += 1
        elif 1 < i < n and (nw < 7 or nw > 22):
            soft.append(f"Cảnh {i}: lời bình {nw} từ (nên 13–20 từ, hoặc 7–12 từ cho Twist).")
        if i == n and (nw < 8 or nw > 16):
            soft.append(f"Cảnh {i} (Kết): {nw} từ, nên 10–14 từ chốt dứt khoát.")
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
        if overlay:
            overlay_count += 1
            if len(overlay.split()) > 5:
                soft.append(f"Cảnh {i}: overlay_keyword_vn dài hơn 5 từ ('{overlay}').")
        if sfx not in VALID_SFX_CUES:
            soft.append(f"Cảnh {i}: sfx_cue '{sfx}' không hợp lệ.")
        elif sfx != "none":
            sfx_count += 1
        vst = str(s.get("visual_source_type", "") or "").strip().lower()
        rmq = str(s.get("real_media_query", "") or "").strip()
        if vst == "real_photo" and not rmq:
            soft.append(f"Cảnh {i}: visual_source_type là 'real_photo' nhưng thiếu real_media_query.")
        has_human = _has_word(img, HUMAN_WORDS)
        human_scenes += int(has_human)
        if intent_mode == "NO_HUMAN_BROLL" and has_human and vst != "real_photo":
            hard.append(f"Cảnh {i}: chế độ NO_HUMAN_BROLL nhưng ảnh có người; đổi sang vật thể/địa điểm.")

    if n >= 5 and short_twist_count == 0:
        soft.append("Thiếu biến thiên nhịp câu: chưa có cảnh Twist ngắn gắt (7–12 từ) ở giữa phim.")
    if overlay_count > 4:
        soft.append(f"Có {overlay_count} cảnh gắn overlay_keyword_vn (chỉ nên 3–4 cảnh neo).")
    if sfx_count > 3:
        soft.append(f"Có {sfx_count} cảnh gắn sfx_cue (chỉ nên 2–3 điểm chuyển nhịp).")

    if intent_mode != "NO_HUMAN_BROLL" and n and human_scenes / n < 0.6:
        hard.append(f"Chế độ có người nhưng chỉ {human_scenes}/{n} cảnh có người (cần ≥ 60%).")

    if scenes:
        hook = scenes[0]["narration_vn"]
        if len(hook.split()) > 13:
            soft.append(f"Hook dài {len(hook.split())} từ, cần 6–11 từ và gây sốc/tò mò.")
        if hook.lower().startswith(BAD_OPENERS):
            hard.append("Hook mở bằng câu cấm ('Bạn có biết', 'Hôm nay', chào hỏi...).")
    for i in range(1, n):
        if scenes[i]["camera"] == scenes[i - 1]["camera"]:
            soft.append(f"Cảnh {i}-{i + 1}: camera lặp liền kề.")

    score = max(1.0, 10.0 - 1.5 * len(hard) - 0.4 * len(soft))
    return round(score, 2), hard, soft


def _scenes_block(scenes: List[Dict[str, Any]]) -> str:
    return "\n".join(
        f"[Cảnh {i}] src={s.get('visual_source_type', 'stock_video')} | real_q={s.get('real_media_query', '')} "
        f"| camera={s.get('camera', '')} | stock={s.get('stock_query_en', '')} | sfx={s.get('sfx_cue', 'none')} "
        f"| bgm={s.get('bgm_energy', 'rise')} | vocal={s.get('vocal_delivery', 'normal_story')} | kw={s.get('overlay_keyword_vn', '')}\n"
        f"   LỜI TTS: {s['narration_vn']}\n"
        f"   PHỤ ĐỀ: {s.get('subtitle_vn', s['narration_vn'])}\n"
        f"   ẢNH: {s['image_prompt_en']}"
        for i, s in enumerate(scenes, 1)
    )


def prompt_scorer_node(state: ChristianVideoState) -> Dict[str, Any]:
    scenes = state.get("scenes") or []
    mode = state.get("effective_intent_mode") or state.get("intent_mode") or "NO_HUMAN_BROLL"
    retry_count = state.get("retry", 0)
    narrative_model = str(state.get("narrative_model", "abt") or "abt").strip().lower()

    rule_score, hard, soft = rule_check(
        scenes,
        mode,
        genre=str(state.get("genre", "")).strip(),
        music_mood=str(state.get("music_mood", "")).strip(),
        style_anchor_en=str(state.get("style_anchor_en", "")).strip(),
        narrative_model=narrative_model,
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
        narrative_model=narrative_model,
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

    groundedness = 1.0
    weak_scenes: List[int] = []
    retry_target = ""
    rag_retry_count = int(state.get("rag_retry_count", 0) or 0)
    book_id = str(state.get("book_id", "") or "").strip()
    retrieved_ctx = str(state.get("retrieved_scripture", "") or "").strip()
    if book_id and retrieved_ctx:
        groundedness, weak_scenes = compute_groundedness_local(scenes, retrieved_ctx)
        if groundedness < 0.62 and weak_scenes:
            msg = (
                f"Cảnh {weak_scenes}: chưa bám sát đoạn sách đã trích "
                f"(Local Groundedness={groundedness:.2f}); cần dùng đúng tình tiết trong đoạn sách hoặc tìm lại chunk khác."
            )
            if (
                len(weak_scenes) >= max(3, len(scenes) // 2)
                and rag_retry_count < 3
                and int(state.get("book_chunk_idx", 0) or 0) == 0
            ):
                retry_target = "retry_rag"
                hard.append(msg)
            else:
                soft.append(msg)

    pass_val = (not hard) and weighted_avg >= MIN_AVERAGE_SCORE and visual >= MIN_AVERAGE_SCORE and groundedness >= 0.55

    feedback_lines = hard + soft
    if critic_feedback:
        feedback_lines.append(critic_feedback)
    feedback = " | ".join(feedback_lines)

    ground_log = f" | Ground={groundedness:.2f}" if (book_id and retrieved_ctx) else ""
    print(
        f"[Node 3: prompt_scorer_node] Điểm: {weighted_avg}/10 (Hook={hook}, Khớp hình-lời={visual}, Mạch kể={story}{ground_log}) "
        f"| LLM critic={'có' if critic_used else 'không'} | lỗi nặng={len(hard)} nhẹ={len(soft)} | Pass={pass_val}"
    )
    if not pass_val and feedback:
        print(f"   └─ Phản hồi gửi lại {'QueryRewriter (RAG)' if retry_target == 'retry_rag' else 'Architect'}: {feedback[:400]}")

    return {
        "rendered_scorer_prompt": rendered,
        "rag_faithfulness_score": round(story * groundedness, 2) if (book_id and retrieved_ctx) else story,
        "script_groundedness_score": groundedness,
        "cinematic_quality_score": visual,
        "theological_moral_score": hook,
        "average_score": weighted_avg,
        "pass_validation": pass_val,
        "prompt_feedback": "" if pass_val else feedback,
        "retry_target": "" if pass_val else retry_target,
        "retry": retry_count if retry_target == "retry_rag" else (retry_count + 1),
    }


def should_retry_prompt(state: ChristianVideoState) -> str:
    if state.get("pass_validation", False):
        return "media_generator_node"
    if state.get("retry_target") == "retry_rag" and int(state.get("rag_retry_count", 0) or 0) < 3:
        return "retry_rag"
    if state.get("retry", 0) >= MAX_PROMPT_RETRIES:
        return "media_generator_node"
    return "prompt_architect_node"
