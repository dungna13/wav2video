"""
Prompt độc lập cho mô hình `aida` — AIDA (Attention – Interest – Desire – Action).

Nhóm: Thuyết phục / Bán hàng / B2B.
"""

from __future__ import annotations

from ._shared import build_model_prompt_template, render_model_prompt_template

MODEL_ID = "aida"
MODEL_NAME = "AIDA (Attention – Interest – Desire – Action)"
GROUP_LABEL = "Thuyết phục / Bán hàng / B2B"
CORE_STRUCTURE = "Attention (Chú ý) -> Interest (Hứng thú) -> Desire (Khao khát) -> Action (Hành động)"
BEST_FOR = "Video landing page, ra mắt sản phẩm/nền tảng, chốt đăng ký/CTA"

BEAT_SHEET = """- **Cảnh 1 (ATTENTION — 6–11 từ, `punch_urgent`):** Khóa chặt chú ý trong 3 giây đầu bằng một sự thay đổi thực tế, phép đo thời gian gắt hoặc tuyên bố phá vỡ thói quen cũ.
- **Cảnh 2 (INTEREST 1 — Trình diễn cơ chế, 13–18 từ):** Đưa máy quay vào thẳng cách sản phẩm/nền tảng vận hành trong bối cảnh thật, giải thích cơ chế ngắn gọn cho tai nghe.
- **Cảnh 3 (INTEREST 2 — Gỡ điểm ma sát + Open Loop, 13–20 từ):** Cho thấy thao tác rườm rà trước đây biến mất ra sao; cuối cảnh đặt Open Loop dẫn sang điểm khác biệt cốt lõi.
- **Cảnh 4 (INTEREST 3 — Bối cảnh ứng dụng thực tế, 13–18 từ):** Mở rộng góc nhìn sang hiện trường làm việc thật (xưởng, văn phòng, phòng lab, tuyến vận hành) thay vì lý thuyết.
- **Cảnh 5 (TWIST — Lợi thế khác biệt, 7–12 từ, kết thanh Trắc):** Câu chốt ngắn gắt chỉ ra năng lực vượt trội không thể thay thế bởi cách làm cũ.
- **Cảnh 6 (DESIRE 1 — Kết quả kiểm chứng, 13–20 từ):** Biến tính năng thành lợi ích cảm nhận được (tốc độ, độ tin cậy, an toàn, giảm tải thực sự cho con người).
- **Cảnh 7–8 (DESIRE 2 — Bằng chứng & trải nghiệm thật, 13–18 từ/cảnh):** Cảnh thực tế nghiệm thu/bàn giao/triển khai trơn tru tạo niềm tin ra quyết định. Tối đa tổng 8–10 cảnh toàn clip.
- **Cảnh cuối (ACTION — Chốt CTA, 10–14 từ, `solemn_slow`):** Đặt `--` trước 3–4 từ đắt giá cuối; kêu gọi một bước hành động cụ thể, trực diện và thực hiện được ngay (dùng thử, đặt lịch kiểm thử, trải nghiệm)."""

MODEL_GUIDANCE = """1. **Kỹ thuật Hook Staccato 2 nhịp (6–11 từ, không chữ số, chất tài liệu thực tế):**
   - Cấu trúc: [Tuyên bố cắt bỏ/tốc độ] + `.` + [Hệ quả bất ngờ ở hiện trường].
   - Ví dụ chuẩn (chất phim giới thiệu sản phẩm tài liệu): *"Không thêm một dòng lệnh. Toàn bộ quy trình tự chạy."* hoặc *"Chậm một nhịp phản hồi. Mất trọn hợp đồng lớn."*
   - Tránh mở bài quảng cáo sáo: *"Xin chào mọi người...", "Hôm nay chúng tôi tự hào ra mắt..."*.
2. **Chiến lược Twist & Open Loop:**
   - Cuối Cảnh 3 đặt **Open Loop**: *"Nhưng tốc độ chưa phải lý do các đội kỹ thuật giữ nó lại -- đến phút cuối."*
   - Cảnh 5 là **Twist ngắn gắt (7–12 từ)** kết thanh Trắc khẳng định lợi thế độc tôn (vd: *"Thứ đối thủ không sao chép được chính là lõi dữ liệu sạch."*).
3. **Kỹ thuật chốt CTA / giá trị theo `outro_style`:**
   - Lời kêu gọi `Action` phải chỉ rõ MỘT bước kế tiếp cụ thể, không hô khẩu hiệu chung chung: *"Xem quy trình chạy thật -- đặt lịch thử nghiệm ngay hôm nay."*
4. **Bẫy cần tránh của `aida`:**
   - Biến phần Interest thành danh sách tính năng vô hồn; dùng ảnh mockup app, UI màn hình phát sáng hay chữ nổi trong `image_prompt_en` (vi phạm RULE #2); chốt CTA dồn dập kiểu bán hàng đa cấp.
5. **Gợi ý phối nhịp CAM-WN (`vocal_delivery` / `bgm_energy` / `sfx_cue`):**
   - Cảnh 1 (Attention): `punch_urgent` + `rise` + `low_thud`.
   - Cảnh 2–4 (Interest): `normal_story` + `rise` + `none`.
   - Cảnh 5 (Twist): `punch_urgent` (hoặc `whisper_suspense`) + `peak` (hoặc `drop`) + `camera_click`.
   - Cảnh 6–Kế cuối (Desire): `normal_story` + `peak` + `none` (hoặc `subtle_whoosh` ở Cảnh 6).
   - Cảnh cuối (Action): `solemn_slow` + `calm` + `none`."""

THINKING_PROCESS = """═══ QUY TRÌNH `thinking_process` (≤ 110 từ, viết trước khi viết cảnh) ═══
(1) Chi tiết vận hành nào của sản phẩm/nền tảng đủ sức giữ mắt người xem bận rộn trong 3 giây đầu?
(2) Cơ chế thực tế nào biến tính năng kỹ thuật thành ham muốn sở hữu (Desire) ở góc nhìn người ra quyết định?
(3) Hook Staccato 2 nhịp không số nào mở Attention, và Twist Cảnh 5 tách biệt sản phẩm khỏi lựa chọn cũ ra sao?
(4) 3 cảnh quay phần cứng/hiện trường đời thực (tránh UI/slide) + một bước Action duy nhất, rõ ràng ở cảnh cuối?"""

MODEL_SELF_CHECK = (
    "Đúng mạch `aida` (Attention cảnh 1 -> Interest cảnh 2–4 -> Twist khác biệt cảnh 5 -> Desire cảnh 6–kế cuối -> Action CTA cảnh cuối), "
    "không chụp màn hình UI/slide, CTA cụ thể một bước và không sáo rỗng."
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
    """Kết xuất prompt hoàn chỉnh cho mô hình `aida`."""
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
