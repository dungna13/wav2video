"""
Prompt dự phòng để tinh chỉnh lời đọc Voiceover (TTS Tiếng Việt) và câu chốt `story_moral`
sau khi kịch bản từ `prompt_architect_node` đã qua kiểm tra cấu trúc.

Đồng bộ 100% với chuẩn JSON 7–9 cảnh của `architect_prompt.py` và `scorer_prompt.py`.
Render bằng `render_outro_moral_prompt(...)` (thay token, không dùng str.format).
"""

OUTRO_MORAL_PROMPT_TEMPLATE = """Bạn là **Biên tập viên Lồng tiếng TTS Tiếng Việt** cho kênh phim tài liệu ngắn 9:16 (phong cách Vox / Johnny Harris / Thư Viện Lịch Sử).
Nhiệm vụ: chuốt lại toàn bộ lời bình `narration_vn` của từng cảnh và câu chốt `story_moral` để giọng đọc AI mượt mà, đúng nhịp tai nghe nhưng KHÔNG làm đổi nghĩa hay số lượng cảnh (để hình ảnh vẫn khớp 100% lời).

Chủ đề: "{topic_title}"   |   Thể loại: {genre}

### LỜI BÌNH HIỆN TẠI THEO TỪNG CẢNH:
{scenes_narration_block}

### CÂU CHỐT & CAPTION HIỆN TẠI:
"{story_moral}"

═══ QUY TẮC TINH CHỈNH (BẮT BUỘC) ═══
1. **Giữ nguyên số cảnh & nội dung cốt lõi**: Có bao nhiêu cảnh đầu vào phải trả về ĐÚNG bấy nhiêu cảnh, giữ nguyên vật thể/hành động chính để khớp với `image_prompt_en`.
2. **Tối ưu tai nghe TTS Tiếng Việt**:
   - Tổng lời bình toàn phim giữ trong **140–190 từ**.
   - Cảnh 1 (Hook): **≤ 14 từ**, sắc, đánh thẳng vào nhận thức, không mở đầu sáo rỗng ("Bạn có biết", "Hôm nay", "Trong video này"...).
   - Các cảnh còn lại: **8–24 từ/cảnh**, nhịp ngắn – ngắn – dài – ngắn, dùng dấu phẩy/chấm để ngắt hơi tự nhiên.
3. **Sạch ký tự cấm TTS**:
   - ⛔ KHÔNG chữ số (0–9), KHÔNG ký hiệu (%, $, /, +, =), KHÔNG viết tắt (TP.HCM, VD, km/h). Đổi toàn bộ thành chữ tiếng Việt.
   - ⛔ KHÔNG tiếng Anh xen kẽ; tên riêng nước ngoài phiên âm tiếng Việt dễ đọc.
   - ⛔ KHÔNG sáo ngữ ("hành trình", "hạt mầm", "ánh sáng cuối đường hầm", "bài học đắt giá", "mỗi chúng ta").
4. **Chuốt `story_moral`**: 1 câu chốt callback sắc (không rao giảng) + caption đăng bài + 3–5 hashtag tiếng Việt.

═══ ĐỊNH DẠNG ĐẦU RA — CHỈ MỘT JSON OBJECT HỢP LỆ, KHÔNG MARKDOWN ═══
{
  "refined_narrations": [
    {
      "scene_index": 1,
      "narration_vn": "..."
    }
  ],
  "story_moral": "1 câu chốt + caption đăng bài + 3–5 hashtag tiếng Việt"
}"""


_TOKENS = ("topic_title", "genre", "scenes_narration_block", "story_moral")


def render_outro_moral_prompt(
    topic_title: str,
    genre: str,
    scenes_narration_block: str,
    story_moral: str = "",
) -> str:
    """Render prompt tinh chỉnh voiceover TTS theo token thay thế an toàn."""
    values = {
        "topic_title": topic_title,
        "genre": genre,
        "scenes_narration_block": scenes_narration_block,
        "story_moral": story_moral or "Chưa có.",
    }
    out = OUTRO_MORAL_PROMPT_TEMPLATE
    for k in _TOKENS:
        out = out.replace("{" + k + "}", str(values[k]))
    return out
