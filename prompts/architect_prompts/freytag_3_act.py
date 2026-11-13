"""
Template prompt độc lập cho mô hình kịch bản `freytag_3_act` — Freytag's Pyramid / 3 Hồi.
"""

from __future__ import annotations

from ._shared import build_model_prompt_template, render_model_prompt_template

MODEL_ID = "freytag_3_act"
MODEL_NAME = "Freytag's Pyramid / 3 Hồi"
GROUP_LABEL = "Phim Tài liệu / Edutainment / Kể chuyện"
CORE_STRUCTURE = "Thiết lập -> Leo thang -> Cao trào -> Hạ nhiệt -> Kết cục"
BEST_FOR = "Kể chuyện nhân vật lịch sử, sự kiện dài, hưng thịnh và suy tàn"

BEAT_SHEET = """- **Cảnh 1 (HOOK — Khơi xung đột, 6–11 từ):** Chỉ thẳng vết nứt đầu tiên báo hiệu bi kịch hoặc bước ngoặt của cả thời đại.
- **Cảnh 2 (Hồi 1 — Thế cân bằng & Tham vọng):** Dựng lại thời kỳ hưng thịnh hoặc trật tự ban đầu cùng khát vọng khởi sinh.
- **Cảnh 3 (Hồi 1 — Biến cố châm ngòi & Open Loop):** Mối đe dọa hoặc tham vọng vượt giới hạn xuất hiện, để lửng câu hỏi về cái giá phải trả.
- **Cảnh 4 (Hồi 2 — Leo thang 1):** Các thế lực hoặc mâu thuẫn nội tại bắt đầu va chạm, trật tự cũ rạn nứt.
- **Cảnh 5 (Hồi 2 — Leo thang 2 & Open Loop):** Áp lực đẩy tới giới hạn chịu đựng ngay trước giờ quyết định.
- **Cảnh 6 (CAO TRÀO — Twist ngắn gắt 7–12 từ):** Khoảnh khắc đỉnh điểm định đoạt hoàn toàn thắng thua hoặc sự sụp đổ.
- **Cảnh 7 (Hồi 3 — Hạ nhiệt 1):** Phản ứng dây chuyền ngay sau cao trào khiến quyền lực hoặc cơ nghiệp cũ tan rã.
- **Cảnh 8 (Hồi 3 — Hạ nhiệt 2, tùy chọn đến Cảnh 9):** Cảnh vật, di vật hoặc nhân chứng còn lại khi cơn bão lịch sử vừa đi qua.
- **Cảnh cuối (Hồi 3 — Kết cục Callback 10–14 từ):** Chốt cục diện cuối cùng bằng hình ảnh biểu tượng nối về vết nứt ở Cảnh 1."""

MODEL_GUIDANCE = """1. **Kỹ thuật Hook Staccato 2 nhịp (không chữ số):**
   - Nhịp một gọi tên quyền lực/đỉnh cao; nhịp hai phơi bày dấu hiệu sụp đổ hay mầm bi kịch ngay trong lòng đỉnh cao ấy.
   - Ví dụ mẫu: *"Ngai vàng vừa dựng xong. Lưỡi dao đã kề sau gáy."* / *"Thành quách đứng vững nghìn thu. Chỉ sập từ bên trong."*
2. **Chiến lược Twist & Auditory Open Loop:**
   - Cuối Cảnh 3 và Cảnh 5 đặt cầu nối níu tai chuyển hồi mượt mà (vd: *"Vương triều tưởng như bất khả chiến bại -- cho tới đêm cổng thành tự mở."*).
   - Cảnh 6 là đỉnh kim tự tháp (7–12 từ), cô đặc đúng một hành động quyết định kết thúc bằng thanh **Trắc** (*gãy, tan, mất, cạn, đổi*).
3. **Kỹ thuật chốt `outro_style`:**
   - Chốt cục diện cuối của vòng cung 3 hồi bằng một hình ảnh biểu tượng còn sót lại (tro tàn, ấn triện, bức tường vỡ), đặt `--` trước cụm từ kết tạo dư âm lịch sử.
4. **Bẫy cần tránh của `freytag_3_act`:**
   - Kể tiểu sử theo kiểu liệt kê biên niên sử ("sinh năm..., lên ngôi năm..., mất năm...") thiếu trục xung đột.
   - Phần Hạ nhiệt (Cảnh 7–8) quá dài dòng hoặc lặp lại thông tin của Cao trào.
   - Đánh giá nhân vật lịch sử bằng lời bình luận đạo đức hiện đại thay vì để kết cục tự lên tiếng.
5. **Gợi ý nhịp CAM-WN (`vocal_delivery` / `bgm_energy` / `sfx_cue`):**
   - Cảnh 1 (Khơi xung đột): `punch_urgent` | `bgm_energy: "rise"` | `sfx_cue: "low_thud"`.
   - Cảnh 2–3 (Hồi 1 Thiết lập): `normal_story` | `bgm_energy: "low"` | `sfx_cue: "none"`.
   - Cảnh 4–5 (Hồi 2 Leo thang): `normal_story` | `bgm_energy: "rise"` | `sfx_cue: "wind_swell"` (ở Cảnh 5 nếu hợp).
   - Cảnh 6 (Cao trào): `punch_urgent` hoặc `whisper_suspense` | `bgm_energy: "peak"` | `sfx_cue: "deep_sub_drop"`.
   - Cảnh 7–Kế cuối (Hạ nhiệt): `normal_story` | `bgm_energy: "drop"` | `sfx_cue: "none"`.
   - Cảnh cuối (Kết cục): `solemn_slow` | `bgm_energy: "calm"` | `sfx_cue: "none"`."""

THINKING_PROCESS = """═══ QUY TRÌNH `thinking_process` (≤ 110 từ, viết trước khi viết cảnh) ═══
(1) Trục hưng thịnh–suy tàn hoặc xung đột trung tâm của vòng cung 3 hồi là gì?
(2) Bước ngoặt nào đánh dấu đỉnh Cao trào ở Cảnh 6, và phản ứng dây chuyền nào theo sau ở Hồi 3?
(3) Hook Staccato 2 nhịp không chữ số nào khơi vết nứt ngay Cảnh 1 và Open Loop nào nối Hồi 1 sang Hồi 2?
(4) Hình ảnh biểu tượng nào khép lại dư âm lịch sử ở Cảnh cuối, cùng `voice_profile`, `music_mood`, `bgm_alignment` phù hợp?"""

MODEL_SELF_CHECK = (
    "Đủ 5 nấc Freytag (Thiết lập -> Leo thang -> Cao trào 7–12 từ ở Cảnh 6 -> Hạ nhiệt -> Kết cục biểu tượng), "
    "không liệt kê biên niên sử dàn trải."
)

PROMPT_TEMPLATE = build_model_prompt_template(
    model_id=MODEL_ID,
    model_name=MODEL_NAME,
    group_label=GROUP_LABEL,
    core_structure=CORE_STRUCTURE,
    best_for=BEST_FOR,
    beat_sheet_block=BEAT_SHEET,
    model_guidance_block=MODEL_GUIDANCE,
    thinking_process_block=THINKING_PROCESS,
    model_self_check_line=MODEL_SELF_CHECK,
)


def render_prompt(
    user_request: str,
    intent_mode: str = "NO_HUMAN_BROLL",
    prompt_feedback: str = "",
    filtered_character_context: str = "",
    source_context: str = "",
    rationale: str = "",
) -> str:
    """Kết xuất prompt hoàn chỉnh cho mô hình `freytag_3_act`."""
    return render_model_prompt_template(
        PROMPT_TEMPLATE,
        model_id=MODEL_ID,
        model_name=MODEL_NAME,
        user_request=user_request,
        intent_mode=intent_mode,
        prompt_feedback=prompt_feedback,
        filtered_character_context=filtered_character_context,
        source_context=source_context,
        rationale=rationale,
    )
