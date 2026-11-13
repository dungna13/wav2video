"""
Prompt chuyên biệt cho mô hình `myth_vs_reality` (Myth vs. Reality — Lầm tưởng vs. Sự thật).

Nhóm: Short-Form Viral (TikTok / Reels / Shorts).
"""

from __future__ import annotations

from ._shared import build_model_prompt_template, render_model_prompt_template

MODEL_ID = "myth_vs_reality"
MODEL_NAME = "Myth vs. Reality (Lầm tưởng vs. Sự thật)"
GROUP_LABEL = "Short-Form Viral (TikTok / Reels / Shorts)"
CORE_STRUCTURE = "Lầm tưởng phổ biến -> Phá vỡ định kiến -> Sự thật ẩn -> Bằng chứng"
BEST_FOR = "Giải mã sự thật, phá định kiến lịch sử/khoa học/văn hóa, lật ngược quan niệm sai"

BEAT_SHEET = """- **Cảnh 1 (HOOK — Phủ định trực diện, 6–11 từ):** Bẻ gãy ngay định kiến quen thuộc nhất bằng cú Staccato 2 nhịp khiến người xem giật mình vì thứ mình tin lâu nay có thể sai.
- **Cảnh 2 (MYTH 1 — Dựng lại niềm tin cũ, 13–18 từ):** Miêu tả hình ảnh cụ thể của lời đồn, sách cũ hoặc quan niệm đại chúng mà ai cũng từng nghe.
- **Cảnh 3 (MYTH 2 — Điểm nứt của lầm tưởng, 13–19 từ):** Đưa chi tiết phi lý ẩn bên trong niềm tin cũ; cuối câu cài **Auditory Open Loop** dẫn sang góc khuất chưa kể.
- **Cảnh 4 (REALITY 1 — Cơ chế ẩn lộ diện, 13–19 từ):** Hé lộ nguyên nhân thật sự (địa chất, kinh tế, kỹ thuật, tâm lý...) mà góc nhìn bề mặt bỏ sót.
- **Cảnh 5 (REALITY 2 — Bằng chứng đối chứng, 13–18 từ):** Đặt vật chứng hoặc bối cảnh thực tế đối lập hoàn toàn với huyền thoại ở Cảnh 2, cài nhịp chờ sang cú lật.
- **Cảnh 6 (TWIST — Phá vỡ ngắn gắt, 7–12 từ):** Câu chốt sắc lạnh đảo ngược hoàn toàn kết luận cũ (kết thanh Trắc dứt khoát).
- **Cảnh 7 (EVIDENCE 1 — Xác thực thực địa, 13–18 từ):** Dẫn chứng khảo cổ, hồ sơ ghi chép hoặc thí nghiệm đo được để khóa chặt sự thật mới.
- **Cảnh 8–9 (EVIDENCE 2 — Hệ quả còn sót lại, 12–17 từ, tùy chọn nếu 9–10 cảnh):** Giải thích vì sao lầm tưởng vẫn tồn tại đến hôm nay hoặc dấu tích thực tế còn lại.
- **Cảnh cuối (CALLBACK — 10–14 từ):** Quay lại đúng hình ảnh/đối tượng của Hook mở đầu nhưng với chân lý mới gọn ghẽ, đặt `--` trước cụm từ chốt để tạo Sonic Echo."""

MODEL_GUIDANCE = """1. **Kỹ thuật Hook "Staccato 2 nhịp" (6–11 từ, đọc < 3s, KHÔNG chữ số):**
   - Nhịp 1 (2–4 từ): Gọi thẳng biểu tượng hoặc định kiến phổ biến, ngắt gắt bằng dấu chấm hoặc `--`.
   - Nhịp 2 (4–7 từ): Phủ định thẳng thừng hoặc chỉ ra sự thật ngược chiều gây sốc.
   - *Ví dụ tiếng Việt chuẩn (không số):* *"Kim tự tháp do nô lệ xây. Câu chuyện đó hoàn toàn sai."* / *"Cá vàng nhớ được vài giây. Khoa học vừa chứng minh điều ngược lại."*
2. **Chiến lược Twist & Open Loop:**
   - Phải dựng Myth thật thuyết phục ở Cảnh 2–3 trước khi đập vỡ: người xem chỉ thấy "sướng" khi sự thật đánh vào đúng thứ họ vừa công nhận.
   - Đặt **Auditory Open Loop** cuối Cảnh 3 (vd: *"Nhưng nếu nhìn kỹ vào vết cắt đá này..."*) và cuối Cảnh 5 trước khi bung Cảnh 6 (Twist **7–12 từ**, kết thanh Trắc) để chuyển pha từ "ngờ vực" sang "lật tẩy".
3. **Kỹ thuật chốt (`outro_style`):**
   - Thực hiện **Bookend Callback**: quay lại đúng hình ảnh/lầm tưởng ở Cảnh 1 để đặt dấu chấm hết bằng sự thật vừa chứng minh.
   - Hãm nhịp bằng `--` trước 3–4 từ kết để tạo cảm giác chốt hạ đáng tin cậy, không lên lớp dạy đời.
4. **Bẫy cần tránh:**
   - Phủ định suông không có bằng chứng vật lý/thực địa ở Cảnh 7–8 (người xem sẽ phản bác trong bình luận).
   - Bêu riếu khán giả ("Đó là vì bạn bị lừa") gây phản cảm; hãy đặt lỗi ở "câu chuyện truyền miệng" hoặc "bản dịch cũ".
   - Liệt kê sự thật rời rạc, quên quay về đóng khung lầm tưởng mở đầu.
5. **Gợi ý phối hợp nhịp CAM-WN (`vocal_delivery` / `bgm_energy` / `sfx_cue`):**
   - **Cảnh 1 (Hook phủ định):** `punch_urgent` + `bgm_energy="rise"` + `sfx_cue="low_thud"`.
   - **Cảnh 2–3 (Vẽ lại Myth):** `normal_story` + `bgm_energy="rise"`, `sfx_cue="none"` (Cảnh 3 có thể chùng nhẹ vào cuối).
   - **Cảnh 4–5 (Bóc Reality):** `whisper_suspense` hoặc `normal_story` + `bgm_energy="rise"` → `"peak"`, `sfx_cue="none"`.
   - **Cảnh 6 (Twist phá vỡ):** `punch_urgent` + `bgm_energy="drop"` + `sfx_cue="deep_sub_drop"` (cắt gắt niềm tin cũ).
   - **Cảnh 7–Kế cuối (Evidence):** `normal_story` + `bgm_energy="rise"` → `"peak"`, `sfx_cue="camera_click"` (tối đa 1 điểm nhấn hồ sơ/vật chứng nếu tổng SFX ≤ 3).
   - **Cảnh cuối (Callback):** `solemn_slow` + `bgm_energy="calm"` + `sfx_cue="none"`."""

THINKING_PROCESS = """═══ QUY TRÌNH `thinking_process` (≤ 110 từ, viết trước khi viết cảnh) ═══
(1) Lầm tưởng đại chúng nào về chủ đề này ăn sâu nhất để đánh gãy ngay bằng Hook Staccato hai nhịp? (2) Chi tiết phi lý nào bên trong lầm tưởng mở đường cho Open Loop ở cảnh ba? (3) Sự thật ẩn và cú Twist ngắn bảy đến mười hai từ dựa trên bằng chứng thực địa cụ thể nào? (4) Cảnh cuối quay về đối chiếu hình ảnh mở đầu ra sao, phối giọng từ phủ định sang thì thầm đối chứng rồi lắng đọng như thế nào?"""

MODEL_SELF_CHECK = "Đúng cấu trúc `myth_vs_reality`: gọi rõ Myth phổ biến, đập tan bằng cơ chế ẩn + bằng chứng thực địa ở Cảnh 7+, và Cảnh cuối Callback về đúng định kiến ở Hook."

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
    """Kết xuất prompt đầy đủ cho mô hình `myth_vs_reality`."""
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
