"""
Prompt dự phòng để tinh chỉnh lời đọc Voiceover (TTS Tiếng Việt) và câu chốt `story_moral`
sau khi kịch bản từ `prompt_architect_node` đã qua kiểm tra cấu trúc.

Đồng bộ 100% với chuẩn JSON 8–10 cảnh của `architect_prompt.py` và `scorer_prompt.py`.
Render bằng `render_outro_moral_prompt(...)` (thay token, không dùng str.format).
"""

from .narrative_models import NARRATIVE_MODELS

OUTRO_MORAL_PROMPT_TEMPLATE = """Bạn là **Biên tập viên Lồng tiếng TTS Tiếng Việt** cho kênh phim tài liệu ngắn 9:16 (phong cách Vox / Johnny Harris / Thư Viện Lịch Sử).
Nhiệm vụ: chuốt lại lời bình `narration_vn` (cho TTS đọc) và `subtitle_vn` (cho mắt đọc) của từng cảnh cùng câu chốt `story_moral` nhưng KHÔNG làm đổi nghĩa hay số lượng cảnh (để hình ảnh vẫn khớp 100% lời).

Chủ đề: "{topic_title}"   |   Thể loại: {genre}   |   Mô hình: `{narrative_model_id}`
Kiểu chốt bắt buộc của mô hình `{narrative_model_id}`: {outro_style}

### LỜI BÌNH HIỆN TẠI THEO TỪNG CẢNH:
{scenes_narration_block}

### CÂU CHỐT & CAPTION HIỆN TẠI:
"{story_moral}"

═══ QUY TẮC TINH CHỈNH (BẮT BUỘC) ═══
1. **Giữ nguyên số cảnh & nội dung cốt lõi**: Có bao nhiêu cảnh đầu vào phải trả về ĐÚNG bấy nhiêu cảnh, giữ nguyên vật thể/hành động chính để khớp với `image_prompt_en`.
2. **Biến thiên nhịp câu TTS (`narration_vn`)**:
   - Tổng `narration_vn` toàn phim giữ trong **130–185 từ** (8–10 cảnh).
   - Cảnh 1 (Hook): **6–11 từ**, sắc, không mở đầu sáo rỗng ("Bạn có biết", "Hôm nay", "Trong video này"...).
   - Có **1–2 cảnh Twist ngắn gắt (7–12 từ)** và **Cảnh cuối (Kết) 10–14 từ** chốt dứt khoát đúng kiểu của `{narrative_model_id}`; các cảnh giải thích giữ **13–20 từ/cảnh**, dùng dấu phẩy/chấm để ngắt hơi TTS.
3. **Sạch ký tự cấm TTS trong `narration_vn` & Gọn cho `subtitle_vn`**:
   - `narration_vn`: ⛔ KHÔNG chữ số (0–9), KHÔNG ký hiệu (%, $, /, +, =), KHÔNG viết tắt (TP.HCM, VD, km/h), KHÔNG tiếng Anh xen kẽ, KHÔNG sáo ngữ. Tên riêng phiên âm tự nhiên dễ đọc.
   - `subtitle_vn`: cùng nghĩa với `narration_vn`, rút gọn tự nhiên và ĐƯỢC dùng số/ký hiệu (`thế kỷ 9`, `400 năm`, `20%`).
4. **Chuốt `story_moral` theo `{narrative_model_id}`**: Giữ đúng kiểu chốt của mô hình ({outro_style}) — ví dụ Callback cho ABT/Myth, Payoff cho Hook-Retain-Payoff, CTA cụ thể cho PAS/BAB/AIDA... — gồm 1 câu chốt sắc gọn + caption đăng bài + 3–5 hashtag tiếng Việt.

═══ ĐỊNH DẠNG ĐẦU RA — CHỈ MỘT JSON OBJECT HỢP LỆ, KHÔNG MARKDOWN ═══
{
  "refined_narrations": [
    {
      "scene_index": 1,
      "narration_vn": "...",
      "subtitle_vn": "..."
    }
  ],
  "story_moral": "1 câu chốt + caption đăng bài + 3–5 hashtag tiếng Việt"
}"""


_TOKENS = (
    "narrative_model_id",
    "outro_style",
    "topic_title",
    "genre",
    "scenes_narration_block",
    "story_moral",
)


def render_outro_moral_prompt(
    topic_title: str,
    genre: str,
    scenes_narration_block: str,
    story_moral: str = "",
    narrative_model: str = "abt",
) -> str:
    """Render prompt tinh chỉnh voiceover TTS theo token thay thế an toàn."""
    model_key = (narrative_model or "abt").strip().lower()
    model = NARRATIVE_MODELS.get(model_key) or NARRATIVE_MODELS["abt"]
    values = {
        "narrative_model_id": model["id"],
        "outro_style": model["outro_style"],
        "topic_title": topic_title,
        "genre": genre,
        "scenes_narration_block": scenes_narration_block,
        "story_moral": story_moral or "Chưa có.",
    }
    out = OUTRO_MORAL_PROMPT_TEMPLATE
    for k in _TOKENS:
        out = out.replace("{" + k + "}", str(values[k]))
    return out
