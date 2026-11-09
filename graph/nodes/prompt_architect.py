"""
NODE 2: `prompt_architect_node` (LLM Suy Luận Thinking & Thiết Kế Nhân Vật + Bối Cảnh + 4 Phân Cảnh 3D Từ A-Z)
Nhận bất kỳ Topic nào từ `user_request`, gọi LLM để tự động:
  1. Suy luận Chain-of-Thought (`thinking_process`) để tìm ẩn dụ thị giác đắt giá nhất.
  2. Tự động khởi tạo Nhân vật chính cố định (`new_characters` - Character Bible) ngay cả khi người dùng chưa có nhân vật sẵn.
  3. Chọn Thực thể Hoạt hình 3D chuyển động ở Tiền cảnh (`visual_archetype`) + 4 Nhãn phân cảnh (`visual_labels`).
  4. Thiết kế Prompt Lưới 4 Phân cảnh 2x2 (`scene_action_prompt`) và Kịch bản lồng tiếng 3 phần sâu sắc.
"""

from typing import Dict, List, Any
from prompts.architect_prompt import PROMPT_ARCHITECT_TEMPLATE
from graph.llm_client import call_gemini_thinking_structured, ARCHITECT_GEMINI_SCHEMA
from graph.guardrails import to_ascii_slug
from graph.state import (
    ChristianVideoState,
    CharacterProfile,
)


VALID_ARCHETYPES = {
    "butterfly_chaos_wings",
    "cosmic_orbital_spheres",
    "chrono_hourglass_gears",
    "soul_lantern_ascension",
}


def _infer_best_archetype(topic_text: str, raw_arch: str) -> str:
    if raw_arch in VALID_ARCHETYPES:
        return raw_arch
    low = (topic_text + " " + raw_arch).lower()
    if any(k in low for k in ["bướm", "hỗn loạn", "butterfly", "chaos", "thay đổi", "nhân quả"]):
        return "butterfly_chaos_wings"
    if any(k in low for k in ["thời gian", "lịch sử", "đồng hồ", "tuổi", "kỷ luật", "time", "chrono"]):
        return "chrono_hourglass_gears"
    if any(k in low for k in ["tâm hồn", "cảm xúc", "chữa lành", "hạnh phúc", "cô đơn", "lantern", "soul"]):
        return "soul_lantern_ascension"
    return "cosmic_orbital_spheres"


def prompt_architect_node(state: ChristianVideoState) -> Dict[str, Any]:
    user_request = state.get("user_request", "").strip()
    filtered_character_context = state.get("filtered_character_context", "Chưa có nhân vật sẵn - Hãy tự thiết kế 1 Nhân vật chính cố định.")
    prompt_feedback = state.get("prompt_feedback", "") or "Không có phản hồi lỗi."

    rendered_prompt = PROMPT_ARCHITECT_TEMPLATE.format(
        user_request=user_request,
        filtered_character_context=filtered_character_context,
        prompt_feedback=prompt_feedback,
    )

    llm_json = call_gemini_thinking_structured(
        prompt=rendered_prompt,
        response_schema=ARCHITECT_GEMINI_SCHEMA,
    )

    if llm_json and llm_json.get("hook_and_context_vn"):
        topic_title = llm_json.get("topic_title", user_request[:42]).strip()
        thinking_process = llm_json.get("thinking_process", "").strip()
        visual_archetype = _infer_best_archetype(user_request, str(llm_json.get("visual_archetype", "")).strip())

        raw_labels = llm_json.get("visual_labels") or []
        visual_labels = [str(x).strip() for x in raw_labels[:4] if str(x).strip()]
        default_labels = [
            "Cảnh 1: Khoảnh khắc Khởi nguồn",
            "Cảnh 2: Sóng Năng lượng Lan tỏa",
            "Cảnh 3: Cao trào Biến đổi Vũ trụ",
            "Cảnh 4: Bình minh Giác ngộ",
        ]
        while len(visual_labels) < 4:
            visual_labels.append(default_labels[len(visual_labels)])

        raw_new = llm_json.get("new_characters") or []
        if not raw_new:
            raw_new = [
                {
                    "key_name": "protagonist_seeker",
                    "aliases": ["Người Lữ Hành Ánh Sáng"],
                    "visual_traits": "young curious traveler wearing a glowing cobalt cloak and warm amber scarf, expressive eyes, 3D Pixar style",
                }
            ]

        char_traits = raw_new[0].get(
            "visual_traits",
            "young curious traveler wearing a glowing cobalt cloak and warm amber scarf, 3D Pixar style",
        )
        raw_scene_prompt = llm_json.get("scene_action_prompt", "").strip()
        if "2x2" not in raw_scene_prompt.lower() and "4-panel" not in raw_scene_prompt.lower():
            raw_scene_prompt = (
                f"A 2x2 4-panel grid storyboard of 3D Pixar and Makoto Shinkai anime masterpiece featuring {char_traits}: "
                f"{raw_scene_prompt}, volumetric god rays, rich vibrant colors, 8k, no text"
            )
        scene_action_prompt = " ".join(raw_scene_prompt.split()[:68])

        hook_vn = llm_json.get("hook_and_context_vn", "").strip()
        deep_vn = llm_json.get("deep_explanation_vn", "").strip()
        outro_vn = llm_json.get("outro_takeaway_vn", "").strip()
        story_moral = llm_json.get("story_moral", f"{topic_title} #3DAnimation #KhoaHoc #TrietLy").strip()
    else:
        topic_title = user_request[:42].strip()
        visual_archetype = _infer_best_archetype(user_request, "")
        thinking_process = (
            f"Bước 1 (Ẩn dụ): Chuyển hóa '{topic_title}' thành hành trình thị giác 4 hồi | "
            f"Bước 2 (Nhân vật): Thiết kế Người Lữ Hành Ánh Sáng mặc áo choàng xanh phát sáng | "
            f"Bước 3 (Chuyển động 3D): Thực thể {visual_archetype} bay xuyên qua 4 bối cảnh."
        )
        visual_labels = [
            "Cảnh 1: Khoảnh khắc Khởi nguồn",
            "Cảnh 2: Sóng Năng lượng Lan tỏa",
            "Cảnh 3: Cao trào Biến đổi Vũ trụ",
            "Cảnh 4: Bình minh Giác ngộ",
        ]
        raw_new = [
            {
                "key_name": "protagonist_seeker",
                "aliases": ["Người Lữ Hành Ánh Sáng"],
                "visual_traits": "young curious traveler wearing a glowing cobalt cloak and warm amber scarf, expressive eyes, 3D Pixar style",
            }
        ]
        scene_action_prompt = (
            f"A 2x2 4-panel grid storyboard of 3D Pixar and Makoto Shinkai anime masterpiece featuring a young traveler in glowing cobalt cloak: "
            f"Top-Left close-up reaching toward a glowing butterfly; Top-Right shockwave ripples across mystical forest; "
            f"Bottom-Left epic cosmic storm; Bottom-Right golden sunrise on mountain peak, 8k, no text"
        )
        hook_vn = (
            f"Bạn đã bao giờ tự hỏi, điều gì thực sự ẩn giấu đằng sau {user_request}? "
            f"Một khoảnh khắc nhỏ bé tưởng chừng vô tình, lại có thể khởi đầu cho cả một chuỗi biến đổi kỳ vĩ."
        )
        deep_vn = (
            f"Giống như những gợn sóng lan tỏa trong không gian, mỗi tác động nhỏ đều kết nối chặt chẽ với nhau, "
            f"tạo nên một bức tranh nhân quả sống động vượt xa trực giác thông thường của con người."
        )
        outro_vn = (
            f"Không có điều gì trong cuộc sống là hoàn toàn ngẫu nhiên hay vô nghĩa. "
            f"Mỗi lựa chọn nhỏ hôm nay của bạn, chính là hạt mầm kiến tạo nên tương lai."
        )
        story_moral = f"Khám phá câu chuyện đằng sau {topic_title} #3DAnimation #TrietLyCuocSong #KienThuc"

    new_chars_dict: Dict[str, CharacterProfile] = {}
    for item in raw_new:
        if isinstance(item, dict) and item.get("key_name"):
            kname = to_ascii_slug(item["key_name"])
            aliases = item.get("aliases") or [kname]
            new_chars_dict[aliases[0]] = {
                "key_name": kname,
                "name": aliases[0],
                "aliases": aliases,
                "visual_traits": " ".join(str(item.get("visual_traits", "")).split()[:32]),
                "reference_image_url": "",
                "seed": abs(hash(kname)) % 900000 + 100000,
            }

    full_script_summary = f"{hook_vn} {deep_vn} {outro_vn}"
    char_summary = ", ".join(f"{c['name']} ({c['visual_traits'][:45]}...)" for c in new_chars_dict.values())

    print(
        f"[Node 2: prompt_architect_node] Chủ đề: '{topic_title}'\n"
        f"   ├─ Suy luận Thinking : {thinking_process[:140]}...\n"
        f"   ├─ Nhân vật tự tạo   : {char_summary}\n"
        f"   └─ 3D Actor & 4 Cảnh : {visual_archetype} | {visual_labels}"
    )

    return {
        "topic_title": topic_title,
        "scripture_reference": topic_title,
        "retrieved_scripture": full_script_summary,
        "visual_archetype": visual_archetype,
        "visual_labels": visual_labels,
        "rendered_architect_prompt": rendered_prompt,
        "thinking_process": thinking_process,
        "scene_action_prompt": scene_action_prompt,
        "hook_and_context_vn": hook_vn,
        "deep_explanation_vn": deep_vn,
        "outro_takeaway_vn": outro_vn,
        "story_moral": story_moral,
        "new_characters": new_chars_dict,
    }
