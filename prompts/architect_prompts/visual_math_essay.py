"""
Prompt chuyên biệt cho mô hình `visual_math_essay`
(Visual Math Essay / Minimalist Motion Graphics — lấy cảm hứng từ 3Blue1Brown Manim-style & anim.vn,
kết hợp kể chuyện vi lịch sử ngắn bằng ảnh tư liệu Wikimedia đen-trắng).

Nhóm: Phim Tài liệu / Edutainment / Kể chuyện.
"""

from __future__ import annotations

from ._shared import build_model_prompt_template, render_model_prompt_template

MODEL_ID = "visual_math_essay"
MODEL_NAME = "Visual Math Essay (3B1B Manim + Micro-History)"
GROUP_LABEL = "Phim Tài liệu / Edutainment / Kể chuyện"
CORE_STRUCTURE = (
    "Câu đố đời thường (Hook) -> Thu gọn khung khái niệm -> Lịch sử phát minh (B&W Archival) "
    "-> Ẩn dụ hình học trực quan (Manim Dark-Mode + Gold) -> Bản đồ ứng dụng / Mẹo -> Thử thách kết"
)
BEST_FOR = (
    "Toán cao cấp (giải tích, đạo hàm, tích phân, ma trận), thuật toán, AI/ML, vật lý, xác suất, "
    "giải thích khái niệm trừu tượng bằng trực giác hình học & lịch sử ngắn"
)
STYLE_TAG = (
    '[STYLE]: 3Blue1Brown (Manim-style) / anim.vn — Visual Math Essay nền đen lưới tọa độ mờ, '
    'đồ họa hình học tối giản nét mảnh phát sáng vàng hổ phách (gold) xen kẽ ảnh tư liệu lịch sử đen-trắng, '
    'tuyệt đối không "trẻ con / slide PowerPoint / rườm rà"'
)

BEAT_SHEET = """- **Cảnh 1 (HOOK — Câu đố đời thường, 6–11 từ):** Mở ngay bằng bài toán thực tế sát sườn (bán hàng, tối ưu chi phí, tốc độ, AI) hoặc nghịch lý trực giác; KHÔNG định nghĩa sách giáo khoa.
- **Cảnh 2 (THU GỌN KHUNG — Giảm áp lực nhận thức, 13–18 từ):** Gom toàn bộ chủ đề phức tạp về 1–3 bức hình/nguyên lý trực quan đơn giản (kiểu "thật ra chỉ xoay quanh ba hình").
- **Cảnh 3 (MICRO-HISTORY — Nguồn gốc cổ đại / tranh luận, 13–20 từ):** Kể ngắn xuất phát điểm lịch sử (bảng tính cổ, tranh cãi học giả, bài báo bước ngoặt) bằng `visual_source_type: "real_photo"` nếu có bản thảo/nhân vật thật; đặt **Auditory Open Loop** cuối câu.
- **Cảnh 4 (MICRO-HISTORY — Bước ngoặt hiện đại / Nobel, 13–19 từ):** Nối lịch sử với ứng dụng kinh tế/AI bằng nhân vật thật (`real_photo` chân dung đen-trắng từ Wikimedia) trước khi bước vào trực quan hóa.
- **Cảnh 5 (TRỰC GIÁC HÌNH HỌC 1 — Vẽ hình thay công thức, 13–19 từ):** Minh họa khái niệm bằng ẩn dụ hình học tối giản (độ dốc cây thước tựa sườn đồi, lát cắt chữ nhật mỏng, lưới ma trận số) trên nền đen nhấn vàng hổ phách.
- **Cảnh 6 (TWIST — Lật bản chất cốt lõi, 7–12 từ):** Câu ngắn gắt (kết thanh Trắc) thu gọn công thức/cơ chế vào một hình ảnh vàng rực duy nhất trên đỉnh/nút chuyển.
- **Cảnh 7 (TRỰC GIÁC HÌNH HỌC 2 / CƠ CHẾ, 13–19 từ):** Mở rộng sang cơ chế thứ hai hoặc cho thấy một phép biến đổi đơn giản tác động hàng triệu phần tử cùng lúc.
- **Cảnh 8 (BẢN ĐỒ ỨNG DỤNG / MẸO THỰC CHIẾN, 13–18 từ):** Đặt ma trận chấm tròn vàng hoặc danh sách đánh số tối giản ánh xạ "ngành nào dùng gì" / "mẹo hết sợ" — mỗi mục ≤ 4 từ thị giác.
- **Cảnh cuối (BOOKEND CALLBACK & THỬ THÁCH, 10–14 từ):** Quay lại chính bài toán Hook ở Cảnh 1 dưới góc nhìn mới, hãm nhịp `--` trước 3–4 từ đúc kết (`solemn_slow`), kèm thử thách tính nhẹ ở `closing_takeaway`."""

MODEL_GUIDANCE = """1. **Quy tắc "Trực giác hình học trước — Công thức theo sau" (Visual Intuition First):**
   - Với `visual_math_essay`, **cho phép và ưu tiên** mô tả đồ họa hình học tối giản kiểu Manim (`luminous amber-gold parabolic curve`, `faint perspective coordinate grid on pure obsidian black`, `thin translucent slate-blue rectangular slices`, `minimalist glowing number matrix grid`) thay cho ảnh đời thật ở các cảnh giải thích khái niệm; vẫn **CẤM** `cartoon`, `anime`, `pixar`, `clipart`, `slide`, `presentation`, `watermark`, `logo`.
   - `style_anchor_en` (30–45 từ) phải khóa chặt bảng màu **Anim/3B1B Dark-Mode**: nền đen sâu (`deep matte black background with subtle faint perspective grid lines`), nét trắng/xám thanh mảnh, duy nhất điểm nhấn **vàng hổ phách (`luminous warm amber-gold accent`)**, khoảng trống thoáng, dồn chủ thể vào 2/3 trên và chừa 1/3 dưới tối sạch cho phụ đề pill.
2. **Kỷ luật Micro-History (`real_photo` B&W đồng bộ nền tối):**
   - Trong 1–2 cảnh kể chuyện lịch sử (Cảnh 3–4), BẮT BUỘC ưu tiên `visual_source_type: "real_photo"` kèm `real_media_query` chính xác tên nhà toán học, giải Nobel hoặc bản thảo gốc trên Wikipedia/Wikimedia Commons (vd: `"Isaac Newton Godfrey Kneller"`, `"Gottfried Wilhelm Leibniz"`, `"Wassily Leontief"`, `"Geoffrey Hinton"`, `"Nine Chapters Mathematical Art"`), và trong `image_prompt_en` fallback giữ mô tả chân dung/di vật đơn sắc tương phản cao hòa vào nền đen.
3. **Kỹ thuật Hook "Câu đố đời thường" (6–11 từ, KHÔNG chữ số trong `narration_vn`):**
   - Đẩy người xem vào tình huống thực tế quen thuộc (trà sữa, tiền lãi, điểm ảnh điện thoại, đường đua...) rồi hỏi thẳng bản chất thay vì định nghĩa.
   - *Ví dụ chuẩn TTS:* *"Bán giá nào một ly trà sữa cho lãi lớn nhất?"* / *"Một phép nhân bảng số đang điều khiển cả trí tuệ nhân tạo."*
4. **Hợp đồng Bố cục Khung hình (Visual Restraint):**
   - Mỗi cảnh chỉ minh họa **MỘT ẩn dụ hình học** (`1 hình = 1 khái niệm`); tránh nhồi > 3 biểu thức hoặc dày đặc chữ trên màn hình.
   - Đánh tiêu điểm bằng **một chi tiết vàng rực duy nhất** (đỉnh đồi, thanh thước ngang, dòng đáp án đúng, chấm tròn trọng số ngành).
5. **Gợi ý phối hợp nhịp CAM-WN (`vocal_delivery` / `bgm_energy` / `sfx_cue`):**
   - **Cảnh 1 (Hook câu đố):** `punch_urgent` + `bgm_energy="rise"` + `sfx_cue="camera_click"` hoặc `"low_thud"`.
   - **Cảnh 2–5 (Thu gọn & Micro-History & Hình 1):** `normal_story` + `bgm_energy="rise"`.
   - **Cảnh 6 (Twist bản chất):** `whisper_suspense` hoặc `punch_urgent` + `bgm_energy="drop"` + `sfx_cue="deep_sub_drop"`.
   - **Cảnh 7–8 (Mở rộng & Bản đồ ngành):** `normal_story` + `bgm_energy="peak"` + `sfx_cue="none"`.
   - **Cảnh cuối (Callback & Thử thách):** `solemn_slow` + `bgm_energy="calm"` + `sfx_cue="none"`."""

THINKING_PROCESS = """═══ QUY TRÌNH `thinking_process` (≤ 110 từ, viết trước khi viết cảnh) ═══
(1) Câu đố đời thường nào ở Cảnh 1 kích thích người học tự tính mà không dùng chữ số trong `narration_vn`? (2) Thu gọn chủ đề về 1–3 ẩn dụ hình học cụ thể nào (cây thước độ dốc, lát mỏng diện tích, bảng số ma trận)? (3) Chọn 1–2 nhân vật/tư liệu lịch sử nào cho `real_photo` Wikimedia đen-trắng? (4) Cảnh 6 Twist tóm bản chất thế nào và câu kết Cảnh cuối callback lại Cảnh 1 + gài thử thách bình luận ra sao?"""

MODEL_SELF_CHECK = (
    "Đúng phong cách `visual_math_essay`: mở bằng câu đố đời thường, có ≥ 1 cảnh Micro-History dùng `real_photo` B&W, "
    "ẩn dụ hình học nền đen lưới mờ nhấn vàng hổ phách (1 hình = 1 khái niệm), không chữ số/tiếng Anh trong `narration_vn`, "
    "không dùng cartoon/slide/clipart."
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
    style_tag=STYLE_TAG,
)


def render_prompt(
    user_request: str,
    intent_mode: str = "NO_HUMAN_BROLL",
    prompt_feedback: str = "",
    filtered_character_context: str = "",
    source_context: str = "",
    rationale: str = "",
) -> str:
    """Kết xuất prompt đầy đủ cho mô hình `visual_math_essay`."""
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

