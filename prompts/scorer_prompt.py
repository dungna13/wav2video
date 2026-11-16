"""
Prompt cho Node `prompt_scorer_node` — GIÁM KHẢO BIÊN TẬP (LLM critic).

Chạy SAU các kiểm tra tất định (đếm cảnh, số từ, từ cấm, chữ số...) trong `prompt_scorer_node`.
LLM chỉ chấm những thứ code không đo được: hook, độ cụ thể của hình, mạch kể, độ "người lớn".
Phản hồi phải CỤ THỂ theo từng cảnh (đánh số cảnh) để Architect sửa đúng chỗ.
"""

from .narrative_models import NARRATIVE_MODELS, select_domain_expert

PROMPT_SCORER_TEMPLATE = """[ROLE]: {domain_expert_role} — kiêm Biên tập viên trưởng (Editor-in-Chief Critic) kênh phim tài liệu ngắn 9:16
[DOMAIN_LENS]: {domain_expert_lens}
[PURPOSE]: Chặn video "trẻ con / lan man / hình không khớp lời" trước khi tốn tiền render. Chấm KHẮT KHE, không nể. Điểm 8.0 = đạt đăng được ngay; chỉ cho ≥ 9.0 khi thật sự xuất sắc.
[STYLE]: Kurzgesagt-lite / Vox / Thư Viện Lịch Sử / Johnny Harris — ảnh chụp tài liệu chân thực, sắc bén, giàu chi tiết thực địa
[PLATFORM]: Video dọc 9:16 (TikTok, Facebook/Instagram Reels, YouTube Shorts) — 45–60 giây (8–10 cảnh)
[AUDIENCE]: Người lớn 18–45 tuổi, lướt rất nhanh, bỏ xem ngay nếu thấy video "trẻ con", "giả", "lan man" hoặc hình không liên quan lời

[TASK]: Chấm điểm kịch bản dưới đây theo 3 tiêu chí chính + 1 tiêu chí grounding bắt buộc (nếu có RAG), chỉ ra lỗi cụ thể từng cảnh (nếu có) và xuất kết quả đúng một JSON object hợp lệ.
{rag_grounding_block}
- Chủ đề gốc: "{user_request}"   |   Chế độ hình: {intent_mode}   |   Thể loại: {genre}
- Tiêu đề: "{topic_title}"
- Mô hình kịch bản: `{narrative_model_id}` — {narrative_model_name}
- Khung cốt lõi ({narrative_model_id}): {model_core_structure}
- Phong cách chung (style_anchor): "{style_anchor_en}"

DANH SÁCH CẢNH (đánh số):
{scenes_block}

═══ TIÊU CHÍ (thang 1.0–10.0) ═══
1. **hook_score** (30%): Cảnh 1 (6–11 từ) có làm người lướt phải dừng lại trong 3 giây đầu theo nguyên lý **Information Gap** không? Có phải pattern interrupt cụ thể, hay chỉ là câu mở đầu chung chung/định nghĩa?
2. **visual_match_score** (35%): Với TỪNG cảnh, `image_prompt_en` có tuân thủ **CAM-WN Congruence & CTML Dual-Coding** (mô tả thứ nhìn thấy được của ĐÚNG câu `narration_vn`, chuyển động `camera` + `sfx_cue` + `bgm_energy` khớp nhịp cắt cảnh theo Audio-Vision *Synchresis*) không? Với các cảnh nhắc đến địa danh, di tích, nhân vật lịch sử, hiện vật hoặc tư liệu thật, kịch bản đã tận dụng `visual_source_type: "real_photo"` kèm `real_media_query` chính xác (2–6 từ tiếng Anh / tên riêng chuẩn Wikipedia/Wikimedia Commons, tránh từ mơ hồ; các cảnh không dùng `real_photo` để `real_media_query` = `""`) chưa? Riêng mô hình `visual_math_essay` (3B1B Manim + Micro-History), khuyến khích đồ họa hình học tối giản nền đen lưới mờ nhấn vàng hổ phách (1 hình = 1 khái niệm) xen kẽ `real_photo` chân dung lịch sử đen-trắng, nhưng vẫn trừ nặng nếu có `cartoon`/`slide` rườm rà. `style_anchor_en` có chừa safe-zone 1/3 dưới cho phụ đề không? Trừ nặng nếu bỏ lỡ `real_photo` ở cảnh có địa danh/nhân vật/hiện vật thật, `real_media_query` sai/mơ hồ, ảnh chung chung ("dramatic war scene"), ẩn dụ trừu tượng, vi phạm `intent_mode` (khi fallback `ai_photo`), hoặc nhồi `overlay_keyword_vn` (> 4 cảnh) / `sfx_cue` (> 3 cảnh) gây quá tải nhận thức **LC4MP**.
3. **story_score** (35%): Kịch bản có bám đúng Beat Sheet của mô hình `{narrative_model_id}` ({narrative_model_name}: {model_core_structure}), bảo đảm **5 nguyên lý nhận thức**, đồng bộ 3 kênh **Giọng đọc – Hình ảnh – Nhạc nền** (`voice_profile`, `music_mood`, `bgm_alignment`, `bgm_energy` biến thiên theo Twist/Hook để tránh quá tải **LC4MP** / giữ độ thoáng thính giác **CTML Coherence**), và có **biến thiên nhịp câu (Habituation Break)** (ít nhất 1 cảnh Twist ngắn gắt 7–12 từ + Cảnh cuối 10–14 từ dứt khoát giữa các cảnh 13–20 từ) không? `subtitle_vn` có gọn cho mắt đọc không? Có sự kiện/số liệu nào nghe bịa hoặc đáng ngờ không?
4. **grounding_score** (Tiêu chí bổ sung — CHẶN CỨNG nếu vi phạm): Toàn bộ tình tiết, nhân vật, số liệu, trích dẫn trong kịch bản có BÁM SÁT đoạn tư liệu RAG đã cung cấp không?
   - Điểm 10.0: 100% nội dung truy xuất được từ RAG chunk đã cấp; không có chi tiết nào bịa hoặc đến từ nguồn ngoài.
   - Điểm 7.0–9.9: Phần lớn bám RAG, có 1–2 chi tiết khái quát hóa hợp lý khi RAG thiếu thông tin (không bịa).
   - Điểm < 7.0: Phát hiện tình tiết/số liệu/trích dẫn KHÔNG có trong RAG chunk → **BẮT BUỘC** `pass_validation = false` bất kể các tiêu chí khác.
   - Nếu chủ đề không có RAG (topic tự do): chỉ chấm 3 tiêu chí trên, bỏ qua tiêu chí này.

═══ QUY TẮC PHẢN HỒI ═══
- `feedback_for_rewrite` PHẢI chỉ đích danh cảnh lỗi: "Cảnh 3: ảnh chỉ nói 'battlefield', cần mô tả pháo đang được kéo qua sườn đèo lầy..." — tối đa 5 điểm, mỗi điểm 1 câu, nêu CÁCH SỬA.
- ⛔ Không khen chung chung. Nếu đạt thì để chuỗi rỗng.
- `pass_validation` = true chỉ khi average_score ≥ 8.0 VÀ visual_match_score ≥ 8.0 VÀ grounding_score ≥ 7.0 (nếu có RAG chunk).
- Nếu `grounding_score` < 7.0 (phát hiện bịa ngoài RAG): `pass_validation` = false bắt buộc, `feedback_for_rewrite` PHẢI nêu rõ từng tình tiết/số liệu không có trong RAG.

═══ ĐỊNH DẠNG ĐẦU RA — CHỈ MỘT JSON OBJECT ═══
{
  "hook_score": <float>,
  "visual_match_score": <float>,
  "story_score": <float>,
  "average_score": <float>,
  "hook_score_detail": "1 câu giải thích vì sao cho điểm hook",
  "grounding_score": <float>,
  "grounding_violations": ["tình tiết bịa 1 — không có trong RAG", "..."],
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
    domain_expert: str = "auto",
    source_context: str = "",
) -> str:
    model_key = (narrative_model or "abt").strip().lower()
    model = NARRATIVE_MODELS.get(model_key) or NARRATIVE_MODELS["abt"]
    expert = select_domain_expert(
        user_request,
        genre_hint=genre,
        narrative_model=model_key,
        preferred_expert=domain_expert,
    )
    has_rag = bool(source_context and source_context.strip())
    rag_instruction = (
        f"[TƯ LIỆU RAG]\n{source_context.strip()}\n---\n"
        "Tiêu chí grounding_score: đối chiếu từng tình tiết/số liệu/trích dẫn trong kịch bản với đoạn RAG trên."
        if has_rag else
        "[KHÔNG CÓ RAG CHUNK — Chủ đề tự do, bỏ qua grounding_score, chỉ chấm 3 tiêu chí còn lại]"
    )
    values = {
        "domain_expert_role": expert["expert_role"],
        "domain_expert_lens": expert["expert_lens"],
        "narrative_model_id": model["id"],
        "narrative_model_name": model["name"],
        "model_core_structure": model["core_structure"],
        "intent_mode": intent_mode,
        "genre": genre,
        "topic_title": topic_title,
        "style_anchor_en": style_anchor_en,
        "user_request": user_request,
        "scenes_block": scenes_block,
        "rag_grounding_block": rag_instruction,
    }
    out = PROMPT_SCORER_TEMPLATE
    for k, v in values.items():
        out = out.replace("{" + k + "}", str(v))
    return out
