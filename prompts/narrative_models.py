"""
Kho Mô hình Lý thuyết & Bộ Chọn Mô hình Kịch bản Tối ưu theo Chủ đề Đầu vào.

Tích hợp đầy đủ:
- 5 nguyên lý nền tảng nhận thức/tự sự (ABT, Information Gap, Micro Beat Sheet & Callback,
  Dual-Coding & Multimedia Coherence, Habituation Break & Zeigarnik Effect).
- 12 mô hình cấu trúc kịch bản phổ biến chia theo 3 nhóm mục tiêu:
  1. Nhóm Phim Tài liệu / Edutainment / Kể chuyện: abt, in_medias_res, freytag_3_act, pixar_story_spine, scqa
  2. Nhóm Short-Form Viral (TikTok / Reels / Shorts): hook_retain_payoff, myth_vs_reality, open_loops, rule_of_three
  3. Nhóm Thuyết phục / Bán hàng / B2B: pas, bab, aida
"""

from __future__ import annotations

import re
from typing import Any

CORE_COGNITIVE_PRINCIPLES: tuple[dict[str, str], ...] = (
    {
        "id": "information_gap",
        "name": "Information Gap Theory (George Loewenstein)",
        "rule_ref": "RULE #3 & Hook 6–11 từ",
        "directive": "Mở đầu bằng khoảng vênh nhận thức giữa điều người xem tin và thực tế để kích hoạt tò mò trong 3 giây đầu.",
    },
    {
        "id": "dual_coding",
        "name": "Dual-Coding & Multimedia Coherence (Paivio & Mayer)",
        "rule_ref": "RULE #1, RULE #2 & subtitle_vn",
        "directive": "Kênh hình khớp 1-1 với vật thể/hành động của đúng câu đang đọc; loại bỏ slide, chart, text rác trong ảnh.",
    },
    {
        "id": "habituation_zeigarnik",
        "name": "Habituation Break & Zeigarnik Effect",
        "rule_ref": "Biến thiên nhịp câu + sfx_cue",
        "directive": "Xen câu Twist ngắn gắt (7–12 từ) giữa các câu 13–20 từ, mỗi cảnh thêm thông tin mới để chống tê liệt chú ý.",
    },
    {
        "id": "bookend_callback",
        "name": "Micro Beat Sheet & Bookend Callback",
        "rule_ref": "Cấu trúc 8–10 cảnh",
        "directive": "Mỗi cảnh giữ đúng một vai trò tâm lý; cảnh cuối quay lại hình ảnh/ý mở đầu ở tầng nghĩa cao hơn.",
    },
)

NARRATIVE_MODELS: dict[str, dict[str, Any]] = {
    # ═══════════════════════════════════════════════════════════════════════
    # A. NHÓM PHIM TÀI LIỆU / EDUTAINMENT / KỂ CHUYỆN
    # ═══════════════════════════════════════════════════════════════════════
    "abt": {
        "id": "abt",
        "name": "ABT (And–But–Therefore)",
        "group": "documentary",
        "group_label": "Phim Tài liệu / Edutainment / Kể chuyện",
        "core_structure": "Bối cảnh (And) -> Mâu thuẫn (But) -> Hệ quả (Therefore)",
        "best_for": "Lịch sử, khoa học, kinh tế, giải thích cơ chế nhân quả",
        "preferred_genres": ("science_nature", "economics_business", "history_culture", "history_war"),
        "phrase_signals": (
            ("tại sao", 3),
            ("vì sao", 3),
            ("nguyên nhân", 2),
            ("cơ chế", 3),
            ("lạm phát", 3),
            ("mất giá", 3),
            ("kinh tế", 2),
            ("khoa học", 2),
            ("hệ quả", 2),
            ("quy luật", 2),
            ("tiến hóa", 2),
            ("vũ trụ", 2),
            ("khí hậu", 2),
            ("lịch sử", 1),
        ),
        "beat_sheet_8_10": (
            "- Cảnh 1 (**HOOK — 6–11 từ**): Nêu một hệ quả hoặc sự thật nhân quả gây tò mò ngay lập tức.\n"
            "- Cảnh 2–4 (**AND — Thừa nhận bối cảnh**): Đặt nền sự thật quen thuộc mà khán giả dễ đồng ý.\n"
            "- Cảnh 5 (**BUT — Bước ngoặt ngắn gắt 7–12 từ**): Đập mâu thuẫn cốt lõi phá vỡ giả định ban đầu.\n"
            "- Cảnh 6–Kế cuối (**Cơ chế & Bằng chứng**): Trình bày cơ chế ẩn hoặc dữ kiện cụ thể giải thích chữ *But*.\n"
            "- Cảnh cuối (**THEREFORE — Kết Callback 10–14 từ**): Chốt hệ quả tất yếu, quay lại ý Hook ở tầng nghĩa mới."
        ),
        "outro_style": "Chốt hệ quả tất yếu (Therefore) nối thẳng về hình ảnh/ý mở đầu, không rao giảng.",
    },
    "in_medias_res": {
        "id": "in_medias_res",
        "name": "In Medias Res (Giữa cao trào)",
        "group": "documentary",
        "group_label": "Phim Tài liệu / Edutainment / Kể chuyện",
        "core_structure": "Nhảy thẳng vào khoảnh khắc căng nhất -> Tua ngược giải thích -> Quay lại kết cục",
        "best_for": "Vụ án, chiến dịch quân sự, thảm họa, sự cố sinh tồn",
        "preferred_genres": ("true_story_crime", "history_war"),
        "phrase_signals": (
            ("vụ án", 4),
            ("án mạng", 4),
            ("chiến dịch", 3),
            ("trận đánh", 3),
            ("thảm họa", 4),
            ("chìm tàu", 4),
            ("rơi máy bay", 4),
            ("vụ nổ", 3),
            ("hỏa hoạn", 3),
            ("đột kích", 3),
            ("gián điệp", 3),
            ("sinh tồn", 3),
            ("tội phạm", 3),
            ("tai nạn", 3),
            ("điện biên", 3),
            ("phút cuối", 2),
        ),
        "beat_sheet_8_10": (
            "- Cảnh 1 (**HOOK — Giữa cơn bão, 6–11 từ**): Ném thẳng người xem vào giây phút căng thẳng/nguy kịch nhất đang diễn ra.\n"
            "- Cảnh 2–3 (**Tua ngược mốc khởi phát**): Đặt câu hỏi vì sao mọi thứ đi tới điểm này rồi lùi về nguyên nhân đầu tiên.\n"
            "- Cảnh 4–5 (**Chuỗi mắt xích leo thang**): Từng sai lầm hoặc quyết định đẩy sự việc tiến sát mép vực.\n"
            "- Cảnh 6 (**TWIST — Điểm gãy 7–12 từ**): Chi tiết bước ngoặt khiến cục diện không còn đường lui.\n"
            "- Cảnh 7–Kế cuối (**Khoảnh khắc bùng nổ**): Diễn biến tại hiện trường khép nối lại giây phút ở Cảnh 1.\n"
            "- Cảnh cuối (**Kết Callback 10–14 từ**): Dư chấn thực tế sau biến cố và cái giá lịch sử."
        ),
        "outro_style": "Khép vòng quay lại khoảnh khắc hỗn loạn ở Cảnh 1, nhấn mạnh hệ quả thực địa.",
    },
    "freytag_3_act": {
        "id": "freytag_3_act",
        "name": "Freytag's Pyramid / 3 Hồi",
        "group": "documentary",
        "group_label": "Phim Tài liệu / Edutainment / Kể chuyện",
        "core_structure": "Thiết lập -> Leo thang -> Cao trào -> Hạ nhiệt -> Kết cục",
        "best_for": "Kể chuyện nhân vật lịch sử, sự kiện dài, hưng thịnh và suy tàn",
        "preferred_genres": ("history_war", "history_culture"),
        "phrase_signals": (
            ("triều đại", 4),
            ("hưng thịnh", 4),
            ("suy tàn", 4),
            ("sự trỗi dậy", 4),
            ("chiến tranh", 3),
            ("cách mạng", 3),
            ("vương quốc", 3),
            ("đế chế", 3),
            ("kỷ nguyên", 3),
            ("thời kỳ", 2),
            ("bi kịch", 2),
            ("hồi kết", 2),
        ),
        "beat_sheet_8_10": (
            "- Cảnh 1 (**HOOK — Khơi xung đột, 6–11 từ**): Điểm nứt đầu tiên báo hiệu bi kịch hoặc bước ngoặt thời đại.\n"
            "- Cảnh 2–3 (**Hồi 1 — Thiết lập**): Thế cân bằng ban đầu và tham vọng/điều kiện khởi sinh.\n"
            "- Cảnh 4–5 (**Hồi 2 — Leo thang**): Mâu thuẫn chồng chéo đẩy sự kiện lên đỉnh căng thẳng.\n"
            "- Cảnh 6 (**CAO TRÀO — Twist ngắn gắt 7–12 từ**): Khoảnh khắc đỉnh điểm định đoạt thắng thua.\n"
            "- Cảnh 7–Kế cuối (**Hạ nhiệt**): Phản ứng dây chuyền sau cao trào làm trật tự cũ tan rã.\n"
            "- Cảnh cuối (**Hồi 3 — Kết cục 10–14 từ**): Dư âm lịch sử khép trọn vòng cung 3 hồi."
        ),
        "outro_style": "Chốt cục diện cuối cùng của vòng cung 3 hồi bằng hình ảnh biểu tượng còn sót lại.",
    },
    "pixar_story_spine": {
        "id": "pixar_story_spine",
        "name": "Pixar Story Spine",
        "group": "documentary",
        "group_label": "Phim Tài liệu / Edutainment / Kể chuyện",
        "core_structure": "Ngày xửa... Mỗi ngày... Cho đến một ngày... Vì thế... Cuối cùng...",
        "best_for": "Storytelling nhân văn, tiểu sử, chân dung nhà sáng lập/phát minh",
        "preferred_genres": ("history_culture", "lifestyle_motivation", "psychology_philosophy"),
        "phrase_signals": (
            ("tiểu sử", 4),
            ("cuộc đời", 4),
            ("nhà phát minh", 4),
            ("người sáng lập", 4),
            ("từ hai bàn tay trắng", 4),
            ("nhân văn", 3),
            ("cảm động", 3),
            ("cậu bé", 3),
            ("cô gái", 3),
            ("người đàn ông", 3),
            ("nghệ sĩ", 3),
            ("xuất thân", 3),
            ("vượt nghịch cảnh", 3),
            ("ước mơ", 2),
        ),
        "beat_sheet_8_10": (
            "- Cảnh 1 (**HOOK — Cho đến một ngày, 6–11 từ**): Khoảnh khắc bước ngoặt thay đổi hẳn số phận nhân vật.\n"
            "- Cảnh 2–3 (**Ngày xửa & Mỗi ngày**): Xuất phát điểm đời thường và thói quen lặp lại trước biến cố.\n"
            "- Cảnh 4–5 (**Vì thế...**): Biến cố buộc nhân vật dấn thân vào chuỗi thử thách liên tiếp.\n"
            "- Cảnh 6 (**TWIST — Thử thách sinh tử 7–12 từ**): Thời khắc nhân vật tưởng như gục ngã hoàn toàn.\n"
            "- Cảnh 7–Kế cuối (**Cho đến khi...**): Lựa chọn hoặc phát kiến quyết định xoay chuyển kết cục.\n"
            "- Cảnh cuối (**Và kể từ đó — 10–14 từ**): Di sản để lại và sự đổi thay của nhân vật."
        ),
        "outro_style": "Chốt bằng di sản nhân văn cụ thể ('và kể từ đó...'), tránh khẩu hiệu giáo điều.",
    },
    "scqa": {
        "id": "scqa",
        "name": "SCQA (McKinsey)",
        "group": "documentary",
        "group_label": "Phim Tài liệu / Edutainment / Kể chuyện",
        "core_structure": "Tình huống (S) -> Biến cố (C) -> Câu hỏi (Q) -> Lời giải (A)",
        "best_for": "Phân tích kinh doanh, chiến lược B2B, tài chính doanh nghiệp, chính sách",
        "preferred_genres": ("economics_business", "tech_future"),
        "phrase_signals": (
            ("chiến lược", 4),
            ("doanh nghiệp", 4),
            ("mô hình kinh doanh", 4),
            ("chuỗi cung ứng", 4),
            ("biên lợi nhuận", 4),
            ("tái cấu trúc", 4),
            ("thâu tóm", 3),
            ("phá sản", 3),
            ("b2b", 3),
            ("thị trường", 2),
            ("cạnh tranh", 2),
            ("chính sách", 2),
            ("quản trị", 2),
            ("độc quyền", 2),
        ),
        "beat_sheet_8_10": (
            "- Cảnh 1 (**HOOK — Complication, 6–11 từ**): Đưa thẳng biến cố thị trường làm mô hình cũ lung lay.\n"
            "- Cảnh 2–3 (**Situation — Tình huống nền**): Trạng thái vận hành ổn định trước khi biến cố xuất hiện.\n"
            "- Cảnh 4–5 (**Complication & Question**): Phân tích áp lực và câu hỏi chiến lược sống còn.\n"
            "- Cảnh 6 (**TWIST — Điểm mù chiến lược 7–12 từ**): Góc nhìn cốt lõi mà đa số đối thủ bỏ sót.\n"
            "- Cảnh 7–Kế cuối (**Answer — Cơ chế lời giải**): Hành động tái cấu trúc cụ thể cùng bằng chứng kết quả.\n"
            "- Cảnh cuối (**Hàm ý điều hành — 10–14 từ**): Nguyên tắc ra quyết định rút ra từ thực tế."
        ),
        "outro_style": "Chốt hàm ý chiến lược gọn như kết luận một bản ghi nhớ điều hành (executive memo).",
    },
    # ═══════════════════════════════════════════════════════════════════════
    # B. NHÓM SHORT-FORM VIRAL (TIKTOK / REELS / SHORTS)
    # ═══════════════════════════════════════════════════════════════════════
    "hook_retain_payoff": {
        "id": "hook_retain_payoff",
        "name": "Hook – Retain – Payoff",
        "group": "short_form_viral",
        "group_label": "Short-Form Viral (TikTok / Reels / Shorts)",
        "core_structure": "3s đầu sốc -> Giữ nhịp leo thang liên tục -> Cú chốt bất ngờ",
        "best_for": "Video ngắn 30–60s đa chủ đề, khám phá nhanh, công nghệ, điều gì xảy ra nếu",
        "preferred_genres": ("tech_future", "science_nature", "lifestyle_motivation"),
        "phrase_signals": (
            ("điều gì xảy ra nếu", 4),
            ("chuyện lạ", 3),
            ("sự thật thú vị", 3),
            ("ít ai để ý", 3),
            ("tương lai", 2),
            ("công nghệ", 2),
            ("trí tuệ nhân tạo", 2),
            ("60 giây", 3),
            ("30 giây", 3),
            ("thú vị", 2),
        ),
        "beat_sheet_8_10": (
            "- Cảnh 1 (**HOOK — 3 giây dừng lướt, 6–11 từ**): Cú đánh nhận thức trực diện khiến người xem khựng lại.\n"
            "- Cảnh 2–5 (**RETAIN — Leo thang giữ nhịp**): Mỗi cảnh mở một lớp dữ kiện mới tăng cấp bất ngờ, cấm lan man.\n"
            "- Cảnh 6 (**TWIST — Bẻ lái ngắn gắt 7–12 từ**): Đảo chiều suy đoán quen thuộc trước khi chốt.\n"
            "- Cảnh 7–Kế cuối (**Tích lũy Payoff**): Mảnh ghép chứng cứ cuối cùng đẩy kỳ vọng lên cao nhất.\n"
            "- Cảnh cuối (**PAYOFF — Cú chốt 10–14 từ**): Trả câu kết sắc lẹm tạo cảm giác vỡ òa."
        ),
        "outro_style": "Trả Payoff bất ngờ nhưng hợp lý tuyệt đối với chuỗi dữ kiện vừa đưa.",
    },
    "myth_vs_reality": {
        "id": "myth_vs_reality",
        "name": "Myth vs. Reality (Lầm tưởng vs. Sự thật)",
        "group": "short_form_viral",
        "group_label": "Short-Form Viral (TikTok / Reels / Shorts)",
        "core_structure": "Lầm tưởng phổ biến -> Phá vỡ định kiến -> Sự thật ẩn -> Bằng chứng",
        "best_for": "Giải mã sự thật, phá định kiến lịch sử/khoa học/văn hóa, lật ngược quan niệm sai",
        "preferred_genres": ("history_culture", "science_nature", "economics_business", "psychology_philosophy"),
        "phrase_signals": (
            ("lầm tưởng", 4),
            ("hiểu lầm", 4),
            ("hiểu sai", 4),
            ("không phải như bạn nghĩ", 4),
            ("giải mã", 4),
            ("sự thật về", 4),
            ("sự thật ẩn", 4),
            ("diệt vong", 4),
            ("biến mất bí ẩn", 4),
            ("bị bỏ hoang", 3),
            ("sụp đổ", 3),
            ("thật ra", 3),
            ("định kiến", 3),
            ("huyền thoại", 3),
            ("còn hay mất", 5),
            ("hay đã mất", 5),
            ("đúng hay sai", 5),
            ("tuyệt chủng", 4),
            ("còn tồn tại", 4),
            ("có thật sự", 4),
        ),
        "beat_sheet_8_10": (
            "- Cảnh 1 (**HOOK — Phủ định trực diện, 6–11 từ**): Bẻ gãy ngay định kiến phổ biến về chủ đề.\n"
            "- Cảnh 2–3 (**MYTH — Vẽ lại lầm tưởng**): Kéo người xem vào cách hiểu quen thuộc trên mạng/sách cũ.\n"
            "- Cảnh 4–5 (**REALITY — Cơ chế ẩn**): Hé lộ lớp nguyên nhân thật sự ít người nhìn thấy.\n"
            "- Cảnh 6 (**TWIST — Phá vỡ ngắn gắt 7–12 từ**): Câu chốt đảo ngược hoàn toàn kết luận cũ.\n"
            "- Cảnh 7–Kế cuối (**EVIDENCE — Bằng chứng thực địa**): Dẫn chứng vật lý/khảo cổ/số liệu kiểm chứng.\n"
            "- Cảnh cuối (**CALLBACK — 10–14 từ**): Trở lại hình ảnh Hook với chân lý mới gọn ghẽ."
        ),
        "outro_style": "Quay lại lầm tưởng ở đầu clip và đặt dấu chấm hết bằng sự thật vừa chứng minh.",
    },
    "open_loops": {
        "id": "open_loops",
        "name": "Open Loops (Vòng lặp mở)",
        "group": "short_form_viral",
        "group_label": "Short-Form Viral (TikTok / Reels / Shorts)",
        "core_structure": "Mở câu hỏi A -> Mở tiếp vòng B -> Giải mã B -> Quay về đóng trọn A",
        "best_for": "Bí ẩn chưa lời giải, tâm lý học nhận thức, hiệu ứng lạ, thí nghiệm hành vi",
        "preferred_genres": ("psychology_philosophy", "true_story_crime", "science_nature"),
        "phrase_signals": (
            ("bí ẩn", 4),
            ("vòng lặp", 4),
            ("tâm lý", 3),
            ("hiệu ứng", 4),
            ("nghịch lý", 4),
            ("thí nghiệm", 3),
            ("tiềm thức", 3),
            ("ảo giác", 3),
            ("mất tích", 3),
            ("chưa lời giải", 4),
            ("không thể giải thích", 4),
            ("tại sao não", 4),
        ),
        "beat_sheet_8_10": (
            "- Cảnh 1 (**HOOK — Mở Loop A, 6–11 từ**): Nêu nghịch lý hoặc dấu hỏi lớn chưa giải thích ngay.\n"
            "- Cảnh 2–3 (**Mở Loop B**): Đưa manh mối đầu tiên nhưng manh mối này lại đẻ ra câu hỏi thứ hai kỳ lạ hơn.\n"
            "- Cảnh 4–5 (**Lần theo Loop B**): Bóc từng lớp bằng chứng làm câu đố ngày càng sát đáp án.\n"
            "- Cảnh 6 (**TWIST — Chìa khóa ngắn gắt 7–12 từ**): Manh mối bất ngờ nối thẳng Loop B vào Loop A.\n"
            "- Cảnh 7–Kế cuối (**Đóng Loop B**): Giải tỏa nút thắt phụ bằng cơ chế thực tế.\n"
            "- Cảnh cuối (**Đóng Loop A — 10–14 từ**): Trả lời trọn vẹn câu hỏi ở Cảnh 1 khiến não được giải tỏa."
        ),
        "outro_style": "Đóng kín vòng lặp đầu tiên (Loop A) bằng một câu trả lời trọn vẹn, không bỏ lửng.",
    },
    "rule_of_three": {
        "id": "rule_of_three",
        "name": "Rule of Three / Listicle",
        "group": "short_form_viral",
        "group_label": "Short-Form Viral (TikTok / Reels / Shorts)",
        "core_structure": "Hook tổng -> Điểm 1 (quen) -> Điểm 2 (sâu hơn) -> Điểm 3 (đắt giá nhất) -> Chốt",
        "best_for": "3 lý do, 3 sai lầm, 3 dấu hiệu, mẹo/nguyên tắc, tổng hợp kiến thức nhanh",
        "preferred_genres": ("lifestyle_motivation", "economics_business", "psychology_philosophy", "tech_future"),
        "phrase_signals": (
            ("3 lý do", 5),
            ("ba lý do", 5),
            ("3 sai lầm", 5),
            ("ba sai lầm", 5),
            ("3 dấu hiệu", 5),
            ("ba dấu hiệu", 5),
            ("3 cách", 5),
            ("ba cách", 5),
            ("3 nguyên tắc", 5),
            ("top 3", 5),
            ("những sai lầm", 3),
            ("bí quyết", 3),
            ("thói quen", 2),
        ),
        "beat_sheet_8_10": (
            "- Cảnh 1 (**HOOK — Gọi tên bộ 3, 6–11 từ**): Đặt khung 3 yếu tố quyết định bằng tuyên bố dứt khoát.\n"
            "- Cảnh 2–3 (**Điểm 1 — Tầng bề mặt**): Lý do/sai lầm đầu tiên dễ thấy nhưng chưa đủ giải thích.\n"
            "- Cảnh 4–5 (**Điểm 2 — Tầng cơ chế**): Yếu tố thứ hai sâu hơn đang âm thầm khuếch đại vấn đề.\n"
            "- Cảnh 6 (**TWIST — Nhấn trước Điểm 3, 7–12 từ**): Câu dẫn ngắn gắt báo hiệu nhân tố quyết định.\n"
            "- Cảnh 7–Kế cuối (**Điểm 3 — Đắt giá nhất**): Lý do/bài học thứ ba lật ngược toàn bộ cách nhìn.\n"
            "- Cảnh cuối (**TỔNG KẾT — 10–14 từ**): Gộp cả 3 điểm thành một nguyên tắc sắc gọn."
        ),
        "outro_style": "Gói 3 điểm vừa liệt kê vào một nguyên tắc nhớ ngay sau khi xem xong.",
    },
    # ═══════════════════════════════════════════════════════════════════════
    # C. NHÓM THUYẾT PHỤC / BÁN HÀNG / B2B
    # ═══════════════════════════════════════════════════════════════════════
    "pas": {
        "id": "pas",
        "name": "PAS (Problem – Agitate – Solution)",
        "group": "persuasion_b2b",
        "group_label": "Thuyết phục / Bán hàng / B2B",
        "core_structure": "Problem (Vấn đề) -> Agitate (Khoét nỗi đau) -> Solution (Giải pháp)",
        "best_for": "Quảng cáo giải pháp, sản phẩm/dịch vụ, thuyết phục xử lý rủi ro/nỗi đau",
        "preferred_genres": ("economics_business", "tech_future", "lifestyle_motivation"),
        "phrase_signals": (
            ("nỗi đau", 4),
            ("thất thoát", 4),
            ("lỗ hổng", 4),
            ("tấn công mạng", 4),
            ("rò rỉ dữ liệu", 4),
            ("tốn kém", 3),
            ("sản phẩm", 3),
            ("dịch vụ", 3),
            ("quảng cáo", 4),
            ("bán hàng", 3),
            ("giải pháp", 3),
            ("khắc phục", 3),
            ("rủi ro", 2),
            ("khách hàng", 2),
        ),
        "beat_sheet_8_10": (
            "- Cảnh 1 (**HOOK — Problem, 6–11 từ**): Gọi thẳng tên vấn đề hoặc thất thoát mà người xem đang gánh.\n"
            "- Cảnh 2–4 (**AGITATE — Khoét nỗi đau thực tế**): Mô tả cái giá cụ thể về tiền, thời gian hoặc rủi ro nếu trì hoãn.\n"
            "- Cảnh 5 (**TWIST — Ngưỡng báo động 7–12 từ**): Câu cắt sắc chỉ ra điểm không thể làm ngơ.\n"
            "- Cảnh 6–Kế cuối (**SOLUTION — Cơ chế xử lý tận gốc**): Hình ảnh vận hành giải pháp thực tế ngoài đời.\n"
            "- Cảnh cuối (**KẾT & CTA — 10–14 từ**): Lời kêu gọi hành động / cam kết kết quả rõ ràng."
        ),
        "outro_style": "Chốt lời kêu gọi chuyển từ tình trạng thất thoát sang hành động xử lý dứt điểm.",
    },
    "bab": {
        "id": "bab",
        "name": "BAB (Before – After – Bridge)",
        "group": "persuasion_b2b",
        "group_label": "Thuyết phục / Bán hàng / B2B",
        "core_structure": "Before (Trước) -> After (Sau) -> Bridge (Giải pháp cầu nối)",
        "best_for": "Case study B2B, chuyển đổi số, triển khai hạ tầng/cloud, tối ưu vận hành",
        "preferred_genres": ("tech_future", "economics_business"),
        "phrase_signals": (
            ("case study", 5),
            ("chuyển đổi số", 5),
            ("trước và sau", 5),
            ("lột xác", 4),
            ("tự động hóa", 4),
            ("nâng cấp hệ thống", 4),
            ("triển khai cloud", 4),
            ("hiệu suất", 3),
            ("tiết kiệm chi phí", 4),
            ("giảm thời gian", 3),
            ("chính phủ số", 4),
            ("hạ tầng", 2),
        ),
        "beat_sheet_8_10": (
            "- Cảnh 1 (**HOOK — Before, 6–11 từ**): Cảnh tượng bế tắc hoặc nghẽn cổ chai trước khi thay đổi.\n"
            "- Cảnh 2–3 (**BEFORE — Hiện trạng cũ**): Nút thắt thủ công, chậm trễ và chi phí ẩn trong quy trình cũ.\n"
            "- Cảnh 4–5 (**AFTER — Trạng thái sau chuyển đổi**): Cảnh vận hành trơn tru và chỉ số cải thiện thực tế.\n"
            "- Cảnh 6 (**TWIST — Điểm nối ngắn gắt 7–12 từ**): Chỉ ra khoảng cách giữa hai trạng thái nằm ở đâu.\n"
            "- Cảnh 7–Kế cuối (**BRIDGE — Cây cầu giải pháp**): Cách công nghệ hoặc kiến trúc mới nối từ Before sang After.\n"
            "- Cảnh cuối (**CHỐT GIÁ TRỊ — 10–14 từ**): Khẳng định bước chuyển bền vững và hướng áp dụng."
        ),
        "outro_style": "Khẳng định cầu nối (Bridge) đã đưa thực tế từ tắc nghẽn sang vận hành chủ động.",
    },
    "aida": {
        "id": "aida",
        "name": "AIDA (Attention – Interest – Desire – Action)",
        "group": "persuasion_b2b",
        "group_label": "Thuyết phục / Bán hàng / B2B",
        "core_structure": "Attention (Chú ý) -> Interest (Hứng thú) -> Desire (Khao khát) -> Action (Hành động)",
        "best_for": "Video landing page, ra mắt sản phẩm/nền tảng, chốt đăng ký/CTA",
        "preferred_genres": ("tech_future", "economics_business", "lifestyle_motivation"),
        "phrase_signals": (
            ("landing page", 5),
            ("ra mắt", 4),
            ("đăng ký", 4),
            ("dùng thử", 4),
            ("chốt đơn", 4),
            ("ưu đãi", 4),
            ("khóa học", 3),
            ("nền tảng mới", 3),
            ("trải nghiệm ngay", 4),
            ("đặt lịch", 4),
            ("cta", 4),
            ("demo", 3),
        ),
        "beat_sheet_8_10": (
            "- Cảnh 1 (**ATTENTION — 6–11 từ**): Mở khóa sự chú ý bằng tuyên bố hoặc hình ảnh đột phá.\n"
            "- Cảnh 2–4 (**INTEREST — Khơi hứng thú**): Trình diễn cơ chế hoạt động thực tế khiến người xem tò mò.\n"
            "- Cảnh 5 (**TWIST — Lợi thế khác biệt 7–12 từ**): Điểm vượt trội không thể thay thế.\n"
            "- Cảnh 6–Kế cuối (**DESIRE — Tạo khao khát**): Kết quả cụ thể và bằng chứng kiểm chứng ngoài đời.\n"
            "- Cảnh cuối (**ACTION — Chốt CTA 10–14 từ**): Kêu gọi bước hành động rõ ràng, không sáo rỗng."
        ),
        "outro_style": "Chốt lời kêu gọi hành động (Action) cụ thể, trực diện và dễ thực hiện ngay.",
    },
}

VALID_NARRATIVE_MODELS = frozenset(NARRATIVE_MODELS.keys())


def format_models_catalog_for_prompt() -> str:
    """Xuất bảng rút gọn 12 mô hình kịch bản theo 3 nhóm để nhúng vào LLM prompt."""
    groups = (
        ("documentary", "A. Phim Tài liệu / Edutainment / Kể chuyện"),
        ("short_form_viral", "B. Short-Form Viral (TikTok / Reels / Shorts)"),
        ("persuasion_b2b", "C. Thuyết phục / Bán hàng / B2B"),
    )
    lines: list[str] = []
    for g_key, g_title in groups:
        lines.append(f"**{g_title}:**")
        for m in NARRATIVE_MODELS.values():
            if m["group"] == g_key:
                lines.append(
                    f"- `{m['id']}` ({m['name']}): {m['core_structure']} | Phù hợp: {m['best_for']}"
                )
    return "\n".join(lines)


def render_model_beat_sheet_block(model_id: str) -> str:
    """Sinh block cấu trúc Beat Sheet 8–10 cảnh tương ứng với mô hình được chọn."""
    model = NARRATIVE_MODELS.get(model_id) or NARRATIVE_MODELS["abt"]
    return (
        f"Mô hình áp dụng: `{model['id']}` — **{model['name']}** ({model['group_label']})\n"
        f"Khung cốt lõi: {model['core_structure']}\n"
        f"Phân vai Beat Sheet 8–10 cảnh theo `{model['id']}`:\n"
        f"{model['beat_sheet_8_10']}"
    )


def select_optimal_narrative_model(
    user_request: str,
    source_context: str = "",
    genre_hint: str = "",
    preferred_model: str = "auto",
) -> dict[str, Any]:
    """
    Chấm điểm tất cả 12 mô hình dựa trên nội dung chủ đề đầu vào (`user_request` + `source_context`)
    và chọn mô hình tối ưu nhất. Hỗ trợ ép chọn thủ công qua `preferred_model`.
    """
    req_norm = preferred_model.strip().lower()
    if req_norm and req_norm != "auto":
        if req_norm not in NARRATIVE_MODELS:
            valid = ", ".join(sorted(VALID_NARRATIVE_MODELS))
            raise ValueError(f"`preferred_model` không hợp lệ: '{preferred_model}'. Hợp lệ: {valid}.")
        chosen = NARRATIVE_MODELS[req_norm]
        return {
            "selected_model_id": req_norm,
            "selected_model": chosen,
            "selection_mode": "manual",
            "rationale": f"Áp dụng theo chỉ định thủ công mô hình {chosen['name']}.",
            "matched_signals": [],
            "scores": {req_norm: 100},
            "runner_ups": [],
        }

    haystack = f"{user_request}\n{source_context}".lower()
    scores: dict[str, int] = {}
    matched_by_model: dict[str, list[str]] = {}

    for m_id, m in NARRATIVE_MODELS.items():
        score = 0
        hits: list[str] = []
        for phrase, weight in m["phrase_signals"]:
            if re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", haystack):
                # Ưu tiên cụm từ xuất hiện trực tiếp trong user_request
                boost = weight * 2 if phrase in user_request.lower() else weight
                score += boost
                hits.append(phrase)
        if genre_hint and genre_hint in m["preferred_genres"]:
            score += 2
            hits.append(f"genre:{genre_hint}")
        scores[m_id] = score
        matched_by_model[m_id] = hits

    # Quy tắc cấu trúc đặc thù (pattern regex cấp độ câu hỏi/đếm số)
    if re.search(r"\b(3|ba|top\s*3)\s+(lý do|sai lầm|dấu hiệu|cách|bước|nguyên tắc|bí quyết)\b", haystack):
        scores["rule_of_three"] += 8
        matched_by_model["rule_of_three"].append("pattern:3_list")

    if re.search(r"\b(bị\s+diệt\s+vong|sụp\s+đổ|biến\s+mất|lầm\s+tưởng|giải\s+mã|không\s+phải\s+như)\b", haystack):
        scores["myth_vs_reality"] += 4
        matched_by_model["myth_vs_reality"].append("pattern:myth_debunk")

    if re.search(r"^(tại\s+sao|vì\s+sao)\b", user_request.strip().lower()):
        scores["abt"] += 2
        matched_by_model["abt"].append("pattern:why_question")

    # Ưu tiên xếp hạng theo (score giảm dần, độ đặc hiệu tín hiệu)
    ranked = sorted(
        NARRATIVE_MODELS.keys(),
        key=lambda k: (scores[k], len(matched_by_model[k])),
        reverse=True,
    )
    best_id = ranked[0]

    # Nếu không có tín hiệu rõ rệt nào (>0), chọn fallback hợp lý nhất theo độ dài chủ đề
    if scores[best_id] == 0:
        best_id = "hook_retain_payoff" if len(user_request.split()) <= 8 else "abt"
        rationale = (
            f"Chủ đề mang tính khám phá tổng quát, chọn mặc định tối ưu `{best_id}` "
            f"({NARRATIVE_MODELS[best_id]['name']})."
        )
    else:
        chosen_hits = ", ".join(matched_by_model[best_id][:4])
        rationale = (
            f"Chủ đề khớp mạnh với `{best_id}` ({NARRATIVE_MODELS[best_id]['name']}) "
            f"nhờ tín hiệu [{chosen_hits}] — tối ưu cho nhóm {NARRATIVE_MODELS[best_id]['best_for']}."
        )

    runner_ups = [
        {"id": r_id, "name": NARRATIVE_MODELS[r_id]["name"], "score": scores[r_id]}
        for r_id in ranked[1:4]
        if scores[r_id] > 0
    ]

    return {
        "selected_model_id": best_id,
        "selected_model": NARRATIVE_MODELS[best_id],
        "selection_mode": "auto",
        "rationale": rationale,
        "matched_signals": matched_by_model[best_id],
        "scores": scores,
        "runner_ups": runner_ups,
    }

