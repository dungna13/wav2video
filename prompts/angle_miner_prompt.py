"""
Prompt cho Node `angle_miner_node` — KHAI THÁC GÓC KỂ TỪ TƯ LIỆU SÁCH / RAG CHUNK.

Chạy TRƯỚC `prompt_architect_node` khi đầu vào là một chương sách, báo cáo dài, hoặc RAG chunk.
Mục tiêu: tách một đoạn tư liệu thành 3–5 góc kể phim tài liệu ngắn 9:16 độc lập,
không trùng lặp và bám sát sự thật trong `source_chunk` (không bịa ngoài văn bản).

Render bằng `render_angle_miner_prompt(...)` (thay token, không dùng str.format).
"""

from .narrative_models import (
    DOMAIN_EXPERTS,
    format_models_catalog_for_prompt,
    select_domain_expert,
)

PROMPT_ANGLE_MINER_TEMPLATE = """[ROLE]: {domain_expert_role} — kiêm Trưởng ban Biên tập Phim Tài liệu Ngắn 9:16
[DOMAIN_LENS]: {domain_expert_lens}
[PURPOSE]: Thu hút người xem dừng lướt ngay trong 3 giây đầu (bằng nghịch lý, cơ chế ẩn hoặc cái giá đắt nhất) và giữ chân khán giả đến giây cuối thông qua góc kể sắc nét, không tóm tắt lan man
[STYLE]: Vox / Johnny Harris / Thư Viện Lịch Sử — sắc lạnh, giàu chi tiết thực địa, phá vỡ định kiến quen thuộc
[PLATFORM]: Video ngắn dọc 9:16 (TikTok, Facebook/Instagram Reels, YouTube Shorts)
[AUDIENCE]: Người lớn 18–45 tuổi, lướt rất nhanh, bỏ qua ngay nội dung chung chung, trẻ con hoặc tóm tắt sách giáo khoa

[TASK]: Đọc đoạn tư liệu gốc dưới đây và khai thác **{num_angles} góc kể (angles) độc lập** để sản xuất {num_angles} clip ngắn khác nhau — TUYỆT ĐỐI KHÔNG tóm tắt dàn trải cả chương sách.
- Tên tác phẩm / nguồn: "{book_title}"
- Các chủ đề đã làm trước đó (TRÁNH TRÙNG): "{existing_topics}"

═══ TƯ LIỆU NGUỒN (RAG CHUNK) ═══
{source_chunk}

═══ NGUYÊN TẮC KHAI THÁC GÓC KỂ (BẮT BUỘC) ═══
1. **Mỗi góc = 1 nghịch lý / cơ chế ẩn / cái giá đắt nhất**:
   - Tìm chi tiết khiến người lớn 18–45 tuổi phải khựng lại vì phá vỡ định kiến quen thuộc.
   - ⛔ Cấm góc chung chung kiểu "Tóm tắt bài học của chương...", "Giới thiệu về...".
2. **Độ phủ không trùng lặp**:
   - Mỗi góc phải khai thác một nhân vật, sự kiện, cơ chế hoặc mâu thuẫn KHÁC NHAU trong đoạn tư liệu và không trùng với `{existing_topics}`.
3. **Kỷ luật bám sát nguồn**:
   - Chỉ chọn góc có đủ dữ kiện cụ thể nằm ngay trong đoạn tư liệu; trích nguyên văn câu/chi tiết neo vào `key_evidence_quote`.
4. **Sẵn sàng nạp cho `prompt_architect_node`**:
   - Mỗi góc phải sinh sẵn `user_request_for_architect` (1 câu đề bài sắc nét), `hook_idea_vn` (6–11 từ, pattern interrupt), `recommended_genre`, `recommended_intent_mode`, `recommended_narrative_model` (1 trong 12 ID ở danh mục bên dưới), `model_selection_reason` (1 câu ngắn giải thích vì sao mô hình đó hợp nhất với góc kể này), `recommended_domain_expert` (1 trong 14 ID chuyên gia ở danh mục bên dưới), cấu hình giọng đọc (`recommended_voice_profile`, `recommended_tts_voice`, `voice_selection_reason`) và cấu hình nhạc nền (`recommended_bgm_profile`, `bgm_affect_quadrant`, `bgm_alignment_mode`, `bgm_selection_reason`).
5. **Lựa chọn giọng đọc phù hợp với nội dung (Bắt buộc đồng nhất 1 giọng/clip)**:
   - Căn cứ thể loại (`recommended_genre`), sắc thái cảm xúc của góc kể và nhịp của mô hình kịch bản (`recommended_narrative_model`), chọn **01 profile giọng đọc tối ưu nhất** từ danh mục bên dưới và giữ **đồng nhất 1 giọng duy nhất** xuyên suốt toàn bộ các cảnh trong clip (tuyệt đối không đổi giọng giữa chừng).
6. **Lựa chọn nhạc nền (BGM) theo 5 mô hình lý thuyết**:
   - **Russell Circumplex:** Chốt tọa độ cảm xúc `Valence` (tích cực/tiêu cực) × `Arousal` (tĩnh/kịch tính) vào `bgm_affect_quadrant`.
   - **Chion (Empathetic vs. Anempathetic):** Mặc định dùng `empathetic` (đồng điệu tâm trạng cảnh); chỉ dùng `anempathetic` (nhạc tươi/thản nhiên trên nền bi kịch) khi góc kể chủ đích tạo tương phản mỉa mai hoặc rợn ngợp.
   - **CAM-WN & BRECVEMA:** Chọn nhịp BPM khớp tốc độ cắt cảnh (`Rhythmic Entrainment`) và có khoảng nghỉ/build-up tại điểm Twist (`Musical Expectancy`).
   - **Berlyne’s Inverted-U (Chống quá tải nhận thức):** **BẮT BUỘC nhạc không lời (instrumental)**, kết cấu vừa phải — tránh quá đều (nhàm chán) hoặc quá dày/ồn (át giọng TTS dù đã Audio Ducking).

═══ DANH MỤC 13 MÔ HÌNH KỊCH BẢN (CHỌN 1 ID TỐI ƯU CHO MỖI GÓC) ═══
{models_catalog}

═══ DANH MỤC 14 CHUYÊN GIA LĨNH VỰC (CHỌN 1 ID CHO `recommended_domain_expert` MỖI GÓC) ═══
{domain_experts_catalog}

═══ DANH MỤC GIỌNG ĐỌC TIKTOK / TTS TIẾNG VIỆT (CHỌN 1 PROFILE CHO MỖI GÓC) ═══
- `nam_tram_am` | TTS: `vi-VN-NamMinhNeural` (tông nam trầm ấm, đĩnh đạc, nhịp vừa) → Hợp: `history_war`, `history_culture`, `science_nature`, `economics_business`, `true_story_crime`; mô hình giải mã/đối chứng chiều sâu (`myth_vs_reality`, `scqa`, `abt`, `freytag_3_act`).
- `nu_hoat_ngon` | TTS: `vi-VN-HoaiMyNeural` (tông nữ tươi sáng, năng động, nhịp nhanh gọn) → Hợp: `tech_future`, `lifestyle_motivation`, mẹo thực hành, review/xu hướng mới; mô hình thuyết phục/bắt nhịp nhanh (`aida`, `pas`, `hook_retain_payoff`, `rule_of_three`).
- `nu_truyen_cam` | TTS: `vi-VN-HoaiMyNeural` (tông nữ ấm, tự sự, tiết chế nhịp vừa-chậm) → Hợp: `psychology_philosophy`, `lifestyle_motivation`, câu chuyện nhân sinh/cảm xúc (`pixar_story_spine`, `bab`, `in_medias_res`).
- `ai_hai_huoc` | TTS: `gtts_vi` (phong cách "Chị Google" đều giọng, gây cười/châm biếm) → Chỉ dùng cho góc meme, mỉa mai nhẹ, fact giải trí ngắn; **CẤM dùng** cho lịch sử bi tráng, điều tra tội phạm hoặc kiến thức cần độ tin cậy cao.

═══ DANH MỤC NHẠC NỀN (BGM) KHÔNG LỜI (CHỌN 1 PROFILE CHO MỖI GÓC) ═══
- `ambient_huyen_bi` | `low_valence_low_arousal` hoặc `high_arousal` nhẹ (synth trầm, drone, percussion nhỏ, 70–90 BPM) → Hợp: giải mã bí ẩn, khảo cổ, tội phạm, phá định kiến (`history_culture`, `science_nature`, `true_story_crime`, `myth_vs_reality`, `open_loops`).
- `cinematic_bi_trang` | `low_valence_high_arousal` (strings dồn dập, cello/brass, build-up rõ tại Twist, 95–125 BPM) → Hợp: chiến tranh, sụp đổ, kịch tính lịch sử, kinh tế khủng hoảng (`history_war`, `economics_business`, `freytag_3_act`, `in_medias_res`).
- `lo_fi_tu_su` | `high_valence_low_arousal` hoặc `low_valence_low_arousal` ấm (piano tối giản, acoustic/lo-fi nhẹ, 70–88 BPM) → Hợp: tâm lý học, triết lý, chữa lành, bài học nhân sinh (`psychology_philosophy`, `lifestyle_motivation`, `pixar_story_spine`, `bab`).
- `electronic_nang_dong` | `high_valence_high_arousal` (synthwave/corporate pulse gọn sắc, cắt nhịp nhanh, 110–130 BPM) → Hợp: công nghệ tương lai, kinh doanh tăng trưởng, mẹo/CTA nhanh (`tech_future`, `economics_business`, `aida`, `pas`, `hook_retain_payoff`, `rule_of_three`).
- `anempathetic_irony` | Tương phản Chion (giai điệu cổ điển/vui tươi nhẹ đặt trên nền sự kiện u tối/nghịch lý) → Chỉ dùng khi góc kể mang tính châm biếm lịch sử, nghịch lý xã hội sắc lạnh.

═══ ĐỊNH DẠNG ĐẦU RA — CHỈ MỘT JSON OBJECT HỢP LỆ, KHÔNG MARKDOWN ═══
{
  "book_title": "{book_title}",
  "angles": [
    {
      "angle_title": "Tiêu đề ngắn 4–8 từ",
      "user_request_for_architect": "Đề bài cụ thể 1 câu cho prompt_architect_node",
      "hook_idea_vn": "Câu mở đầu 6–11 từ, không chữ số/tiếng Anh",
      "recommended_genre": "history_war | history_culture | science_nature | economics_business | psychology_philosophy | true_story_crime | tech_future | lifestyle_motivation",
      "recommended_intent_mode": "NO_HUMAN_BROLL | HUMAN_NO_LIPSYNC",
      "recommended_narrative_model": "abt | in_medias_res | freytag_3_act | pixar_story_spine | scqa | visual_math_essay | hook_retain_payoff | myth_vs_reality | open_loops | rule_of_three | pas | bab | aida",
      "model_selection_reason": "1 câu giải thích vì sao mô hình kịch bản này tối ưu cho góc kể trên",
      "recommended_domain_expert": "military_historian | archaeologist_cultural_historian | macro_financial_analyst | b2b_strategy_architect | astrophysicist_science_communicator | biologist_earth_scientist | ai_cyber_architect | cognitive_psychologist | practical_philosopher | investigative_forensic_journalist | disaster_safety_engineer | behavioral_habit_coach | urban_travel_curator | general_documentary_researcher",
      "recommended_voice_profile": "nam_tram_am | nu_hoat_ngon | nu_truyen_cam | ai_hai_huoc",
      "recommended_tts_voice": "vi-VN-NamMinhNeural | vi-VN-HoaiMyNeural | gtts_vi",
      "voice_selection_reason": "1 câu giải thích vì sao chất giọng, giới tính và nhịp đọc này hợp với nội dung góc kể",
      "recommended_bgm_profile": "ambient_huyen_bi | cinematic_bi_trang | lo_fi_tu_su | electronic_nang_dong | anempathetic_irony",
      "bgm_affect_quadrant": "low_valence_high_arousal | low_valence_low_arousal | high_valence_high_arousal | high_valence_low_arousal",
      "bgm_alignment_mode": "empathetic | anempathetic",
      "bgm_selection_reason": "1 câu giải thích lựa chọn nhạc nền theo Valence/Arousal, nhịp cắt cảnh và độ thoáng giọng TTS",
      "key_evidence_quote": "Chi tiết/câu neo trích trực tiếp từ tư liệu nguồn"
    }
  ]
}"""


_TOKENS = (
    "book_title",
    "source_chunk",
    "num_angles",
    "existing_topics",
    "models_catalog",
    "domain_expert_role",
    "domain_expert_lens",
    "domain_experts_catalog",
)


def _format_domain_experts_catalog() -> str:
    """Liệt kê ngắn gọn `expert_id: role_title` để LLM chọn cho từng góc kể."""
    return "\n".join(
        f"- `{expert_id}`: {expert['role_title']}"
        for expert_id, expert in DOMAIN_EXPERTS.items()
    )


def render_angle_miner_prompt(
    source_chunk: str,
    book_title: str = "Tư liệu nghiên cứu",
    num_angles: int = 3,
    existing_topics: str = "",
    domain_expert: str = "auto",
) -> str:
    """Render prompt khai thác nhiều góc kể độc lập từ một đoạn sách/tư liệu RAG."""
    expert_info = select_domain_expert(
        book_title,
        source_context=source_chunk,
        preferred_expert=domain_expert,
    )
    values = {
        "book_title": book_title,
        "source_chunk": source_chunk.strip(),
        "num_angles": max(1, min(6, int(num_angles))),
        "existing_topics": existing_topics.strip() or "Chưa có.",
        "models_catalog": format_models_catalog_for_prompt(),
        "domain_expert_role": expert_info["expert_role"],
        "domain_expert_lens": expert_info["expert_lens"],
        "domain_experts_catalog": _format_domain_experts_catalog(),
    }
    out = PROMPT_ANGLE_MINER_TEMPLATE
    for k in _TOKENS:
        out = out.replace("{" + k + "}", str(values[k]))
    return out

