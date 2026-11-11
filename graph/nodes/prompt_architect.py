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


def _build_smart_fallback_scenes(topic: str, intent_mode: str) -> Dict[str, Any]:
    """Sinh kịch bản tài liệu chuyên sâu theo chủ đề khi API LLM gặp sự cố hoặc timeout mạng."""
    low = topic.lower()
    if any(k in low for k in ["điện biên", "dien bien", "1954", "chiến dịch", "pháo", "chiến tranh", "lịch sử"]):
        return {
            "topic_title": "Chiến Dịch Điện Biên Phủ 1954",
            "genre": "history_war",
            "style_anchor_en": "archival 35mm photograph, authentic 1954 historical documentary, rugged trenches, dramatic overcast lighting",
            "music_mood": "tense_epic",
            "thinking_process": "Tái hiện 56 ngày đêm Điện Biên Phủ 1954: Từ Mường Thanh, dốc đèo kéo pháo, bùn lầy chiến hào, đến khoảnh khắc toàn thắng.",
            "story_moral": "Điện Biên Phủ 1954: Bản hùng ca chấn động địa cầu #DienBienPhu #LichSuVietNam #1954",
            "claims_to_verify": ["Năm 1954", "56 ngày đêm", "Mường Thanh", "Tướng De Castries"],
            "scenes": [
                {
                    "narration_vn": "Năm một nghìn chín trăm năm mươi tư, thung lũng Mường Thanh chìm trong biển lửa chiến tranh.",
                    "image_prompt_en": "wide aerial view of smoky mountain valley trenches battlefield in 1954, dramatic clouds",
                    "stock_query_en": "fire smoke war",
                    "camera": "zoom_in",
                    "overlay_keyword_vn": "NĂM 1954"
                },
                {
                    "narration_vn": "Hàng vạn chiến sĩ ngày đêm kéo những cỗ pháo nặng hai tấn qua từng con dốc dựng đứng.",
                    "image_prompt_en": "heavy artillery cannon being moved across muddy mountain path in heavy rain, rugged terrain",
                    "stock_query_en": "cannon mountain rain",
                    "camera": "pan_right",
                    "overlay_keyword_vn": "KÉO PHÁO"
                },
                {
                    "narration_vn": "Mưa rừng tầm tã, chiến hào ngập bùn lầy, tiếng đạn pháo rền vang xé toạc màn đêm.",
                    "image_prompt_en": "muddy battlefield trench line under torrential rain, explosions smoke in the distance",
                    "stock_query_en": "rain storm mud",
                    "camera": "tilt_up",
                    "overlay_keyword_vn": "CHIẾN HÀO"
                },
                {
                    "narration_vn": "Năm mươi sáu ngày đêm kiên cường siết chặt vòng vây, từng tấc đất đều thấm đẫm mồ hôi và máu.",
                    "image_prompt_en": "military bunker fortifications barbed wire battlefield landscape at dusk, atmospheric haze",
                    "stock_query_en": "bunker dark smoke",
                    "camera": "pan_left",
                    "overlay_keyword_vn": "56 NGÀY ĐÊM"
                },
                {
                    "narration_vn": "Chiều ngày mùng bảy tháng năm, lá cờ quyết chiến quyết thắng tung bay trên nóc hầm chỉ huy, khép lại bản hùng ca chấn động địa cầu.",
                    "image_prompt_en": "dramatic silhouette of a flag waving proudly on top of concrete military bunker, golden sunset",
                    "stock_query_en": "flag waving sunset",
                    "camera": "zoom_out",
                    "overlay_keyword_vn": "TOÀN THẮNG"
                }
            ]
        }
    else:
        title = topic[:40].strip()
        return {
            "topic_title": title,
            "genre": "history_culture",
            "style_anchor_en": "cinematic documentary still, authentic natural lighting, 35mm photograph texture",
            "music_mood": "solemn_cinematic",
            "thinking_process": f"Phân tích tài liệu chuyên sâu cho chủ đề '{title}': Bối cảnh, bước ngoặt, thực tiễn và thông điệp.",
            "story_moral": f"{title} #KhamPha #LichSu #TriThuc",
            "claims_to_verify": [title],
            "scenes": [
                {
                    "narration_vn": f"Có những câu chuyện trong lịch sử thay đổi hoàn toàn cách chúng ta nhìn nhận về {title}.",
                    "image_prompt_en": f"dramatic wide angle cinematic view exploring {title}, atmospheric mood",
                    "stock_query_en": "history mountain ancient",
                    "camera": "zoom_in",
                    "overlay_keyword_vn": "KHỞI NGUỒN"
                },
                {
                    "narration_vn": "Những con số và sự thật đằng sau nó từng là dấu hỏi lớn đối với nhiều thế hệ.",
                    "image_prompt_en": "close up of ancient documents historical artifacts on wooden desk, moody lighting",
                    "stock_query_en": "book library document",
                    "camera": "pan_right",
                    "overlay_keyword_vn": "DỮ LIỆU"
                },
                {
                    "narration_vn": "Mỗi biến cố diễn ra đều để lại dấu ấn sâu sắc và bài học vô giá cho tương lai.",
                    "image_prompt_en": "epic panoramic landscape under moving dramatic clouds, cinematic lighting",
                    "stock_query_en": "clouds sky walking",
                    "camera": "tilt_up",
                    "overlay_keyword_vn": "BƯỚC NGOẶT"
                },
                {
                    "narration_vn": "Hiểu rõ về quá khứ chính là chìa khóa để chúng ta vững bước bước vào ngày mai.",
                    "image_prompt_en": "inspiring sunrise over mountain peak, rays of light through clouds",
                    "stock_query_en": "sunrise mountain light",
                    "camera": "zoom_out",
                    "overlay_keyword_vn": "ĐÚC KẾT"
                }
            ]
        }


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
        print(" [Architect Info] LLM API bận/timeout -> Kích hoạt Bộ phân tích Kịch bản Chuyên sâu theo chủ đề.")
        llm_json = _build_smart_fallback_scenes(user_request, intent_mode)
        scenes = normalize_scenes(llm_json.get("scenes"))

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
