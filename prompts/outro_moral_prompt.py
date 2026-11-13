"""
Prompt dự phòng để tinh chỉnh lời đọc Voiceover (TTS Tiếng Việt) và câu chốt `story_moral`
sau khi kịch bản từ `prompt_architect_node` đã qua kiểm tra cấu trúc.

Đồng bộ 100% với chuẩn JSON 8–10 cảnh của `architect_prompt.py` và `scorer_prompt.py`.
Render bằng `render_outro_moral_prompt(...)` (thay token, không dùng str.format).
"""

from .narrative_models import NARRATIVE_MODELS, select_domain_expert

OUTRO_MORAL_PROMPT_TEMPLATE = """[ROLE]: {domain_expert_role} — kiêm Biên tập viên Lồng tiếng TTS Tiếng Việt
[DOMAIN_LENS]: {domain_expert_lens}
[PURPOSE]: Chuốt lại lời bình `narration_vn` (cho TTS đọc) và `subtitle_vn` (cho mắt đọc) của từng cảnh cùng câu chốt `story_moral` nhưng KHÔNG làm đổi nghĩa hay số lượng cảnh (để hình ảnh vẫn khớp 100% lời).
[STYLE]: Vox / Johnny Harris / Thư Viện Lịch Sử — nhịp câu biến thiên (Staccato Hook, Twist ngắn gắt, Sonic Echo lúc kết), giàu động từ giác quan, sạch ký tự cấm TTS
[PLATFORM]: Video dọc 9:16 (TikTok, Facebook/Instagram Reels, YouTube Shorts) — 45–60 giây (8–10 cảnh, 130–185 từ)
[AUDIENCE]: Người lớn 18–45 tuổi, nghe nhanh trên di động, bỏ xem ngay nếu lời đọc đều giọng, sáo rỗng hoặc TTS đọc vấp

[TASK]: Tinh chỉnh lời bình từng cảnh và câu chốt `story_moral` theo đúng kiểu chốt của mô hình `{narrative_model_id}`, giữ nguyên số lượng cảnh và xuất đúng một JSON object hợp lệ.
- Chủ đề: "{topic_title}"   |   Thể loại: {genre}   |   Mô hình: `{narrative_model_id}`
- Kiểu chốt bắt buộc của mô hình `{narrative_model_id}`: {outro_style}

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
    "domain_expert_role",
    "domain_expert_lens",
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
    domain_expert: str = "auto",
) -> str:
    """Render prompt tinh chỉnh voiceover TTS theo token thay thế an toàn."""
    model_key = (narrative_model or "abt").strip().lower()
    model = NARRATIVE_MODELS.get(model_key) or NARRATIVE_MODELS["abt"]
    expert = select_domain_expert(
        topic_title,
        source_context=scenes_narration_block,
        genre_hint=genre,
        narrative_model=model_key,
        preferred_expert=domain_expert,
    )
    values = {
        "domain_expert_role": expert["expert_role"],
        "domain_expert_lens": expert["expert_lens"],
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
