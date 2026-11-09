"""
Prompt Template cho Node `prompt_scorer_node`:
Chấm điểm khắt khe Kịch bản, Hồ sơ Nhân vật (Character Bible), Bối cảnh 3D và Storyboard 4 Phân cảnh của LLM.
"""

PROMPT_SCORER_TEMPLATE = """Bạn là Giám khảo Kiểm định Chất lượng Phim Hoạt hình 3D & Kịch bản Short Video (Senior Script & Visual QA Critic).
Hãy chấm điểm bản thiết kế kịch bản và phân cảnh hoạt hình 3D vừa được tạo cho chủ đề: "{user_request}".

### DỮ LIỆU ĐỐI CHIẾU:
- Chủ đề gốc: "{user_request}"
- Tiêu đề kịch bản: "{topic_title}"
- Thực thể chuyển động 3D Tiền cảnh (`visual_archetype`): "{visual_archetype}"
- 4 Phân cảnh Storyboard (`visual_labels`): {visual_labels}
- Prompt vẽ 4 Phân cảnh 2x2 Grid (`scene_action_prompt`): "{scene_action_prompt}"
- Lời bình 3 phần:
  1. Mở đầu (Hook): "{hook_and_context_vn}"
  2. Giải thích sâu: "{deep_explanation_vn}"
  3. Đúc kết cuối: "{outro_takeaway_vn}"

### TIÊU CHÍ CHẤM ĐIỂM KHẮT KHE (Thang 1.0 - 10.0):
1. **rag_faithfulness_score (Độ sâu sắc, logic suy luận & bám sát chủ đề - Trọng số 40%):**
   - Lời bình 3 phần có giải thích sâu sắc, giàu hình tượng ẩn dụ và đúng trọng tâm chủ đề "{user_request}" không?
2. **cinematic_quality_score (Chất lượng Storyboard 4 cảnh, Nhân vật & Chuyển động 3D - Trọng số 30%):**
   - `scene_action_prompt` đã mô tả rõ 4 khung cảnh 2x2 Grid (`Top-Left`, `Top-Right`, `Bottom-Left`, `Bottom-Right`) có nhân vật chính, bối cảnh 3D và hành động biến đổi rõ rệt qua từng cảnh chưa? (Trừ điểm nặng nếu chỉ mô tả 1 cảnh tĩnh hoặc biểu đồ toán học).
3. **theological_moral_score (Sức hút Hook 3 giây đầu & Thông điệp đọng lại - Trọng số 30%):**
   - Câu mở đầu có giữ chân người xem ngay lập tức và câu kết có truyền cảm hứng mạnh mẽ không?

### ĐỊNH DẠNG ĐẦU RA (JSON SCHEMA):
{{
  "rag_faithfulness_score": <float>,
  "cinematic_quality_score": <float>,
  "theological_moral_score": <float>,
  "average_score": <float>,
  "pass_validation": <boolean (True nếu average_score >= 8.0 và cinematic_quality_score >= 8.0)>,
  "feedback_for_rewrite": "Nếu pass_validation = False, chỉ rõ cần bổ sung nhân vật, bối cảnh 4 ô 2x2 hay sửa lời bình chỗ nào. Nếu True, để chuỗi rỗng."
}}"""
