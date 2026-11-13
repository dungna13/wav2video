"""
Prompt chuyên biệt cho mô hình `open_loops` (Open Loops — Vòng lặp mở).

Nhóm: Short-Form Viral (TikTok / Reels / Shorts).
"""

from __future__ import annotations

from ._shared import build_model_prompt_template, render_model_prompt_template

MODEL_ID = "open_loops"
MODEL_NAME = "Open Loops (Vòng lặp mở)"
GROUP_LABEL = "Short-Form Viral (TikTok / Reels / Shorts)"
CORE_STRUCTURE = "Mở câu hỏi A -> Mở tiếp vòng B -> Giải mã B -> Quay về đóng trọn A"
BEST_FOR = "Bí ẩn chưa lời giải, tâm lý học nhận thức, hiệu ứng lạ, thí nghiệm hành vi"

BEAT_SHEET = """- **Cảnh 1 (HOOK — Mở Loop A, 6–11 từ):** Đặt ngay một nghịch lý hoặc dấu hỏi lớn chưa giải thích (tuyệt đối không lộ đáp án) để kích hoạt hiệu ứng Zeigarnik.
- **Cảnh 2 (Dẫn chứng A, 13–18 từ):** Mô tả hiện trường, thí nghiệm hoặc hành vi kỳ lạ gắn trực tiếp với Loop A.
- **Cảnh 3 (Mở Loop B — Lồng vòng lặp phụ, 13–19 từ):** Đưa manh mối đầu tiên tưởng là lời giải, nhưng manh mối này lại đẻ ra câu hỏi thứ hai (Loop B) oái oăm hơn.
- **Cảnh 4 (Lần theo Loop B — Lớp 1, 13–19 từ):** Bóc tách dữ kiện sâu hơn về Loop B bằng hình ảnh vật thể/hành động cụ thể.
- **Cảnh 5 (Lần theo Loop B — Áp sát nút thắt, 12–18 từ):** Đẩy bí ẩn phụ đến giới hạn; đặt **Auditory Open Loop** buộc người xem chờ chìa khóa nối hai vòng lặp.
- **Cảnh 6 (TWIST — Chìa khóa nối B sang A, 7–12 từ):** Câu ngắn gắt (kết thanh Trắc) đưa phát hiện bất ngờ nối thẳng Loop B về Loop A.
- **Cảnh 7 (Đóng Loop B — Giải mã cơ chế, 13–18 từ):** Giải tỏa trọn vẹn nút thắt phụ bằng quy luật tâm lý, sinh học hoặc vật chứng thực tế.
- **Cảnh 8–9 (Mở rộng bằng chứng đóng B, 12–17 từ, tùy chọn nếu 9–10 cảnh):** Chiếu rọi ngược cơ chế vừa giải mã lên hiện trường của Cảnh 2 để mọi mảnh ghép khớp khít.
- **Cảnh cuối (Đóng Loop A — 10–14 từ):** Trả lời trọn vẹn, súc tích câu hỏi ở Cảnh 1 (đặt `--` trước 3–4 từ kết) khiến não bộ được giải tỏa hoàn toàn."""

MODEL_GUIDANCE = """1. **Kỹ thuật Hook "Staccato 2 nhịp" (6–11 từ, đọc < 3s, KHÔNG chữ số):**
   - Nhịp 1 (2–4 từ): Nêu tình huống hoặc hiện tượng bình thường bị bẻ cong.
   - Nhịp 2 (4–7 từ): Gieo dấu hỏi mở Loop A không thể bỏ qua.
   - *Ví dụ tiếng Việt chuẩn (không số):* *"Căn phòng hoàn toàn trống rỗng. Nhưng ai cũng nghe tiếng bước chân."* / *"Người bệnh quên sạch quá khứ. Vậy sao tay vẫn đàn trôi chảy?"*
2. **Chiến lược Twist & Open Loop (Quản trị cấu trúc lồng ghép A → B → B' → A'):**
   - **Kỷ luật thép:** Chỉ được đóng Loop B trước, tuyệt đối KHÔNG giải thích Loop A ở Cảnh 4–5. Nếu đóng A quá sớm, nửa sau video sẽ sụt người xem.
   - Cuối Cảnh 3 là điểm mở Loop B; cuối Cảnh 5 đặt **Auditory Open Loop** dẫn vào Cảnh 6 (Twist **7–12 từ**, kết thanh Trắc) — chính là bản lề nối B quay ngược lại A.
   - Phải đảm bảo cả Loop B lẫn Loop A đều được **đóng kín 100%** trước khi kết thúc clip.
3. **Kỹ thuật chốt (`outro_style`):**
   - Đóng kín vòng lặp đầu tiên (Loop A) bằng một câu trả lời trọn vẹn, chính xác, không bỏ lửng câu hỏi tu từ.
   - Dùng `--` trước 3–4 từ cuối để tiếng nói chùng xuống như tiếng "cạch" khóa chiếc hộp bí ẩn vừa giải xong.
4. **Bẫy cần tránh:**
   - Mở quá nhiều vòng lặp (Loop C, Loop D) trong 60 giây khiến khán giả rối não và quên mất câu hỏi đầu.
   - Kết thúc kiểu câu view rẻ tiền ("Xem phần hai để biết...") — vi phạm `outro_style` đóng trọn Loop A.
   - Nói trừu tượng ("não bộ xử lý thông tin") thay vì miêu tả hình ảnh đời thật của thí nghiệm/hiện trường (Rule #1).
5. **Gợi ý phối hợp nhịp CAM-WN (`vocal_delivery` / `bgm_energy` / `sfx_cue`):**
   - **Cảnh 1 (Mở Loop A):** `whisper_suspense` hoặc `punch_urgent` + `bgm_energy="rise"` + `sfx_cue="heartbeat_pulse"` (hoặc `"low_thud"`).
   - **Cảnh 2–5 (Mở & lần theo Loop B):** `whisper_suspense` / `normal_story` xen kẽ + `bgm_energy="rise"` → `"peak"`, `sfx_cue="none"` (giữ tension dồn nén).
   - **Cảnh 6 (Twist chìa khóa):** `punch_urgent` + `bgm_energy="drop"` + `sfx_cue="deep_sub_drop"` (khoảng lặng mở khóa).
   - **Cảnh 7–Kế cuối (Đóng Loop B):** `normal_story` + `bgm_energy="rise"`, `sfx_cue="none"`.
   - **Cảnh cuối (Đóng Loop A):** `solemn_slow` + `bgm_energy="calm"` + `sfx_cue="clock_tick_stop"` (hoặc `"none"`)."""

THINKING_PROCESS = """═══ QUY TRÌNH `thinking_process` (≤ 110 từ, viết trước khi viết cảnh) ═══
(1) Loop A nào đủ lạ để đặt ngay ở Hook sáu đến mười một từ mà không lộ đáp án? (2) Manh mối ở cảnh hai mở ra Loop B gì ở cảnh ba để giữ lực kéo Zeigarnik? (3) Cú Twist ngắn ở cảnh sáu nối chìa khóa từ Loop B ngược về Loop A qua chi tiết vật lý nào? (4) Cảnh bảy đóng Loop B và cảnh cuối đóng trọn Loop A ra sao, phối whisper_suspense với drop và calm thế nào?"""

MODEL_SELF_CHECK = "Đúng cấu trúc `open_loops`: Hook mở Loop A không lộ đáp án, Cảnh 3 mở Loop B, Cảnh 6 nối B sang A, đóng trọn B trước rồi đóng kín Loop A ở Cảnh cuối (không bỏ lửng)."

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
    """Kết xuất prompt đầy đủ cho mô hình `open_loops`."""
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
