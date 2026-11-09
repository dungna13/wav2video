"""
Prompt dự phòng để tinh chỉnh lời đọc Voiceover nếu cần.
"""

OUTRO_MORAL_PROMPT_TEMPLATE = """Bạn là Biên tập viên Lồng tiếng cho kênh giải thích khoa học & triết học Median Lab.
Hãy chuốt lại lời đọc 3 phần cho chủ đề "{scripture_reference}" để giọng đọc mượt mà, tự nhiên nhất.

### ĐẦU VÀO:
- Nội dung: "{retrieved_scripture}"
- Prompt hình ảnh: "{scene_action_prompt}"
- Thông điệp: "{story_moral}"

### ĐẦU RA (JSON SCHEMA):
{{
  "scene_narration_vn": "Lời bình Phần 1 mở đầu hấp dẫn (30-45 từ).",
  "outro_reflection_vn": "Lời bình Phần 2 phân tích sâu sắc (35-55 từ).",
  "closing_prayer_vn": "Lời bình Phần 3 kết luận đắt giá cuối video (20-35 từ)."
}}"""
