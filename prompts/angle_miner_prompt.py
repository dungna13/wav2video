"""
Prompt cho Node `angle_miner_node` — KHAI THÁC GÓC KỂ TỪ TƯ LIỆU SÁCH / RAG CHUNK.

Chạy TRƯỚC `prompt_architect_node` khi đầu vào là một chương sách, báo cáo dài, hoặc RAG chunk.
Mục tiêu: tách một đoạn tư liệu thành 3–5 góc kể phim tài liệu ngắn 9:16 độc lập,
không trùng lặp và bám sát sự thật trong `source_chunk` (không bịa ngoài văn bản).

Render bằng `render_angle_miner_prompt(...)` (thay token, không dùng str.format).
"""

from .narrative_models import format_models_catalog_for_prompt

PROMPT_ANGLE_MINER_TEMPLATE = """Bạn là **Trưởng ban Biên tập Phim Tài liệu Ngắn 9:16** (phong cách Vox / Johnny Harris / Thư Viện Lịch Sử).
Nhiệm vụ: đọc đoạn tư liệu gốc dưới đây và khai thác **{num_angles} góc kể (angles) độc lập** để sản xuất {num_angles} clip ngắn khác nhau — TUYỆT ĐỐI KHÔNG tóm tắt dàn trải cả chương sách.

Tên tác phẩm / nguồn: "{book_title}"
Các chủ đề đã làm trước đó (TRÁNH TRÙNG): "{existing_topics}"

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
   - Mỗi góc phải sinh sẵn `user_request_for_architect` (1 câu đề bài sắc nét), `hook_idea_vn` (6–11 từ, pattern interrupt), `recommended_genre`, `recommended_intent_mode`, `recommended_narrative_model` (1 trong 12 ID ở danh mục bên dưới) và `model_selection_reason` (1 câu ngắn giải thích vì sao mô hình đó hợp nhất với góc kể này).

═══ DANH MỤC 12 MÔ HÌNH KỊCH BẢN (CHỌN 1 ID TỐI ƯU CHO MỖI GÓC) ═══
{models_catalog}

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
      "recommended_narrative_model": "abt | in_medias_res | freytag_3_act | pixar_story_spine | scqa | hook_retain_payoff | myth_vs_reality | open_loops | rule_of_three | pas | bab | aida",
      "model_selection_reason": "1 câu giải thích vì sao mô hình kịch bản này tối ưu cho góc kể trên",
      "key_evidence_quote": "Chi tiết/câu neo trích trực tiếp từ tư liệu nguồn"
    }
  ]
}"""


_TOKENS = ("book_title", "source_chunk", "num_angles", "existing_topics", "models_catalog")


def render_angle_miner_prompt(
    source_chunk: str,
    book_title: str = "Tư liệu nghiên cứu",
    num_angles: int = 3,
    existing_topics: str = "",
) -> str:
    """Render prompt khai thác nhiều góc kể độc lập từ một đoạn sách/tư liệu RAG."""
    values = {
        "book_title": book_title,
        "source_chunk": source_chunk.strip(),
        "num_angles": max(1, min(6, int(num_angles))),
        "existing_topics": existing_topics.strip() or "Chưa có.",
        "models_catalog": format_models_catalog_for_prompt(),
    }
    out = PROMPT_ANGLE_MINER_TEMPLATE
    for k in _TOKENS:
        out = out.replace("{" + k + "}", str(values[k]))
    return out

