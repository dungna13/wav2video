"""
Prompt chuyên biệt cho mô hình `rule_of_three` (Rule of Three / Listicle).

Nhóm: Short-Form Viral (TikTok / Reels / Shorts).
"""

from __future__ import annotations

from ._shared import build_model_prompt_template, render_model_prompt_template

MODEL_ID = "rule_of_three"
MODEL_NAME = "Rule of Three / Listicle"
GROUP_LABEL = "Short-Form Viral (TikTok / Reels / Shorts)"
CORE_STRUCTURE = "Hook tổng -> Điểm 1 (quen) -> Điểm 2 (sâu hơn) -> Điểm 3 (đắt giá nhất) -> Chốt"
BEST_FOR = "3 lý do, 3 sai lầm, 3 dấu hiệu, mẹo/nguyên tắc, tổng hợp kiến thức nhanh"

BEAT_SHEET = """- **Cảnh 1 (HOOK — Gọi tên bộ ba, 6–11 từ):** Đặt khung ba yếu tố quyết định bằng tuyên bố Staccato dứt khoát, đánh vào hậu quả hoặc lợi ích sát sườn.
- **Cảnh 2 (ĐIỂM 1 — Giới thiệu tầng bề mặt, 13–18 từ):** Gọi tên yếu tố đầu tiên dễ gặp nhất bằng hình ảnh đời thật cụ thể (`overlay_keyword_vn` có thể neo số `"1."`).
- **Cảnh 3 (ĐIỂM 1 — Hệ quả & cầu nối, 13–18 từ):** Giải thích vì sao Điểm 1 mới chỉ là phần nổi; cuối câu đặt **Auditory Open Loop** đẩy sang yếu tố nguy hiểm/sâu hơn.
- **Cảnh 4 (ĐIỂM 2 — Cơ chế âm thầm, 13–19 từ):** Mở yếu tố thứ hai ít người để ý hơn nhưng đang âm thầm khuếch đại vấn đề (`overlay_keyword_vn` neo `"2."`).
- **Cảnh 5 (ĐIỂM 2 — Đòn bẩy sang cao trào, 12–18 từ):** Chỉ ra cái giá của Điểm 2 và gài câu mở lửng rằng cả hai yếu tố đầu vẫn chưa phải thứ chí mạng nhất.
- **Cảnh 6 (TWIST — Bản lề trước Điểm 3, 7–12 từ):** Câu ngắn gắt (kết thanh Trắc) cắt nhịp liệt kê, báo hiệu nhân tố quyết định nằm ở điểm cuối.
- **Cảnh 7 (ĐIỂM 3 — Yếu tố đắt giá nhất, 13–19 từ):** Trình bày lý do/sai lầm/nguyên tắc thứ ba — thứ lật ngược cách nhìn phổ thông (`overlay_keyword_vn` neo `"3."`).
- **Cảnh 8–9 (ĐIỂM 3 — Minh họa thực chứng, 12–17 từ, tùy chọn nếu 9–10 cảnh):** Đưa ví dụ hoặc hành động kiểm chứng cụ thể để Điểm 3 bám rễ vào trí nhớ.
- **Cảnh cuối (TỔNG KẾT — Nguyên tắc vàng, 10–14 từ):** Gộp cả ba điểm thành một nguyên tắc sắc gọn dễ nhớ, đặt `--` trước 3–4 từ đúc kết để tạo Sonic Echo."""

MODEL_GUIDANCE = """1. **Kỹ thuật Hook "Staccato 2 nhịp" (6–11 từ, đọc < 3s, KHÔNG chữ số):**
   - Nhịp 1 (2–4 từ): Đánh thẳng vào nỗi đau, sai lầm hoặc tình huống thực tế (không viết chữ số trong `narration_vn`, dùng chữ *"ba"*).
   - Nhịp 2 (4–7 từ): Gọi khung bộ ba và cái giá nếu bỏ qua điểm cuối.
   - *Ví dụ tiếng Việt chuẩn (không số):* *"Tiền tự động bốc hơi. Đây là ba cái bẫy ngầm."* / *"Thức khuya chẳng làm bạn giỏi. Chỉ ba thói quen này quyết định."*
2. **Chiến lược Twist & Open Loop (Chống hội chứng "xem hết Điểm 1 rồi lướt"):**
   - **Quy tắc leo thang 1 < 2 << 3:** Điểm 1 là thứ khán giả đoán được (tạo đồng thuận); Điểm 2 là cơ chế ẩn; Điểm 3 là cú lật đắt giá nhất.
   - Cuối Cảnh 3 và Cảnh 5 cài **Auditory Open Loop** nhắc ngầm thứ thực sự nguy hiểm đang chờ ở sau; Cảnh 6 (Twist **7–12 từ**, kết thanh Trắc) chặn mạch "đếm danh sách đều đều" và buộc người xem ở lại nghe Điểm 3.
   - Neo `overlay_keyword_vn` ngắn gọn ở 3–4 cảnh (Hook + Điểm 1/2/3 hoặc Điểm 3 + Kết) để giữ tính listicle rõ ràng trên màn hình dọc.
3. **Kỹ thuật chốt (`outro_style`):**
   - Gói trọn ba điểm vừa liệt kê vào **một nguyên tắc nhớ ngay** sau khi xem xong (không lặp lại máy móc cả 3 đầu mục).
   - Hãm nhịp `--` trước 3–4 từ cuối để chuyển từ tốc độ listicle sang dư âm đúc kết.
4. **Bẫy cần tránh:**
   - Liệt kê 3 điểm ngang hàng, thậm chí Điểm 1 hay hơn Điểm 3 (khiến cuối clip bị tụt lực).
   - Dùng chữ số `"3"`, `"1."`, `"2."` trong `narration_vn` (vi phạm Rule #5 TTS; số thứ tự ngắn chỉ đưa vào `subtitle_vn` hoặc `overlay_keyword_vn`).
   - Biến mỗi điểm thành gạch đầu dòng khô khan như slide PowerPoint (vi phạm Rule #1 và #2).
5. **Gợi ý phối hợp nhịp CAM-WN (`vocal_delivery` / `bgm_energy` / `sfx_cue`):**
   - **Cảnh 1 (Hook):** `punch_urgent` + `bgm_energy="rise"` + `sfx_cue="low_thud"`.
   - **Cảnh 2–5 (Điểm 1 & Điểm 2):** `normal_story` (nhịp chắc, gọn) + `bgm_energy="rise"`, `sfx_cue="subtle_whoosh"` tại điểm chuyển sang Điểm 2 (nếu cần, giữ tổng SFX ≤ 3).
   - **Cảnh 6 (Twist dẫn Điểm 3):** `whisper_suspense` hoặc `punch_urgent` + `bgm_energy="drop"` + `sfx_cue="deep_sub_drop"`.
   - **Cảnh 7–Kế cuối (Điểm 3 đắt giá):** `punch_urgent` → `normal_story` + `bgm_energy="peak"`, `sfx_cue="none"`.
   - **Cảnh cuối (Tổng kết):** `solemn_slow` + `bgm_energy="calm"` + `sfx_cue="none"`."""

THINKING_PROCESS = """═══ QUY TRÌNH `thinking_process` (≤ 110 từ, viết trước khi viết cảnh) ═══
(1) Bộ ba nào giải quyết trúng nút thắt của chủ đề, và viết chữ "ba" không dùng chữ số trong Hook ra sao? (2) Sắp xếp Điểm một (quen thuộc) -> Điểm hai (cơ chế ngầm) -> Điểm ba (đắt giá nhất) thế nào để tăng dần độ nặng? (3) Cú Twist bảy đến mười hai từ ở cảnh sáu phá nhịp liệt kê đều đều trước Điểm ba ra sao? (4) Câu kết mười đến mười bốn từ gom cả ba điểm thành nguyên tắc nào, phối rise, drop và peak ra sao?"""

MODEL_SELF_CHECK = "Đúng cấu trúc `rule_of_three`: đủ 3 điểm theo thang tăng dần 1 (quen) < 2 (cơ chế) << 3 (đắt nhất), Cảnh 6 Twist trước Điểm 3, không dùng chữ số trong `narration_vn`, Cảnh cuối gói thành 1 nguyên tắc."

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
    """Kết xuất prompt đầy đủ cho mô hình `rule_of_three`."""
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
