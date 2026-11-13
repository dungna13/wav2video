"""
Template prompt độc lập cho mô hình kịch bản `in_medias_res` — In Medias Res (Giữa cao trào).
"""

from __future__ import annotations

from ._shared import build_model_prompt_template, render_model_prompt_template

MODEL_ID = "in_medias_res"
MODEL_NAME = "In Medias Res (Giữa cao trào)"
GROUP_LABEL = "Phim Tài liệu / Edutainment / Kể chuyện"
CORE_STRUCTURE = "Nhảy thẳng vào khoảnh khắc căng nhất -> Tua ngược giải thích -> Quay lại kết cục"
BEST_FOR = "Vụ án, chiến dịch quân sự, thảm họa, sự cố sinh tồn"

BEAT_SHEET = """- **Cảnh 1 (HOOK — Giữa cơn bão, 6–11 từ):** Ném thẳng người xem vào giây phút nguy kịch nhất đang xảy ra ngay tại hiện trường.
- **Cảnh 2 (Tua ngược — Đặt câu hỏi sinh tử):** Đóng băng khoảnh khắc ở Cảnh 1 và kéo đồng hồ ngược về điểm khởi phát ban đầu.
- **Cảnh 3 (Mầm họa đầu tiên & Open Loop):** Chỉ ra tín hiệu bất thường hoặc quyết định tưởng vô hại nhưng kích hoạt chuỗi domino.
- **Cảnh 4 (Mắt xích leo thang 1):** Áp lực dồn nén tăng lên khi sai lầm đầu tiên gặp điều kiện bất lợi ngoài dự tính.
- **Cảnh 5 (Mắt xích leo thang 2 & Open Loop):** Cơ hội cứu vãn cuối cùng bị bỏ lỡ hoặc tín hiệu cảnh báo bị phớt lờ.
- **Cảnh 6 (TWIST — Điểm gãy 7–12 từ):** Chi tiết bước ngoặt khiến cục diện chính thức trượt qua ranh giới không còn đường lui.
- **Cảnh 7 (Khoảnh khắc bùng nổ — Khớp lại Cảnh 1):** Diễn biến dữ dội tại hiện trường khép vòng thời gian về đúng giây phút mở đầu.
- **Cảnh 8 (Phản ứng hiện trường — Tùy chọn đến Cảnh 9):** Đếm nhịp hậu quả trực tiếp ngay sau cú va chạm hoặc phát súng cuối.
- **Cảnh cuối (Kết Callback 10–14 từ):** Dư chấn thực địa còn sót lại tại hiện trường và cái giá lịch sử."""

MODEL_GUIDANCE = """1. **Kỹ thuật Hook Staccato 2 nhịp (không chữ số):**
   - Nhịp một cắt thẳng vào âm thanh/hình ảnh cận kề cái chết hoặc thảm họa; nhịp hai chêm chi tiết bất thường ngay giữa hỗn loạn.
   - Ví dụ mẫu: *"Khoang lái tối đen. Chuông báo độ cao gào thét."* / *"Nước tràn ngập boong. Cánh cửa sắt vẫn khóa chặt."*
2. **Chiến lược Twist & Auditory Open Loop:**
   - Cuối Cảnh 3 đặt câu lửng tua ngược (*"Không ai ngờ tờ lệnh ký vội ấy -- lại châm ngòi cho đêm định mệnh."*).
   - Cảnh 6 là điểm gãy không thể đảo ngược (7–12 từ), ưu tiên động từ mạnh và kết thúc bằng thanh **Trắc** (*đứt, sập, tắt, nổ, muộn*).
3. **Kỹ thuật chốt `outro_style`:**
   - Khép vòng quay lại đúng khoảnh khắc hỗn loạn hoặc vật chứng ở Cảnh 1, nhấn mạnh hệ quả thực địa bằng câu 10–14 từ hãm nhịp `--`.
4. **Bẫy cần tránh của `in_medias_res`:**
   - Mở đầu bằng lời giới thiệu bối cảnh lịch sử ("Vào năm... tại vùng...") làm mất hoàn toàn chất "nhảy giữa cơn bão".
   - Tua ngược rồi kể tuột tới kết thúc mà quên khép vòng nối khớp lại tình huống Cảnh 1.
   - Dàn trải quá nhiều nhân vật phụ hoặc thông số kỹ thuật khiến mạch sinh tồn bị loãng.
5. **Gợi ý nhịp CAM-WN (`vocal_delivery` / `bgm_energy` / `sfx_cue`):**
   - Cảnh 1 (Giữa cơn bão): `punch_urgent` | `bgm_energy: "peak"` | `sfx_cue: "low_thud"`.
   - Cảnh 2–3 (Tua ngược): `normal_story` | `bgm_energy: "drop"` → `"low"` | `sfx_cue: "subtle_whoosh"`.
   - Cảnh 4–5 (Leo thang): `normal_story` | `bgm_energy: "rise"` | `sfx_cue: "none"`.
   - Cảnh 6 (Điểm gãy): `whisper_suspense` | `bgm_energy: "drop"` | `sfx_cue: "heartbeat_pulse"` hoặc `"deep_sub_drop"`.
   - Cảnh 7–Kế cuối (Bùng nổ): `punch_urgent` | `bgm_energy: "peak"` | `sfx_cue: "none"`.
   - Cảnh cuối (Dư chấn): `solemn_slow` | `bgm_energy: "calm"` | `sfx_cue: "clock_tick_stop"` hoặc `"none"`."""

THINKING_PROCESS = """═══ QUY TRÌNH `thinking_process` (≤ 110 từ, viết trước khi viết cảnh) ═══
(1) Giây phút nghẹt thở nhất của biến cố nằm ở khoảnh khắc nào để mở Cảnh 1?
(2) Sai lầm hoặc điềm báo nào trước đó khởi phát chuỗi domino, và điểm gãy không đường lui nằm ở đâu?
(3) Hook Staccato 2 nhịp không chữ số nào ném tai người nghe vào tâm bão cùng Open Loop kéo qua đoạn tua ngược?
(4) Hình ảnh hiện trường chân thực nào khép vòng Cảnh 1–7–cuối, cùng `voice_profile`, `music_mood`, `bgm_alignment` tương ứng?"""

MODEL_SELF_CHECK = (
    "Cảnh 1 nhảy thẳng giữa cao trào, Cảnh 2–3 tua ngược hợp lý, Cảnh 6 có điểm gãy 7–12 từ, "
    "và Cảnh 7–cuối khép vòng khớp lại biến cố mở đầu."
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
    """Kết xuất prompt hoàn chỉnh cho mô hình `in_medias_res`."""
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
