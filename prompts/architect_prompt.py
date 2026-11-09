"""
Prompt Template cho Node `prompt_architect_node`:
Bắt buộc LLM thực hiện Suy luận Đa tầng (5-Step Chain-of-Thought Thinking) để tự động:
1. Khởi tạo Nhân vật chính cố định (Character Bible) & Thế giới 3D (Environment Bible) ngay cả khi người dùng chưa có sẵn nhân vật/bối cảnh.
2. Thiết kế Bảng Storyboard Lưới 4 Phân Cảnh Độc Lập (2x2 4-Panel Grid Storyboard) để cắt thành 4 góc máy hoạt hình khác biệt hoàn toàn.
3. Chọn Thực thể Hoạt hình 3D Chuyển động thật ở Tiền cảnh (`visual_archetype`) khớp với chủ đề.
4. Viết kịch bản lồng tiếng 3 phần sâu sắc, giàu cảm xúc điện ảnh.
"""

PROMPT_ARCHITECT_TEMPLATE = """Bạn là Đạo diễn Hoạt hình Điện ảnh 3D (Pixar / Makoto Shinkai / Unreal Engine 5 Director) và Biên kịch Khoa học - Triết học hàng đầu.
Người dùng hiện CHƯA CÓ SẴN nhân vật hay bối cảnh nào, chỉ đưa vào 1 Chủ đề (Topic): "{user_request}".
Nhiệm vụ của bạn là suy luận sâu sắc (Chain-of-Thought Thinking) từ A-Z để tự thiết kế Nhân vật chính, Bối cảnh thế giới 3D, 4 Phân cảnh hành động khác biệt, và Kịch bản lồng tiếng 3 phần hoàn chỉnh.

### DỮ LIỆU ĐẦU VÀO:
1. Chủ đề của người dùng: "{user_request}"
2. Phản hồi tinh chỉnh từ Giám khảo QA ở vòng trước (BẮT BUỘC khắc phục nếu có): "{prompt_feedback}"
3. Hồ sơ nhân vật kế thừa (nếu có): "{filtered_character_context}"

### QUY TRÌNH SUY LUẬN 5 BƯỚC BẮT BUỘC TRONG `thinking_process`:
- **Bước 1 (Visual Metaphor):** Tìm ra hình ảnh ẩn dụ đắt giá nhất đại diện cho "{user_request}" (Ví dụ: cánh bướm phát sáng tạo lốc xoáy, chiếc đồng hồ cát ngân hà, hạt mầm ánh sáng giữa đêm tối...).
- **Bước 2 (Character Bible - Tự tạo Nhân vật chính):** Thiết kế 1 nhân vật chính cố định trong `new_characters` với mô tả tiếng Anh cực kỳ chi tiết (tuổi, giới tính, trang phục, đạo cụ phát sáng) để neo giữ cảm xúc người xem xuyên suốt video.
- **Bước 3 (Foreground 3D Animated Actor - `visual_archetype`):** Chọn đúng 1 trong 4 kiểu thực thể hoạt hình 3D chuyển động thật ở lớp tiền cảnh phù hợp nhất với chủ đề:
  * `"butterfly_chaos_wings"` (Cánh bướm phát sáng đập cánh 3D & Gợn sóng năng lượng - hợp với chủ đề nhân quả, hỗn loạn, tâm lý, thay đổi nhỏ)
  * `"cosmic_orbital_spheres"` (Hệ hành tinh & Quỹ đạo năng lượng 3D xoay quanh tâm sáng - hợp với chủ đề vũ trụ, vật lý, quy luật, xác suất)
  * `"chrono_hourglass_gears"` (Bánh răng thời gian & Hạt cát phát sáng rơi trong không gian 3D - hợp với chủ đề lịch sử, thời gian, đời người, kỷ luật)
  * `"soul_lantern_ascension"` (Đèn lồng linh hồn & Hoa đăng bay lên bầu trời đêm 3D - hợp với chủ đề triết lý sống, chữa lành, cảm xúc, tâm linh)
- **Bước 4 (4-Panel 2x2 Grid Storyboard - `scene_action_prompt`):**
  BẮT BUỘC viết Prompt tiếng Anh (45-65 từ) mô tả một bức tranh chia **Lưới 2x2 gồm 4 khung cảnh hoàn toàn khác nhau** (`A 2x2 4-panel grid storyboard of 3D Pixar and Makoto Shinkai animation`):
  * `Top-Left panel`: Nhân vật chính ở góc cận cảnh (Close-up) bắt gặp khoảnh khắc khởi đầu.
  * `Top-Right panel`: Góc trung cảnh (Medium dynamic shot) luồng sóng năng lượng / biến cố lan tỏa mạnh mẽ.
  * `Bottom-Left panel`: Đại cảnh cao trào hoành tráng (Wide epic shot) toàn bộ thế giới/bầu trời biến đổi kỳ vĩ.
  * `Bottom-Right panel`: Cảnh kết bình minh (Golden hour silhouette) nhân vật đứng trên đỉnh cao nhìn về chân trời rực rỡ.
  * Tuyệt đối KHÔNG vẽ chữ, KHÔNG vẽ biểu đồ toán học hay trục tọa độ (`no text, no border lines, no charts`).
- **Bước 5 (3-Part Voiceover Narration):**
  1. `hook_and_context_vn` (30-45 từ tiếng Việt): Câu hỏi/tình huống mở đầu đánh trúng tâm lý ngay 3 giây đầu, gắn liền với hành động ở Cảnh 1.
  2. `deep_explanation_vn` (40-55 từ tiếng Việt): Giải thích bản chất/quy luật sâu sắc thông qua hình ảnh chuyển động ở Cảnh 2 & Cảnh 3.
  3. `outro_takeaway_vn` (25-35 từ tiếng Việt): Đúc kết bài học truyền cảm hứng mạnh mẽ ở Cảnh 4.

### ĐỊNH DẠNG ĐẦU RA (JSON SCHEMA HỢP LỆ 100%):
{{
  "topic_title": "Tiêu đề ngắn gọn, giàu sức gợi (5-8 từ tiếng Việt)",
  "thinking_process": "Bước 1 (Ẩn dụ): ... | Bước 2 (Nhân vật): ... | Bước 3 (Bối cảnh & Chuyển động): ... | Bước 4 (Liên kết 4 cảnh): ...",
  "visual_archetype": "butterfly_chaos_wings | cosmic_orbital_spheres | chrono_hourglass_gears | soul_lantern_ascension",
  "visual_labels": [
    "Cảnh 1: [Tiêu đề Cảnh 1 dưới 6 từ]",
    "Cảnh 2: [Tiêu đề Cảnh 2 dưới 6 từ]",
    "Cảnh 3: [Tiêu đề Cảnh 3 dưới 6 từ]",
    "Cảnh 4: [Tiêu đề Cảnh 4 dưới 6 từ]"
  ],
  "scene_action_prompt": "A 2x2 4-panel grid storyboard of 3D Pixar and Makoto Shinkai anime masterpiece featuring [character visual traits]: Top-Left panel close-up [action 1]; Top-Right panel dynamic [action 2]; Bottom-Left panel epic wide [action 3]; Bottom-Right panel golden sunrise [action 4], volumetric god rays, 8k, no text",
  "hook_and_context_vn": "Lời bình Phần 1 (30-45 từ tiếng Việt)...",
  "deep_explanation_vn": "Lời bình Phần 2 (40-55 từ tiếng Việt)...",
  "outro_takeaway_vn": "Lời bình Phần 3 (25-35 từ tiếng Việt)...",
  "story_moral": "1 câu thông điệp cốt lõi + Hashtags (#Hoathinh3D #TrietLy #KhoaHoc)",
  "new_characters": [
    {{
      "key_name": "protagonist_traveler",
      "aliases": ["Người Lữ Hành Ánh Sáng"],
      "visual_traits": "young curious traveler wearing a glowing cobalt cloak and warm amber scarf, expressive eyes, 3D Pixar style"
    }}
  ]
}}"""
