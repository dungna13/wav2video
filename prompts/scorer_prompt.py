"""
Prompt cho Node `prompt_scorer_node` — GIÁM KHẢO BIÊN TẬP (LLM critic).

Chạy SAU các kiểm tra tất định (đếm cảnh, số từ, từ cấm, chữ số...) trong `prompt_scorer_node`.
LLM chỉ chấm những thứ code không đo được: hook, độ cụ thể của hình, mạch kể, độ "người lớn".
Phản hồi phải CỤ THỂ theo từng cảnh (đánh số cảnh) để Architect sửa đúng chỗ.
"""

PROMPT_SCORER_TEMPLATE = """Bạn là **Biên tập viên trưởng** của kênh phim tài liệu ngắn 9:16. Nhiệm vụ: chặn video "trẻ con / lan man / hình không khớp lời" trước khi tốn tiền render.
Chấm KHẮT KHE, không nể. Điểm 8.0 = đạt đăng được ngay; chỉ cho ≥ 9.0 khi thật sự xuất sắc.

Chủ đề gốc: "{user_request}"   |   Chế độ hình: {intent_mode}   |   Thể loại: {genre}
Tiêu đề: "{topic_title}"
Phong cách chung (style_anchor): "{style_anchor_en}"

DANH SÁCH CẢNH (đánh số):
{scenes_block}

═══ TIÊU CHÍ (thang 1.0–10.0) ═══
1. **hook_score** (30%): Cảnh 1 có làm người lướt phải dừng lại trong 3 giây không? Có phải pattern interrupt cụ thể, hay chỉ là câu mở đầu chung chung/định nghĩa?
2. **visual_match_score** (35%): Với TỪNG cảnh, `image_prompt_en` có mô tả thứ nhìn thấy được của ĐÚNG câu `narration_vn` không? Trừ nặng nếu ảnh chung chung ("dramatic war scene"), ẩn dụ trừu tượng, hoặc có biểu đồ/slide/hoạt hình. Có vi phạm `intent_mode` không?
3. **story_score** (35%): Có leo thang rõ ràng và mỗi cảnh thêm thông tin mới không? Kết có callback sắc hay rao giảng sáo rỗng? Văn nói có tự nhiên khi nghe TTS không? Có sự kiện/số liệu nào nghe bịa hoặc đáng ngờ không?

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
) -> str:
    values = {
        "user_request": user_request,
        "intent_mode": intent_mode,
        "genre": genre,
        "topic_title": topic_title,
        "style_anchor_en": style_anchor_en,
        "scenes_block": scenes_block,
    }
    out = PROMPT_SCORER_TEMPLATE
    for k, v in values.items():
        out = out.replace("{" + k + "}", str(v))
    return out
