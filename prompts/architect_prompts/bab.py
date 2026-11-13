"""
Prompt độc lập cho mô hình `bab` — BAB (Before – After – Bridge).

Nhóm: Thuyết phục / Bán hàng / B2B.
"""

from __future__ import annotations

from ._shared import build_model_prompt_template, render_model_prompt_template

MODEL_ID = "bab"
MODEL_NAME = "BAB (Before – After – Bridge)"
GROUP_LABEL = "Thuyết phục / Bán hàng / B2B"
CORE_STRUCTURE = "Before (Trước) -> After (Sau) -> Bridge (Giải pháp cầu nối)"
BEST_FOR = "Case study B2B, chuyển đổi số, triển khai hạ tầng/cloud, tối ưu vận hành"

BEAT_SHEET = """- **Cảnh 1 (HOOK — Before, 6–11 từ, `punch_urgent`):** Cắt thẳng vào cảnh tượng nghẽn cổ chai hoặc độ trễ vô lý trong quy trình cũ bằng tương phản Before–After.
- **Cảnh 2 (BEFORE 1 — Hiện trạng thủ công, 13–18 từ):** Hình ảnh thực địa của quy trình cũ: giấy tờ chất đống, dây cáp rối, thao tác lặp lại thủ công.
- **Cảnh 3 (BEFORE 2 — Chi phí ẩn + Open Loop, 13–20 từ):** Chỉ ra thời gian chết và sai sót tích tụ; cuối cảnh mở vòng lặp tương phản về một trạng thái vận hành hoàn toàn khác.
- **Cảnh 4 (AFTER 1 — Bức tranh sau chuyển đổi, 13–18 từ):** Hiện trường mới gọn, nhanh, sạch nút thắt; cho người xem thấy kết quả thực tế trước khi giải thích cách làm.
- **Cảnh 5 (AFTER 2 — Chỉ số cải thiện đời thật, 13–20 từ):** Quy đổi thành quả thành thời gian, công suất hoặc độ ổn định cụ thể (viết thuần chữ trong `narration_vn`, số gọn ở `subtitle_vn`).
- **Cảnh 6 (TWIST — Điểm nối giữa hai thế giới, 7–12 từ, kết thanh Trắc):** Câu cắt gắt đặt câu hỏi hoặc chỉ thẳng điều gì đã tạo nên khoảng cách Before–After.
- **Cảnh 7 (BRIDGE 1 — Cây cầu kiến trúc/giải pháp, 13–18 từ):** Bóc tách cơ chế cốt lõi nối từ trạng thái cũ sang mới (tự động hóa, chuẩn hóa luồng dữ liệu, hạ tầng phân tán).
- **Cảnh 8–9 (BRIDGE 2 — Triển khai thực tế & độ bền, 13–18 từ/cảnh):** Hình ảnh vận hành chuyển giao ổn định tại hiện trường, không gián đoạn công việc cũ. Tối đa tổng 8–10 cảnh toàn clip.
- **Cảnh cuối (CHỐT GIÁ TRỊ — 10–14 từ, `solemn_slow`):** Đặt `--` trước 3–4 từ đắt giá cuối; khẳng định cầu nối đã chuyển vận hành từ bị động sang chủ động, callback về Cảnh 1."""

MODEL_GUIDANCE = """1. **Kỹ thuật Hook Staccato 2 nhịp (6–11 từ, không chữ số, chất tài liệu thực tế):**
   - Cấu trúc: [Nút thắt Before cụ thể] + `.` + [Cú chuyển After dứt khoát].
   - Ví dụ chuẩn (chất phim tài liệu vận hành): *"Hồ sơ kẹt ba tuần. Nay thông suốt trong một đêm."* hoặc *"Cả phòng chờ một dấu mộc. Nay xong trước giờ trưa."*
   - Tránh văn mẫu bán hàng: *"Bạn muốn lột xác doanh nghiệp?", "Giải pháp đột phá thời đại mới..."*.
2. **Chiến lược Twist & Open Loop:**
   - Cuối Cảnh 3 đặt **Open Loop**: *"Cùng khối lượng việc ấy -- nhưng một tuần sau không còn ai phải tăng ca."*
   - Cảnh 6 là **Twist ngắn gắt (7–12 từ)** kết thanh Trắc làm bản lề chuyển từ After sang Bridge (vd: *"Khác biệt không nằm ở nhân lực. Nó nằm ở cây cầu này."*).
3. **Kỹ thuật chốt CTA / giá trị theo `outro_style`:**
   - Không kêu gọi "mua ngay"; chốt bằng giá trị bền vững của cây cầu giải pháp (Bridge): *"Đổi đúng hạ tầng -- guồng máy cũ tự khắc chạy nhanh hơn."*
4. **Bẫy cần tránh của `bab`:**
   - Lạm dụng mỹ từ "lột xác, thần kỳ"; miêu tả After bằng dashboard/chart/3D ảo (vi phạm RULE #2); kể phần Bridge dài dòng như tài liệu kỹ thuật khó nghe trên TTS.
5. **Gợi ý phối nhịp CAM-WN (`vocal_delivery` / `bgm_energy` / `sfx_cue`):**
   - Cảnh 1 (Hook): `punch_urgent` + `rise` + `low_thud`.
   - Cảnh 2–3 (Before): `normal_story` + `low` + `none`.
   - Cảnh 4–5 (After): `normal_story` + `rise` + `subtle_whoosh` (chỉ tại Cảnh 4 khi mở cảnh After).
   - Cảnh 6 (Twist): `whisper_suspense` (hoặc `punch_urgent`) + `drop` + `camera_click`.
   - Cảnh 7–Kế cuối (Bridge): `normal_story` + `peak` + `none`.
   - Cảnh cuối (Chốt giá trị): `solemn_slow` + `calm` + `none`."""

THINKING_PROCESS = """═══ QUY TRÌNH `thinking_process` (≤ 110 từ, viết trước khi viết cảnh) ═══
(1) Nút thắt vận hành Before nào dễ nhận ra nhất bằng mắt thường tại hiện trường?
(2) Trạng thái After tương ứng mang lại thay đổi cụ thể gì khiến người xem muốn biết "bằng cách nào"?
(3) Hook Staccato 2 nhịp không số nào nén cặp đối lập Before–After trong 3 giây đầu, và Twist Cảnh 6 mở khóa phần Bridge ra sao?
(4) 3 cảnh quay thực địa phân biệt rõ Before – After – Bridge + nhịp nhạc `driving_modern` chuyển từ `low` sang `peak`?"""

MODEL_SELF_CHECK = (
    "Đúng mạch `bab` (Before cảnh 1–3 -> After cảnh 4–5 -> Twist điểm nối cảnh 6 -> Bridge cảnh 7–kế cuối -> Chốt giá trị cảnh cuối), "
    "tương phản Before/After bằng vật thể và hành động thực tế, không biểu đồ hay UI."
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
    """Kết xuất prompt hoàn chỉnh cho mô hình `bab`."""
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
