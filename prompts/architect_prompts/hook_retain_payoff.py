"""
Prompt chuyên biệt cho mô hình `hook_retain_payoff` (Hook – Retain – Payoff).

Nhóm: Short-Form Viral (TikTok / Reels / Shorts).
"""

from __future__ import annotations

from ._shared import build_model_prompt_template, render_model_prompt_template

MODEL_ID = "hook_retain_payoff"
MODEL_NAME = "Hook – Retain – Payoff"
GROUP_LABEL = "Short-Form Viral (TikTok / Reels / Shorts)"
CORE_STRUCTURE = "3s đầu sốc -> Giữ nhịp leo thang liên tục -> Cú chốt bất ngờ"
BEST_FOR = "Video ngắn 30–60s đa chủ đề, khám phá nhanh, công nghệ, điều gì xảy ra nếu"

BEAT_SHEET = """- **Cảnh 1 (HOOK — 3 giây dừng lướt, 6–11 từ):** Cú đánh nhận thức trực diện ("Staccato 2 nhịp") đẩy thẳng vào nghịch lý hoặc kịch bản cực đoan khiến người xem khựng ngón tay.
- **Cảnh 2 (RETAIN 1 — Neo thực tế, 13–18 từ):** Đặt vật thể, bối cảnh hoặc hiện tượng đời thật ngay trước mắt để xác thực điều vừa nói ở Hook.
- **Cảnh 3 (RETAIN 2 — Leo thang cấp độ một, 13–19 từ):** Mở lớp dữ kiện hoặc hệ quả đầu tiên vượt kỳ vọng; cuối câu đặt **Auditory Open Loop** gài sang cảnh sau.
- **Cảnh 4 (RETAIN 3 — Leo thang cấp độ hai, 13–19 từ):** Tăng quy mô, tốc độ hoặc phạm vi tác động (từ cá nhân sang toàn hệ thống, từ nhỏ sang lớn).
- **Cảnh 5 (RETAIN 4 — Áp lực cận đỉnh, 12–18 từ):** Đưa chi tiết sát sườn nhất đẩy sự tò mò lên ngưỡng căng; cài nhịp lửng kéo sang cú bẻ lái.
- **Cảnh 6 (TWIST — Bẻ lái ngắn gắt, 7–12 từ):** Đảo chiều suy đoán quen thuộc bằng một câu dứt khoát (ưu tiên kết thanh Trắc) khiến khán giả phải tính lại từ đầu.
- **Cảnh 7 (BUILD PAYOFF 1 — Mảnh ghép then chốt, 13–18 từ):** Phơi bày cơ chế thật sự đứng sau chuỗi leo thang ở Cảnh 2–5.
- **Cảnh 8–9 (BUILD PAYOFF 2 — Bằng chứng cận cảnh, 12–17 từ, tùy chọn nếu 9–10 cảnh):** Đưa hình ảnh kiểm chứng cuối cùng đẩy kỳ vọng chạm đỉnh ngay trước khi chốt.
- **Cảnh cuối (PAYOFF — Cú chốt vỡ òa, 10–14 từ):** Trả đáp án bất ngờ nhưng hợp lý tuyệt đối với toàn bộ dữ kiện đã gieo, đặt `--` trước 3–4 từ đắt giá để tạo Sonic Echo."""

MODEL_GUIDANCE = """1. **Kỹ thuật Hook "Staccato 2 nhịp" (6–11 từ, đọc < 3s, KHÔNG chữ số):**
   - Nhịp 1 (2–4 từ): Ảnh hoặc sự kiện đánh gắt vào thị giác/trực giác, dứt bằng dấu chấm hoặc `--`.
   - Nhịp 2 (4–7 từ): Mệnh đề lật ngược kỳ vọng hoặc đặt giả thuyết cực đoan ("Điều gì xảy ra nếu...").
   - *Ví dụ tiếng Việt chuẩn (không số):* *"Chiếc máy bay bốc cháy. Nhưng phi công lại tắt hết động cơ."* / *"Trái Đất ngừng quay. Chỉ một giây cũng đủ xé toạc đại dương."*
2. **Chiến lược Twist & Open Loop:**
   - Giữa các nhịp Retain (Cảnh 3 và Cảnh 5), cuối câu buộc phải cài **Auditory Open Loop** (vd: *"Nhưng đó mới chỉ là phần nổi..."*, *"Và lúc này đồng hồ mới bắt đầu đếm..."*) để triệt tiêu điểm rơi retention.
   - Cảnh 6 (Twist) cắt ngắn còn **7–12 từ**, kết thúc bằng từ mang thanh **Trắc** (sắc/nặng/hỏi/ngã) nhằm chặt đứt mạch đoán của người xem trước khi vào Payoff.
3. **Kỹ thuật chốt (`outro_style`):**
   - Trả Payoff bất ngờ nhưng **hợp lý tuyệt đối** với mọi mảnh ghép từ Cảnh 2–7 (không "deus ex machina" lôi chi tiết trên trời xuống ở cảnh cuối).
   - Đặt `--` trước cụm 3–4 từ kết để giọng đọc hãm nhịp tạo dư âm; nối liền ý với `closing_takeaway`.
4. **Bẫy cần tránh:**
   - Mở đầu bằng câu hỏi sáo rỗng ("Bạn có bao giờ tự hỏi..."), vào đề chậm ở Cảnh 2–3 khiến mất nhịp Viral 30–60s.
   - Retain bị ngang phè (Cảnh 2, 3, 4 chỉ liệt kê cùng một cấp độ thông tin thay vì leo thang cường độ).
   - Payoff hụt hơi hoặc chỉ nhắc lại điều đã nói ở Hook.
5. **Gợi ý phối hợp nhịp CAM-WN (`vocal_delivery` / `bgm_energy` / `sfx_cue`):**
   - **Cảnh 1 (Hook):** `punch_urgent` + `bgm_energy="rise"` + `sfx_cue="low_thud"` (hoặc `"subtle_whoosh"`).
   - **Cảnh 2–5 (Retain leo thang):** `normal_story` (tăng dần tốc độ hình với `camera` luân phiên) + `bgm_energy="rise"` → `"peak"` ở Cảnh 5, `sfx_cue="none"`.
   - **Cảnh 6 (Twist):** `whisper_suspense` (hoặc `punch_urgent`) + `bgm_energy="drop"` + `sfx_cue="deep_sub_drop"` (cắt nhạc tạo khoảng hẫng).
   - **Cảnh 7–Kế cuối (Build Payoff):** `normal_story` → `punch_urgent` + `bgm_energy="rise"` → `"peak"`, `sfx_cue="none"`.
   - **Cảnh cuối (Payoff):** `solemn_slow` + `bgm_energy="calm"` + `sfx_cue="clock_tick_stop"` (hoặc `"none"` nếu đã dùng đủ 2–3 SFX)."""

THINKING_PROCESS = """═══ QUY TRÌNH `thinking_process` (≤ 110 từ, viết trước khi viết cảnh) ═══
(1) Chi tiết sốc hoặc kịch bản "nếu... thì sao" nào đủ sức chặn ngón tay trong ba giây đầu? (2) Chuỗi dữ kiện Retain ở giữa leo thang qua bốn nấc cường độ ra sao để không cảnh nào lặp cấp độ? (3) Cú Twist bảy đến mười hai từ ở cảnh sáu bẻ lái suy đoán nào, và hai cầu nối Open Loop đặt ở đâu? (4) Payoff cảnh cuối nối khớp với mảnh ghép nào đã gieo từ đầu, phối CAM-WN dồn nhịp từ rise lên peak rồi drop/calm thế nào?"""

MODEL_SELF_CHECK = "Đúng cấu trúc `hook_retain_payoff`: Hook Staccato 3s không sáo ngữ, chuỗi Retain leo thang rõ cấp độ (có Open Loop cuối Cảnh 3 & 5), Twist 7–12 từ đảo chiều, Payoff bất ngờ nhưng khớp logic."

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
    """Kết xuất prompt đầy đủ cho mô hình `hook_retain_payoff`."""
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
