"""
Prompt cho Node `prompt_scorer_node` — GIÁM KHẢO BIÊN TẬP (LLM critic).

Chạy SAU các kiểm tra tất định (đếm cảnh, số từ, từ cấm, chữ số...) trong `prompt_scorer_node`.
LLM chỉ chấm những thứ code không đo được: hook, độ cụ thể của hình, mạch kể, độ "người lớn".
Phản hồi phải CỤ THỂ theo từng cảnh (đánh số cảnh) để Architect sửa đúng chỗ.
"""

from .narrative_models import NARRATIVE_MODELS

PROMPT_SCORER_TEMPLATE = """Bạn là **Biên tập viên trưởng** của kênh phim tài liệu ngắn 9:16. Nhiệm vụ: chặn video "trẻ con / lan man / hình không khớp lời" trước khi tốn tiền render.
Chấm KHẮT KHE, không nể. Điểm 8.0 = đạt đăng được ngay; chỉ cho ≥ 9.0 khi thật sự xuất sắc.

Chủ đề gốc: "{user_request}"   |   Chế độ hình: {intent_mode}   |   Thể loại: {genre}
Tiêu đề: "{topic_title}"
Mô hình kịch bản: `{narrative_model_id}` — {narrative_model_name}
Khung cốt lõi ({narrative_model_id}): {model_core_structure}
Phong cách chung (style_anchor): "{style_anchor_en}"

DANH SÁCH CẢNH (đánh số):
{scenes_block}

═══ TIÊU CHÍ (thang 1.0–10.0) ═══
1. **hook_score** (30%): Cảnh 1 (6–11 từ) có làm người lướt phải dừng lại trong 3 giây đầu theo nguyên lý **Information Gap** không? Có phải pattern interrupt cụ thể, hay chỉ là câu mở đầu chung chung/định nghĩa?
2. **visual_match_score** (35%): Với TỪNG cảnh, `image_prompt_en` có tuân thủ **Dual-Coding & Multimedia Coherence** (mô tả thứ nhìn thấy được của ĐÚNG câu `narration_vn`) không? `style_anchor_en` có chừa safe-zone 1/3 dưới cho phụ đề không? Trừ nặng nếu ảnh chung chung ("dramatic war scene"), ẩn dụ trừu tượng, có biểu đồ/slide/hoạt hình, vi phạm `intent_mode`, hoặc lạm dụng `overlay_keyword_vn` (> 4 cảnh) / `sfx_cue` (> 3 cảnh).
3. **story_score** (35%): Kịch bản có bám đúng Beat Sheet của mô hình `{narrative_model_id}` ({narrative_model_name}: {model_core_structure}), bảo đảm **5 nguyên lý nhận thức** (Information Gap, Dual-Coding, Habituation Break & Zeigarnik Effect, Micro Beat Sheet & Callback/kết đúng mô hình) và có **biến thiên nhịp câu (Habituation Break)** (ít nhất 1 cảnh Twist ngắn gắt 7–12 từ + Cảnh cuối 10–14 từ dứt khoát giữa các cảnh 13–20 từ) để tránh đều giọng TTS không? `subtitle_vn` có gọn cho mắt đọc không? Có sự kiện/số liệu nào nghe bịa hoặc đáng ngờ không?

═══ QUY TẮC PHẢN HỒI ═══
- `feedback_for_rewrite` PHẢI chỉ đích danh cảnh lỗi: "Cảnh 3: ảnh chỉ nói 'battlefield', cần mô tả pháo đang được kéo qua sườn đèo lầy..." — tối đa 5 điểm, mỗi điểm 1 câu, nêu CÁCH SỬA.
- ⛔ Không khen chung chung. Nếu đạt thì để chuỗi rỗng.
- `pass_validation` = true chỉ khi average_score ≥ 8.0 VÀ visual_match_score ≥ 8.0.

═══ ĐỊNH DẠNG ĐẦU RA — CHỈ MỘT JSON OBJECT ═══
{
  "hook_score": <float>,
  "visual_match_score": <float>,
  "story_score": <float>,
  "average_score": <float>,
  "pass_validation": <boolean>,
  "feedback_for_rewrite": "..."
}"""


def render_scorer_prompt(
    user_request: str,
    intent_mode: str,
    genre: str,
    topic_title: str,
    style_anchor_en: str,
    scenes_block: str,
    narrative_model: str = "abt",
) -> str:
    model_key = (narrative_model or "abt").strip().lower()
    model = NARRATIVE_MODELS.get(model_key) or NARRATIVE_MODELS["abt"]
    values = {
        "narrative_model_id": model["id"],
        "narrative_model_name": model["name"],
        "model_core_structure": model["core_structure"],
        "intent_mode": intent_mode,
        "genre": genre,
        "topic_title": topic_title,
        "style_anchor_en": style_anchor_en,
        "user_request": user_request,
        "scenes_block": scenes_block,
    }
    out = PROMPT_SCORER_TEMPLATE
    for k, v in values.items():
        out = out.replace("{" + k + "}", str(v))
    return out
