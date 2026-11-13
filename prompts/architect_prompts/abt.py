"""
Template prompt độc lập cho mô hình kịch bản `abt` — ABT (And–But–Therefore).
"""

from __future__ import annotations

from ._shared import build_model_prompt_template, render_model_prompt_template

MODEL_ID = "abt"
MODEL_NAME = "ABT (And–But–Therefore)"
GROUP_LABEL = "Phim Tài liệu / Edutainment / Kể chuyện"
CORE_STRUCTURE = "Bối cảnh (And) -> Mâu thuẫn (But) -> Hệ quả (Therefore)"
BEST_FOR = "Lịch sử, khoa học, kinh tế, giải thích cơ chế nhân quả"

BEAT_SHEET = """- **Cảnh 1 (HOOK — 6–11 từ):** Nêu một hệ quả trớ trêu hoặc sự thật nhân quả bẻ ngược trực giác để dừng ngón tay lướt.
- **Cảnh 2 (AND 1 — Thiết lập nền):** Đặt sự thật quen thuộc ai cũng công nhận về chủ đề bằng một vật thể hoặc bối cảnh cụ thể.
- **Cảnh 3 (AND 2 — Mở rộng & Open Loop):** Bổ sung mảnh ghép thứ hai củng cố niềm tin ban đầu, kết bằng câu lửng mở khoảng trống tò mò.
- **Cảnh 4 (AND 3 — Đẩy giả định lên đỉnh):** Chốt chặt quy luật thông thường ngay trước khi đánh sập nó.
- **Cảnh 5 (BUT — Bước ngoặt ngắn gắt 7–12 từ):** Đập thẳng mâu thuẫn cốt lõi phá vỡ hoàn toàn giả định ở phần AND.
- **Cảnh 6 (Cơ chế 1 — Giải mã ẩn số):** Chỉ ra bánh răng vận hành thật sự hoặc nguyên nhân gốc phía sau chữ *But*.
- **Cảnh 7 (Cơ chế 2 — Bằng chứng thực địa):** Đưa dữ kiện, sự cố hoặc hệ lụy cụ thể chứng minh cơ chế vừa nêu.
- **Cảnh 8 (Mở rộng tác động — Tùy chọn đến Cảnh 9):** Cho thấy cơ chế này lặp lại hoặc chi phối bức tranh rộng hơn ra sao.
- **Cảnh cuối (THEREFORE — Kết Callback 10–14 từ):** Chốt hệ quả tất yếu nối thẳng về hình ảnh/ý ở Cảnh 1 ở tầng nghĩa sắc bén hơn."""

MODEL_GUIDANCE = """1. **Kỹ thuật Hook Staccato 2 nhịp (không chữ số):**
   - Nhịp một gọi đúng hệ quả lạ lùng hoặc nghịch lý; nhịp hai cắt ngang bằng chữ *nhưng* hoặc vế đối nghịch khiến người xem phải hỏi "vì sao?".
   - Ví dụ mẫu: *"Kho bạc chất đầy vàng. Đế chế vẫn sụp vì đói."* / *"Càng in nhiều tiền. Đồng bạc càng nhẹ như giấy vụn."*
2. **Chiến lược Twist & Auditory Open Loop:**
   - Cuối Cảnh 3 đặt cầu nối níu tai kiểu điều kiện chưa giải mã (vd: *"Mọi sổ sách đều đẹp -- cho tới sáng hôm sau."*).
   - Cảnh 5 là nhát cắt **BUT** ngắn gắt (7–12 từ), kết thúc bằng từ mang thanh **Trắc** (*vỡ, tắt, rỗng, sập, ngược*) để đập tan giả định phần AND.
3. **Kỹ thuật chốt `outro_style`:**
   - Chốt hệ quả tất yếu (*Therefore*) nối thẳng về hình ảnh hoặc nghịch lý mở đầu, đặt `--` trước 3–4 từ cuối để tạo độ ngân; tuyệt đối không rao giảng bài học.
4. **Bẫy cần tránh của `abt`:**
   - Kéo phần AND quá dài thành bài giảng sách giáo khoa khiến người xem bỏ đi trước khi gặp chữ *But*.
   - Đặt nhiều chữ *nhưng* vụn vặt ở mọi cảnh làm mất lực cú đấm mâu thuẫn chính ở Cảnh 5.
   - Giải thích cơ chế bằng khái niệm trừu tượng thay vì vật thể/hành động đời thật.
5. **Gợi ý nhịp CAM-WN (`vocal_delivery` / `bgm_energy` / `sfx_cue`):**
   - Cảnh 1 (Hook): `punch_urgent` | `bgm_energy: "rise"` | `sfx_cue: "low_thud"`.
   - Cảnh 2–4 (AND): `normal_story` | `bgm_energy: "low"` → `"rise"` | `sfx_cue: "none"`.
   - Cảnh 5 (BUT Twist): `whisper_suspense` hoặc `punch_urgent` | `bgm_energy: "drop"` | `sfx_cue: "deep_sub_drop"`.
   - Cảnh 6–Kế cuối (Cơ chế): `normal_story` | `bgm_energy: "rise"` → `"peak"` | `sfx_cue: "none"`.
   - Cảnh cuối (THEREFORE): `solemn_slow` | `bgm_energy: "calm"` | `sfx_cue: "clock_tick_stop"` hoặc `"none"`."""

THINKING_PROCESS = """═══ QUY TRÌNH `thinking_process` (≤ 110 từ, viết trước khi viết cảnh) ═══
(1) Giả định quen thuộc nào (AND) mà khán giả tin sái cổ về chủ đề này?
(2) Nghịch lý hay cơ chế ẩn nào (BUT) đập gãy giả định đó trong đúng một câu ngắn gắt?
(3) Hook Staccato 2 nhịp không chữ số nào khơi hệ quả ngược đời ở Cảnh 1 và Open Loop nào nối qua Cảnh 3?
(4) Ba hình ảnh đời thật đắt giá nhất cho AND–BUT–THEREFORE cùng lựa chọn `voice_profile`, `music_mood`, `bgm_alignment` là gì?"""

MODEL_SELF_CHECK = (
    "Mạch AND (Cảnh 2–4) → BUT ngắn gắt 7–12 từ (Cảnh 5) → Cơ chế (Cảnh 6–Kế cuối) → THEREFORE callback về Hook (Cảnh cuối) "
    "rõ ràng, không bị lan man phần nền hoặc mất lực mâu thuẫn."
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
    """Kết xuất prompt hoàn chỉnh cho mô hình `abt`."""
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
