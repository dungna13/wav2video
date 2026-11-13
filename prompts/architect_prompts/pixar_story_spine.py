"""
Template prompt độc lập cho mô hình kịch bản `pixar_story_spine` — Pixar Story Spine.
"""

from __future__ import annotations

from ._shared import build_model_prompt_template, render_model_prompt_template

MODEL_ID = "pixar_story_spine"
MODEL_NAME = "Pixar Story Spine"
GROUP_LABEL = "Phim Tài liệu / Edutainment / Kể chuyện"
CORE_STRUCTURE = "Ngày xửa... Mỗi ngày... Cho đến một ngày... Vì thế... Cuối cùng..."
BEST_FOR = "Storytelling nhân văn, tiểu sử, chân dung nhà sáng lập/phát minh"

BEAT_SHEET = """- **Cảnh 1 (HOOK — Cho đến một ngày, 6–11 từ):** Cắt thẳng vào khoảnh khắc bước ngoặt làm đảo lộn hoàn toàn số phận nhân vật.
- **Cảnh 2 (Ngày xửa... — Xuất phát điểm):** Khắc họa thân phận đời thường, giới hạn hoặc thiếu thốn ban đầu bằng vật dụng cụ thể.
- **Cảnh 3 (Mỗi ngày... — Thói quen lặp lại & Open Loop):** Nhịp sống bền bỉ ngày qua ngày trước biến cố, lửng một chi tiết báo hiệu đổi thay.
- **Cảnh 4 (Vì thế 1 — Bước ra khỏi vùng an toàn):** Hành động đầu tiên của nhân vật ngay sau biến cố ở Cảnh 1.
- **Cảnh 5 (Vì thế 2 — Chuỗi va đập & Open Loop):** Khó khăn hoặc sự từ chối liên tiếp khiến hành trình tưởng như đi vào ngõ cụt.
- **Cảnh 6 (TWIST — Thử thách sinh tử 7–12 từ):** Thời khắc tăm tối nhất khi nhân vật đối mặt nguy cơ mất tất cả hoặc bỏ cuộc.
- **Cảnh 7 (Cho đến khi... — Phát kiến / Lựa chọn):** Một chi tiết quan sát, quyết định táo bạo hoặc thay đổi cách làm xoay chuyển cục diện.
- **Cảnh 8 (Kết quả hữu hình — Tùy chọn đến Cảnh 9):** Thành quả thực tế đầu tiên chứng minh lựa chọn ở Cảnh 7 đã phát huy tác dụng.
- **Cảnh cuối (Và kể từ đó — 10–14 từ):** Di sản nhân văn cụ thể để lại cho đời thực, nối về xuất phát điểm Cảnh 1–2."""

MODEL_GUIDANCE = """1. **Kỹ thuật Hook Staccato 2 nhịp (không chữ số):**
   - Dùng chính biến cố *"Cho đến một ngày"* làm Hook: nhịp một nêu sự việc đột ngột hoặc vật thể nhỏ; nhịp hai nêu sự xoay chuyển số phận.
   - Ví dụ mẫu: *"Một bức thư từ chối. Đủ mở ra cả ngành mới."* / *"Chiếc máy hỏng giữa đêm. Lại sinh ra phát minh triệu người dùng."*
2. **Chiến lược Twist & Auditory Open Loop:**
   - Cuối Cảnh 3 mở lửng chuyển pha (*"Mỗi sáng đều giống hệt nhau -- cho tới khi cánh cửa xưởng khóa chặt."*).
   - Cảnh 6 là "đáy vực" ngắn gắt (7–12 từ), kết thúc bằng từ mang thanh **Trắc** (*cạn, tắt, trắng, gục, khép*) để tạo lực bật cho Cảnh 7 (*"Cho đến khi..."*).
3. **Kỹ thuật chốt `outro_style`:**
   - Chốt bằng di sản nhân văn cụ thể (*"và kể từ đó..."*) gắn với một vật thể/thói quen thực tế thay đổi mãi mãi, đặt `--` trước 3–4 từ cuối; tránh khẩu hiệu truyền cảm hứng sáo rỗng.
4. **Bẫy cần tránh của `pixar_story_spine`:**
   - Dùng sáo ngữ như *"hành trình vượt nghịch cảnh"*, *"hạt mầm ước mơ"*, *"ánh sáng cuối đường hầm"*.
   - Viết `image_prompt_en` thành tranh minh họa hoạt hình hay cận mặt nhân vật nhìn thẳng camera (vi phạm RULE #2 và `intent_mode`).
   - Nhồi quá nhiều giai đoạn cuộc đời khiến mạch nhân quả *"vì thế... vì thế..."* bị đứt gãy.
5. **Gợi ý nhịp CAM-WN (`vocal_delivery` / `bgm_energy` / `sfx_cue`):**
   - Cảnh 1 (Cho đến một ngày): `punch_urgent` | `bgm_energy: "rise"` | `sfx_cue: "camera_click"` hoặc `"low_thud"`.
   - Cảnh 2–3 (Ngày xửa / Mỗi ngày): `normal_story` | `bgm_energy: "low"` | `sfx_cue: "none"`.
   - Cảnh 4–5 (Vì thế): `normal_story` | `bgm_energy: "rise"` | `sfx_cue: "none"`.
   - Cảnh 6 (Đáy vực Twist): `whisper_suspense` | `bgm_energy: "drop"` | `sfx_cue: "heartbeat_pulse"`.
   - Cảnh 7–Kế cuối (Cho đến khi): `normal_story` hoặc `punch_urgent` | `bgm_energy: "peak"` | `sfx_cue: "subtle_whoosh"` (ở Cảnh 7 nếu cần).
   - Cảnh cuối (Và kể từ đó): `solemn_slow` | `bgm_energy: "calm"` | `sfx_cue: "none"`."""

THINKING_PROCESS = """═══ QUY TRÌNH `thinking_process` (≤ 110 từ, viết trước khi viết cảnh) ═══
(1) Khoảnh khắc "Cho đến một ngày" nào làm đổi hướng cuộc đời/phát minh của nhân vật để mở Cảnh 1?
(2) Chuỗi nhân quả "Vì thế..." dẫn tới đáy vực nào ở Cảnh 6 và lựa chọn nào xoay chuyển ở Cảnh 7?
(3) Hook Staccato 2 nhịp không chữ số nào chạm cảm xúc thật mà không sáo rỗng, cùng Open Loop ở Cảnh 3?
(4) Vật thể đời thật nào gắn với di sản "và kể từ đó", cùng `voice_profile`, `music_mood`, `bgm_alignment`?"""

MODEL_SELF_CHECK = (
    "Thể hiện rõ xương sống Pixar (Cho đến một ngày -> Mỗi ngày -> Vì thế -> Đáy vực 7–12 từ -> Cho đến khi -> Và kể từ đó) "
    "bằng vật chứng đời thật, sạch sáo ngữ."
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
    """Kết xuất prompt hoàn chỉnh cho mô hình `pixar_story_spine`."""
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
