"""
Prompt độc lập cho mô hình `pas` — PAS (Problem – Agitate – Solution).

Nhóm: Thuyết phục / Bán hàng / B2B.
"""

from __future__ import annotations

from ._shared import build_model_prompt_template, render_model_prompt_template

MODEL_ID = "pas"
MODEL_NAME = "PAS (Problem – Agitate – Solution)"
GROUP_LABEL = "Thuyết phục / Bán hàng / B2B"
CORE_STRUCTURE = "Problem (Vấn đề) -> Agitate (Khoét nỗi đau) -> Solution (Giải pháp)"
BEST_FOR = "Quảng cáo giải pháp, sản phẩm/dịch vụ, thuyết phục xử lý rủi ro/nỗi đau"

BEAT_SHEET = """- **Cảnh 1 (HOOK — Problem, 6–11 từ, `punch_urgent`):** Ném thẳng người xem vào dấu hiệu rò rỉ, thất thoát hoặc đứt gãy vận hành đang diễn ra ngay lúc này. Hình ảnh vật lý cụ thể (màn hình cảnh báo, xấp hóa đơn, phòng máy tối đèn).
- **Cảnh 2 (PROBLEM — Triệu chứng bề mặt, 13–18 từ):** Mô tả biểu hiện quen thuộc mà doanh nghiệp/người dùng thường bỏ qua vì tưởng là sự cố vặt.
- **Cảnh 3 (AGITATE 1 — Cái giá hữu hình + Open Loop, 13–20 từ):** Đo bằng tiền mặt, giờ công, hoặc cơ hội bị kẹt; cuối cảnh đặt vế mở lửng buộc tai người nghe chờ xem hậu quả dây chuyền.
- **Cảnh 4 (AGITATE 2 — Hiệu ứng domino ẩn, 13–20 từ):** Phơi bày rủi ro âm thầm phía sau (mất uy tín, phạt hợp đồng, khách lặng lẽ rời bỏ) bằng vật thể đời thật, không dùng biểu đồ/slide.
- **Cảnh 5 (TWIST — Ngưỡng báo động, 7–12 từ, kết thanh Trắc):** Cú cắt gắt vạch trần nguyên nhân gốc hoặc ngưỡng không thể trì hoãn thêm (kèm `sfx_cue` cắt nhịp).
- **Cảnh 6 (SOLUTION 1 — Điểm chạm giải pháp, 13–18 từ):** Đưa giải pháp xuất hiện như một cơ chế can thiệp thực địa (bàn tay thao tác, thiết bị, quy trình mới vận hành), không khoe khẩu hiệu.
- **Cảnh 7 (SOLUTION 2 — Cơ chế khóa lỗ hổng, 13–20 từ):** Giải thích ngắn gọn vì sao cơ chế này chặn đứng được nút thắt vừa nêu ở Cảnh 3–5.
- **Cảnh 8–9 (PROOF — Bằng chứng vận hành, 13–18 từ/cảnh):** Cảnh thực tế sau khi xử lý: tiến độ thông suốt, bảng log sạch lỗi, con người làm việc chủ động (tuân `intent_mode`). Tối đa tổng 8–10 cảnh toàn clip.
- **Cảnh cuối (KẾT & CTA — Chốt chuyển đổi, 10–14 từ, `solemn_slow`):** Đặt `--` trước 3–4 từ đắt giá cuối; chốt bước chuyển từ trạng thái thất thoát sang hành động xử lý dứt điểm, callback về Cảnh 1."""

MODEL_GUIDANCE = """1. **Kỹ thuật Hook Staccato 2 nhịp (6–11 từ, không chữ số, chất tài liệu thực tế):**
   - Cấu trúc: [Cụm 2–4 từ dựng hiện trường lạnh] + `.` hoặc `--` + [Mệnh đề chỉ thẳng vết rò rỉ].
   - Ví dụ chuẩn (không sến quảng cáo truyền hình): *"Đèn phòng máy vẫn sáng. Nhưng toàn bộ dữ liệu đã mất."* hoặc *"Kho hàng vẫn chật kín. Nhưng dòng tiền đã cạn."*
   - Tránh mở đầu kiểu TVC: *"Bạn đang đau đầu vì..."*, *"Đừng lo lắng nữa..."*.
2. **Chiến lược Twist & Open Loop:**
   - Cuối Cảnh 3 chèn **Auditory Open Loop**: *"Nhưng phần tiền mất trên sổ sách -- chưa phải thứ đắt nhất."* để kéo qua Cảnh 4.
   - Cảnh 5 là **Twist ngắn gắt (7–12 từ)** kết thúc bằng thanh Trắc (vd: *"Lỗi không nằm ở nhân sự. Nó nằm ở lỗ hổng cũ."*).
3. **Kỹ thuật chốt CTA / giá trị theo `outro_style`:**
   - Chuyển thẳng từ trạng thái mất kiểm soát sang hành động xử lý dứt điểm, không ép mua thô bạo. Ví dụ nhịp `--`: *"Đừng đợi sự cố gõ cửa -- hãy bịt lỗ hổng ngay hôm nay."*
4. **Bẫy cần tránh của `pas`:**
   - Dọa nạt phóng đại, rao giảng sáo rỗng ở đoạn Agitate; biến đoạn Solution thành brochure liệt kê tính năng khô khan hoặc ảnh chụp màn hình giao diện UI (vi phạm RULE #2).
5. **Gợi ý phối nhịp CAM-WN (`vocal_delivery` / `bgm_energy` / `sfx_cue`):**
   - Cảnh 1 (Hook): `punch_urgent` + `rise` + `low_thud`.
   - Cảnh 2–4 (Agitate): `normal_story` -> `whisper_suspense` + `rise`/`peak` + `none`.
   - Cảnh 5 (Twist): `punch_urgent` + `drop` + `deep_sub_drop` (hoặc `clock_tick_stop`).
   - Cảnh 6–Kế cuối (Solution): `normal_story` + `rise`/`peak` + `none` (hoặc 1 `camera_click` ở Cảnh 6).
   - Cảnh cuối (CTA): `solemn_slow` + `calm` + `none` (hoặc `low_thud`)."""

THINKING_PROCESS = """═══ QUY TRÌNH `thinking_process` (≤ 110 từ, viết trước khi viết cảnh) ═══
(1) Vết rò rỉ hoặc nỗi đau cụ thể nào khiến người xem giật mình nhận ra họ đang trả giá mỗi ngày?
(2) Hậu quả dây chuyền nào ở tầng Agitate chứng minh trì hoãn sẽ đắt hơn chi phí xử lý?
(3) Hook Staccato 2 nhịp không số nào dựng ngay hiện trường vấn đề trong 3 giây đầu, và Open Loop cuối Cảnh 3 dẫn vào Twist Cảnh 5 ra sao?
(4) 3 hình ảnh đời thực đại diện cho Problem – Agitate – Solution + cách giữ nhạc `tense_epic`/`driving_modern` không sến TVC?"""

MODEL_SELF_CHECK = (
    "Đúng mạch `pas` (Problem cảnh 1–2 -> Agitate cảnh 3–4 -> Twist ngưỡng cảnh 5 -> Solution cảnh 6–kế cuối -> CTA cảnh cuối), "
    "giữ giọng tài liệu B2B sắc lạnh, không sáo ngữ quảng cáo truyền hình."
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
    """Kết xuất prompt hoàn chỉnh cho mô hình `pas`."""
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
