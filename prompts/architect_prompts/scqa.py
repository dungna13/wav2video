"""
Template prompt độc lập cho mô hình kịch bản `scqa` — SCQA (McKinsey).
"""

from __future__ import annotations

from ._shared import build_model_prompt_template, render_model_prompt_template

MODEL_ID = "scqa"
MODEL_NAME = "SCQA (McKinsey)"
GROUP_LABEL = "Phim Tài liệu / Edutainment / Kể chuyện"
CORE_STRUCTURE = "Tình huống (S) -> Biến cố (C) -> Câu hỏi (Q) -> Lời giải (A)"
BEST_FOR = "Phân tích kinh doanh, chiến lược B2B, tài chính doanh nghiệp, chính sách"

BEAT_SHEET = """- **Cảnh 1 (HOOK — Complication, 6–11 từ):** Đưa thẳng biến cố thị trường hoặc cú sốc vận hành làm mô hình cũ lung lay ngay lập tức.
- **Cảnh 2 (Situation — Tình huống nền):** Trạng thái ổn định, lợi thế cốt lõi hoặc cách vận hành từng kiếm tiền tốt trước biến cố.
- **Cảnh 3 (Complication — Áp lực đè nặng & Open Loop):** Chỉ ra lực ép chi phí, đối thủ hoặc chính sách đang bào mòn nền tảng cũ, mở câu hỏi lửng.
- **Cảnh 4 (Question — Câu hỏi chiến lược):** Đặt thẳng bài toán sinh tồn buộc ban điều hành phải chọn một trong hai ngả rẽ.
- **Cảnh 5 (Bế tắc phổ thông & Open Loop):** Cho thấy vì sao cách phản ứng thông thường của đa số đối thủ chỉ làm lỗ hổng lớn hơn.
- **Cảnh 6 (TWIST — Điểm mù chiến lược 7–12 từ):** Lật ra góc nhìn cốt lõi hoặc đòn bẩy cấu trúc mà cả thị trường đã bỏ sót.
- **Cảnh 7 (Answer 1 — Động tác tái cấu trúc):** Hành động thực thi cụ thể tại nhà máy, chuỗi cung ứng hoặc bảng giá để hiện thực hóa lời giải.
- **Cảnh 8 (Answer 2 — Bằng chứng kết quả, tùy chọn đến Cảnh 9):** Kết quả vận hành thực tế chứng minh lời giải SCQA xoay chiều cuộc chơi.
- **Cảnh cuối (Hàm ý điều hành — 10–14 từ):** Nguyên tắc ra quyết định cô đọng như câu chốt một bản executive memo, callback về Cảnh 1."""

MODEL_GUIDANCE = """1. **Kỹ thuật Hook Staccato 2 nhịp (không chữ số):**
   - Nhịp một gọi tên kẻ thống trị hoặc mô hình tưởng như bất bại; nhịp hai phơi bày điểm gãy tài chính/thị trường ngay lập tức.
   - Ví dụ mẫu: *"Kho hàng đầy ắp đơn. Dòng tiền vẫn cạn từng giờ."* / *"Thị phần dẫn đầu cả nước. Biên lãi lại mỏng như dao."*
2. **Chiến lược Twist & Auditory Open Loop:**
   - Cuối Cảnh 3 chốt bằng áp lực chuyển sang Câu hỏi (Q) (*"Cắt giá để giữ khách -- hay giữ giá để tự loại mình?"*).
   - Cảnh 6 là **Điểm mù chiến lược** (7–12 từ), gãy gọn và kết thúc bằng từ thanh **Trắc** (*lệch, ngược, rỗng, đắt, khóa*) để mở đường cho chữ **Answer**.
3. **Kỹ thuật chốt `outro_style`:**
   - Chốt hàm ý chiến lược gọn, sắc và thực dụng như kết luận một bản ghi nhớ điều hành (*executive memo*), đặt `--` ngay trước 3–4 từ đắt giá cuối; không sáo ngữ đạo lý.
4. **Bẫy cần tránh của `scqa`:**
   - Dùng thuật ngữ quản trị tiếng Anh chưa Việt hóa (TTS đọc sai) hoặc chữ số/tỷ lệ `%` trong `narration_vn` (chỉ đưa số/ký hiệu vào `subtitle_vn` và `overlay_keyword_vn`).
   - Vẽ biểu đồ, slide, bảng tính trong `image_prompt_en` (vi phạm RULE #2) — thay bằng cảng container, dây chuyền sản xuất, kệ kho, phòng họp kính, máy chủ, hóa đơn giấy.
   - Phần Answer chung chung ("tối ưu hóa", "chuyển đổi số") thay vì cơ chế hành động đo được.
5. **Gợi ý nhịp CAM-WN (`vocal_delivery` / `bgm_energy` / `sfx_cue`):**
   - Cảnh 1 (Complication Hook): `punch_urgent` | `bgm_energy: "rise"` | `sfx_cue: "low_thud"`.
   - Cảnh 2–3 (Situation & Complication): `normal_story` | `bgm_energy: "low"` → `"rise"` | `sfx_cue: "none"`.
   - Cảnh 4–5 (Question & Bế tắc): `normal_story` | `bgm_energy: "rise"` | `sfx_cue: "none"`.
   - Cảnh 6 (Điểm mù chiến lược): `whisper_suspense` hoặc `punch_urgent` | `bgm_energy: "drop"` | `sfx_cue: "deep_sub_drop"`.
   - Cảnh 7–Kế cuối (Answer): `normal_story` | `bgm_energy: "peak"` | `sfx_cue: "camera_click"` (ở Cảnh 7 nếu cần).
   - Cảnh cuối (Hàm ý điều hành): `solemn_slow` | `bgm_energy: "calm"` | `sfx_cue: "none"`."""

THINKING_PROCESS = """═══ QUY TRÌNH `thinking_process` (≤ 110 từ, viết trước khi viết cảnh) ═══
(1) Biến cố thực tế nào (Complication) đang làm lung lay tình huống ổn định (Situation) của chủ đề?
(2) Câu hỏi chiến lược sống còn (Question) và điểm mù mà đa số đối thủ bỏ sót ở Cảnh 6 là gì?
(3) Hook Staccato 2 nhịp không chữ số nào đánh thẳng vào nghịch lý kinh doanh cùng Open Loop nối Q sang A?
(4) Bối cảnh vật chất nào thay thế cho biểu đồ/slide khô khan, cùng `voice_profile`, `music_mood`, `bgm_alignment`?"""

MODEL_SELF_CHECK = (
    "Đủ mạch S–C–Q–A với Complication mở Cảnh 1, Question rõ ở Cảnh 4, Điểm mù 7–12 từ ở Cảnh 6, "
    "Answer cụ thể không dùng ảnh chart/slide và kết kiểu executive memo."
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
    """Kết xuất prompt hoàn chỉnh cho mô hình `scqa`."""
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
