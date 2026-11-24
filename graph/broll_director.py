"""
Module Sản xuất Video Dài (1-10 phút) Chế độ B-Roll Tư liệu & Lồng tiếng (`graph/broll_director.py`).

Đặc điểm & Thiết kế:
1. Thuần Python tuyến tính (Pure Python Pipeline):
   - Tuyệt đối KHÔNG dùng các thư viện vẽ đồ thị hay DAG phức tạp (Không dùng LangGraph, NetworkX, Airflow).
   - Luồng chạy tuần tự rõ ràng: Kịch bản (LLM) -> Thu âm (TTS) -> Tự động tìm/tải B-roll (yt-dlp) -> Dựng & Cắt cảnh -> Lồng tiếng & Subtitle -> Xuất video.
2. Tự động tìm & tải B-roll phù hợp chủ đề:
   - LLM sinh các truy vấn tìm kiếm tiếng Anh tối ưu cho Footage/B-roll 4K (Cinematic drone, timelapse, macro, documentary).
   - Tự động dùng `yt-dlp` tìm và tải 1-3 clip B-roll độ phân giải cao (1080p) khớp chủ đề, hoặc nhận video có sẵn từ tham số `--footage`.
3. Kịch bản độ dài tùy biến (3 phút, 5 phút,... theo yêu cầu):
   - Tự động tính toán số lượng từ (Pacing rate ~155 từ/phút ở tốc độ 1.35x chuẩn TikTok vanthanhthu09).
   - Ví dụ: 3 phút = ~460 từ (10-12 cảnh), 5 phút = ~770 từ (18-22 cảnh).
   - Cấu trúc kịch bản tài liệu chuyên nghiệp: Hook mở đầu -> Đặt bối cảnh -> Các manh mối / Bí ẩn -> Cao trào -> Đúc kết triết lý.
4. Dựng phim thông minh & Subtitle TikTok:
   - Cắt B-roll thành các nhịp chuyển cảnh 3s - 5.5s (giống hệt phong cách video triệu view tham khảo).
   - Lặp và đan xen đa góc quay để phủ kín toàn bộ thời lượng audio.
   - Subtitle chuẩn TikTok (chữ vàng/trắng viền đen, nằm trong Safe Zone tránh bị che bởi giao diện TikTok).
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import imageio_ffmpeg

from config.settings import WORKSPACE_DIR, VIDEO_FPS
from graph.audio_sync import synthesize_scene_voiceover
from graph.llm_client import call_gemini_thinking_structured


# =====================================================================
# 1. SCHEMA KỊCH BẢN DÀI CHO LLM
# =====================================================================
BROLL_SCRIPT_SCHEMA: Dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING"},
        "topic_summary_vn": {"type": "STRING"},
        "duration_mins": {"type": "NUMBER"},
        "target_word_count": {"type": "INTEGER"},
        "broll_search_queries": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
        },
        "sections": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "section_index": {"type": "INTEGER"},
                    "title": {"type": "STRING"},
                    "narration_vn": {"type": "STRING"},
                    "visual_mood": {"type": "STRING"},
                },
                "required": ["section_index", "title", "narration_vn", "visual_mood"],
            },
        },
    },
    "required": ["title", "duration_mins", "target_word_count", "broll_search_queries", "sections"],
}


def _get_ffmpeg_bin() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def _get_ytdlp_cmd() -> List[str]:
    """Tìm lệnh yt-dlp tối ưu và tương thích trên cả Windows & Linux."""
    # 1. Thử module python
    try:
        import yt_dlp
        return [sys.executable, "-m", "yt_dlp"]
    except ImportError:
        pass

    # 2. Thử tự động cài đặt yt-dlp qua pip nếu máy chưa có
    try:
        print("⏳ [B-Roll Auto-Fetch] Đang tự động nạp thư viện yt-dlp để kéo video tư liệu...")
        res = subprocess.run([sys.executable, "-m", "pip", "install", "yt-dlp", "-q"], capture_output=True, timeout=40)
        if res.returncode == 0:
            return [sys.executable, "-m", "yt_dlp"]
    except Exception:
        pass

    # 3. Thử tìm file thực thi yt-dlp.exe trong Scripts (Windows) hoặc bin (Linux)
    scripts_dir = Path(sys.executable).parent / ("Scripts" if os.name == "nt" else "bin")
    for name in ("yt-dlp.exe", "yt-dlp"):
        p = scripts_dir / name
        if p.exists():
            return [str(p)]

    # 4. Thử tìm trong venv lân cận
    base_dir = Path(__file__).resolve().parent.parent
    for venv_path in (base_dir / ".venv", base_dir.parent / ".venv"):
        v_scripts = venv_path / ("Scripts" if os.name == "nt" else "bin")
        for name in ("yt-dlp.exe", "yt-dlp"):
            p = v_scripts / name
            if p.exists():
                return [str(p)]

    return ["yt-dlp"]


def _translate_topic_to_english_queries(topic: str) -> List[str]:
    """Tự động ánh xạ từ khóa chủ đề tiếng Việt sang các cụm tìm kiếm tiếng Anh 4K sắc nét chuẩn xác theo đúng chủ đề."""
    t_low = (topic or "").lower()

    # 1. Thí nghiệm Universe 25 / Thiên đường chuột / Hành vi
    if any(k in t_low for k in ("universe 25", "chuột", "chuot", "calhoun", "thiên đường chuột")):
        return [
            "Universe 25 mouse utopia experiment documentary 4k",
            "Mice behavior laboratory science experiment 4k footage",
            "Behavioral sink Universe 25 documentary footage",
            "Laboratory mice colony experiment 4k b-roll",
        ]

    # 2. Thí nghiệm nhà tù Stanford / Tâm lý học
    if any(k in t_low for k in ("stanford", "nhà tù", "nha tu", "cai ngục", "cai nguc")):
        return [
            "Stanford prison experiment documentary 4k footage",
            "Prison psychology experiment documentary 4k",
            "Psychological experiment human behavior documentary b-roll",
        ]

    # 3. Rãnh Mariana / Nơi sâu nhất đại dương
    if any(k in t_low for k in ("mariana", "nơi sâu nhất", "noi sau nhat", "đáy biển", "day bien")):
        return [
            "Mariana trench deepest ocean abyss 4k documentary",
            "Deep sea creatures ocean exploration underwater 4k footage",
            "Abyssal ocean trench submarine exploration 4k",
        ]

    # 4. Hố đen vũ trụ / Thiên hà / Không gian sâu
    if any(k in t_low for k in ("hố đen", "ho den", "vũ trụ", "vu tru", "thiên hà", "black hole", "space")):
        return [
            "Black hole space deep cosmos 4k cinematic documentary",
            "Galaxy universe stars space travel 4k footage",
            "Astrophysics space science documentary b-roll 4k",
        ]

    # 5. Tàu ma Mary Celeste / Tàu mất tích
    if any(k in t_low for k in ("mary celeste", "tàu ma", "tau ma", "mất tích bí ẩn")):
        return [
            "Mary Celeste ghost ship ocean mystery documentary 4k",
            "Abandoned ship drifting at sea 4k cinematic footage",
            "Ghost ship maritime mystery documentary b-roll 4k",
        ]

    # 6. Bản thảo Voynich / Cuốn sách bí ẩn
    if any(k in t_low for k in ("voynich", "bản thảo", "ban thao", "cuốn sách")):
        return [
            "Voynich manuscript mysterious book documentary 4k",
            "Ancient mysterious book medieval manuscript 4k footage",
            "Cipher manuscript uncrackable code documentary 4k",
        ]

    # 7. Tín hiệu Wow / Vũ trụ / Người ngoài hành tinh
    if any(k in t_low for k in ("tín hiệu wow", "tin hieu wow", "wow signal", "ngoài hành tinh")):
        return [
            "Wow signal radio telescope deep space astronomy 4k",
            "SETI radio observatory cosmos documentary 4k",
            "Deep space radio signals cosmos 4k footage",
        ]

    # 8. Kim Tự Tháp Giza / Ai Cập
    if any(k in t_low for k in ("kim tự tháp", "giza", "kim tu thap", "pyramid", "ai cập", "egypt")):
        return [
            "Great Pyramid of Giza chambers interior 4k documentary b-roll",
            "Pyramids of Giza aerial 4k cinematic drone footage",
            "Ancient Egypt Giza plateau mystery 4k footage",
            "Pyramid construction mystery 4k cinematic documentary",
        ]

    # 9. Bãi đá cổ Stonehenge
    if any(k in t_low for k in ("stonehenge", "bãi đá", "bai da")):
        return [
            "Stonehenge ancient mystery drone 4k aerial view",
            "Stonehenge megaliths cinematic documentary 4k footage",
            "Ancient prehistoric monument 4k cinematic b-roll",
        ]

    # 10. Tam giác quỷ Bermuda
    if any(k in t_low for k in ("tam giác", "bermuda", "tam giac quy", "biển", "mất tích")):
        return [
            "Bermuda triangle mystery deep ocean storm 4k",
            "Ocean storm dark sea aerial 4k cinematic footage",
            "Deep ocean mysterious abyss documentary 4k b-roll",
        ]

    # 11. Lăng mộ Tần Thủy Hoàng
    if any(k in t_low for k in ("tần thủy hoàng", "tan thuy hoang", "lăng mộ", "terracotta")):
        return [
            "Terracotta army Qin Shi Huang tomb 4k cinematic documentary",
            "Ancient Chinese empire emperor tomb mystery 4k footage",
            "Ancient warriors archaeological discovery 4k b-roll",
        ]

    # 12. Thảm họa Titanic
    if any(k in t_low for k in ("titanic", "đắm tàu", "dam tau")):
        return [
            "Titanic shipwreck underwater deep ocean 4k documentary",
            "Titanic ship ocean liner wreckage 4k footage",
        ]

    # 13. Thảm họa hạt nhân Chernobyl
    if any(k in t_low for k in ("chernobyl", "hạt nhân", "phóng xạ")):
        return [
            "Chernobyl exclusion zone drone 4k cinematic footage",
            "Pripyat abandoned city disaster documentary 4k",
        ]

    # 14. Thủy chiến Bạch Đằng
    if any(k in t_low for k in ("bạch đằng", "bach dang", "thủy chiến", "thuyền")):
        return [
            "Ancient wooden warship river naval battle cinematic 4k",
            "Historical fleet sea battle documentary b-roll 4k",
            "Misty river aerial ancient landscape 4k drone",
        ]

    # 15. Khởi nguyên sự sống / Trái Đất sơ khai / Sinh học / Vi sinh vật
    if any(k in t_low for k in ("sự sống", "su song", "khởi nguyên", "khoi nguyen", "đầu tiên", "dau tien", "nguồn gốc sự sống", "trái đất sơ khai", "vi sinh", "tế bào")):
        return [
            "origin of life early earth documentary 4k",
            "ancient oceanic hydrothermal vents 4k discovery",
            "primordial earth volcanic landscape timelapse",
            "microscopic single cell organism origin of life",
        ]

    # 16. Khủng long / Thời tiền sử / Kỷ Jura / Tuyệt chủng
    if any(k in t_low for k in ("khủng long", "khung long", "dinosaur", "tiền sử", "tien su", "jura", "kỷ băng hà", "tuyệt chủng")):
        return [
            "dinosaur prehistoric earth documentary 4k footage",
            "prehistoric creatures ancient earth 4k b-roll",
            "jurassic prehistoric world cinematic 4k",
        ]

    # 17. Tiến hóa loài người / Khảo cổ học tiền sử
    if any(k in t_low for k in ("tiến hóa", "tien hoa", "loài người", "vượn người", "tổ tiên", "người tiền sử")):
        return [
            "human evolution anthropology documentary 4k footage",
            "early humans prehistoric ancestors documentary b-roll",
            "archaeological discovery human history 4k",
        ]

    # Mặc định an toàn: Tuyệt đối KHÔNG gộp chữ tiếng Việt không dấu (tránh tìm nhầm bài hát/vlog giải trí).
    # Trả về các từ khóa tài liệu khoa học/khám phá vũ trụ chuẩn để kết hợp với search_queries của LLM.
    return [
        "cinematic science documentary 4k footage",
        "earth history exploration 4k b-roll",
        "historical mystery discovery 4k drone view",
    ]


def _get_ytdlp_bin() -> str:
    """Tương thích ngược."""
    cmd = _get_ytdlp_cmd()
    return cmd[0]


def _slugify(text: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", text)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    return re.sub(r"[-\s]+", "_", s)


def _extract_narration(section: Dict[str, Any]) -> str:
    """Trích xuất lời đọc thuyết minh linh hoạt từ bất kỳ key nào mà LLM trả về (narration_vn, content, narration, text, script)."""
    if not isinstance(section, dict):
        return ""
    for k in ("narration_vn", "content", "narration", "text", "script", "voiceover", "subtitle_vn"):
        val = section.get(k)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _normalize_sections(sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Chuẩn hóa cấu trúc sections đảm bảo luôn có narration_vn, section_index và title."""
    out = []
    for idx, s in enumerate(sections, 1):
        if not isinstance(s, dict):
            continue
        text = _extract_narration(s)
        if not text:
            continue
        item = dict(s)
        item["narration_vn"] = text
        item["section_index"] = item.get("section_index") or item.get("id") or idx
        item["title"] = item.get("title") or f"Phân đoạn {idx}"
        out.append(item)
    return out


NARRATIVE_HOOK_STYLES = [
    {
        "name": "IN_MEDIA_RES (Hiện trường nghẹt thở)",
        "guide": "Mở đầu ngay tại hiện trường đỉnh điểm hoặc thời khắc bi kịch/chấn động nhất. Đưa ra mốc thời gian, tọa độ hoặc sự kiện cụ thể gây lạnh sống lưng.",
        "example": "Năm 1973, bên trong chiếc lồng thép vô trùng tại Maryland, cá thể sống cuối cùng của Universe 25 gục ngã. Không một vết thương, không một mầm bệnh. Nó chết vì một lý do khiến toàn bộ giới khoa học phải lạnh gáy.",
    },
    {
        "name": "DARK_PARADOX (Nghịch lý đen tối)",
        "guide": "Tạo sự tương phản tàn nhẫn giữa ước mơ hoàn hảo và thực tế hủy diệt. Đưa người xem từ cảm giác an toàn rơi thẳng vào vực thẳm.",
        "example": "Một thế giới không bệnh tật, không kẻ thù, thức ăn và nước uống vô tận. Nghe như thiên đường mơ ước của loài người, nhưng nửa thế kỷ trước, một thí nghiệm đã tạo ra nó — và biến nó thành bản án tuyệt chủng tàn bạo nhất lịch sử.",
    },
    {
        "name": "COLD_FACT_OVERWHELM (Dữ kiện chấn động)",
        "guide": "Đưa ra con số thực tế khổng lồ hoặc dữ kiện giải phẫu/địa chất gây choáng ngợp tâm trí, phá vỡ logic thông thường.",
        "example": "2 triệu 300 ngàn khối đá khổng lồ, mỗi khối nặng từ 2 đến 50 tấn được xếp chồng lên nhau với độ chính xác đến từng phần mười milimet. Nếu người xưa chỉ dùng búa đồng và dây thừng, thì đây không phải là công trình kiến trúc, mà là một phép màu vi phạm mọi định luật vật lý.",
    },
    {
        "name": "CHILLING_QUOTE (Trích dẫn rợn người)",
        "guide": "Mở đầu bằng một câu trích dẫn tài liệu mật, lời thú nhận hoặc dòng nhật ký tuyệt vọng của nhân chứng/nhà nghiên cứu.",
        "example": "'Chúng đã ngừng hành xử như một sinh vật sống từ rất lâu trước khi quả tim thực sự ngừng đập.' Dòng ghi chép tuyệt vọng của John Calhoun ở ngày thứ 560 đã báo hiệu hồi kết cho một đế chế từng được coi là hoàn hảo.",
    },
    {
        "name": "DIRECT_PSYCHOLOGICAL_MIRROR (Gương soi tâm lý)",
        "guide": "Tác động trực diện vào nỗi sợ hãi hoặc tâm lý ngầm của người xem, liên hệ trực tiếp tới xã hội và số phận con người hiện đại.",
        "example": "Hãy nhìn kỹ vào cuộc sống của chính chúng ta ngày hôm nay, bởi vì kịch bản kinh hoàng mà bạn sắp chứng kiến đã từng diễn ra với độ chính xác đến rợn người... và hồi kết của nó hoàn toàn không có chỗ cho sự cứu rỗi.",
    },
]


# =====================================================================
# 2. SOẠN KỊCH BẢN DÀI 3P - 5P VỚI LLM
# =====================================================================
def generate_broll_script(
    topic: str,
    duration_mins: float = 3.0,
    model: str = "auto",
) -> Dict[str, Any]:
    """
    LLM viết kịch bản tài liệu dài theo số phút yêu cầu:
    - 3 phút: ~400-420 từ, 10-12 phân đoạn
    - 5 phút: ~670-700 từ, 18-22 phân đoạn
    - Pacing tự nhiên: ~135 từ/phút (tốc độ chuẩn 1.15x giúp giọng đọc tròn vành rõ chữ, không bị méo tiếng).
    - Biến hóa phong cách mở màn (Hook) linh hoạt, loại bỏ hoàn toàn các câu sáo rỗng như "Bạn có biết...".
    """
    import random

    target_words = int(duration_mins * 135)
    num_sections = max(4, int(duration_mins * 3.5))
    chosen_hook = random.choice(NARRATIVE_HOOK_STYLES)

    system_instruction = (
        "Bạn là Đạo diễn kiêm Nhà biên kịch xuất sắc nhất về phim tài liệu điều tra, khoa học bí ẩn và lịch sử điện ảnh. "
        "Phong cách viết của bạn mang đậm tính điện ảnh (cinematic), nghẹt thở, sắc bén và sâu cay như các bộ phim tài liệu đoạt giải của HBO/Netflix. "
        "Bạn TUYỆT ĐỐI NÓI KHÔNG với sự sáo rỗng, buồn ngủ hay các khuôn mẫu rẻ tiền. "
        "Nhiệm vụ của bạn là soạn kịch bản chi tiết, đạt đúng thời lượng và số từ yêu cầu. "
        "Trả về DUY NHẤT 1 JSON Object tuân thủ schema."
    )

    prompt = f"""Hãy viết kịch bản phim tài liệu điện ảnh sâu sắc, giật gân và cuốn hút cho chủ đề sau:
CHỦ ĐỀ: "{topic}"

PHONG CÁCH MỞ MÀN (HOOK) YÊU CẦU CHO VIDEO NÀY:
👉 Thể loại Hook: {chosen_hook["name"]}
👉 Hướng dẫn triển khai: {chosen_hook["guide"]}
👉 Mẫu câu cảm hứng: "{chosen_hook["example"]}"

🚫 QUY TẮC CẤM TUYỆT ĐỐI (NEGATIVE CONSTRAINTS):
1. CẤM HOÀN TOÀN mở đầu bằng các câu hỏi sáo rỗng như:
   - "Bạn có biết..."
   - "Liệu bạn có từng..."
   - "Bạn đã bao giờ tự hỏi..."
   - "Hôm nay chúng ta cùng tìm hiểu..."
   - "Chào mừng các bạn đến với..."
2. CẤM đặt tiêu đề đơn điệu, nhạt nhẽo (ví dụ: "Bí mật bên dưới...", "Thí nghiệm...: Thiên đường chuột...").
   Tiêu đề (title) PHẢI mang tính giật gân, cuốn hút, kích thích trí tò mò tột độ.
   Ví dụ tiêu đề xuất sắc:
   • "Hồ sơ đen Universe 25: Khi sự no đủ biến thiên đường thành nấm mồ tập thể"
   • "Bản án diệt vong 560 ngày: Sự sụp đổ của một đế chế hoàn hảo"
   • "Bí ẩn rợn người đằng sau thí nghiệm Universe 25: Lời cảnh báo cho nhân loại"

YÊU CẦU THỜI LƯỢNG & ĐỘ DÀI:
- Thời lượng mục tiêu: {duration_mins:.1f} phút.
- Tốc độ đọc: 1.15x chuẩn tài liệu (~135 từ tiếng Việt/phút để người nghe thấm từng câu chữ, giọng đọc trầm ổn, uy lực).
- TỔNG SỐ TỪ TIẾNG VIỆT CẦN ĐẠT: Khoảng {target_words} từ (tối thiểu {int(target_words * 0.85)} từ).
- Số lượng phân đoạn (sections): {num_sections} phân đoạn liên hoàn, mỗi đoạn từ 35 đến 55 từ.

CẤU TRÚC KỊCH BẢN KỂ CHUYỆN ĐIỆN ẢNH:
1. Đoạn 1 (Hook 0:00 - 0:15): Áp dụng chuẩn xác phong cách '{chosen_hook["name"]}', giáng một đòn tâm lý mạnh mẽ vào người xem ngay giây đầu tiên.
2. Đoạn 2-4 (Bối cảnh & Dữ liệu chấn động): Đưa ra các mốc thời gian, nhân vật, tọa độ hoặc sự kiện mở đầu với các con số chính xác.
3. Đoạn 5-{num_sections - 3} (Bí ẩn & Sự tha hóa/Nghịch lý): Đi sâu vào các chi tiết kỳ dị, biến đổi hành vi, nghịch lý khoa học hoặc chứng cứ chấn động.
4. Đoạn {num_sections - 2}-{num_sections - 1} (Cao trào / Điểm uốn diệt vong): Khoảnh khắc sụp đổ không thể đảo ngược hoặc giả thuyết gây sốc nhất.
5. Đoạn cuối (Đúc kết & Câu chốt triết lý): Lời kết cảnh tỉnh sâu cay, liên hệ trực diện tới số phận của xã hội hiện đại khiến người xem phải suy ngẫm và tranh luận.

YÊU CẦU VỀ TÌM KIẾM B-ROLL FOOTAGE:
- Trong trường `broll_search_queries`: Hãy gợi ý 3 đến 5 cụm từ tìm kiếm video tư liệu bằng tiếng Anh (chất lượng cao 4K, b-roll, drone shot, cinematic timelapse) liên quan mật thiết đến chủ đề để hệ thống tự động tải footage minh họa trên YouTube.
"""

    print(f"\n[B-Roll Director] Đang yêu cầu LLM soạn kịch bản {duration_mins:.1f} phút (~{target_words} từ, {num_sections} phân đoạn)...")
    print(f"🎬 Phong cách dẫn chuyện (Hook): {chosen_hook['name']}")
    result = call_gemini_thinking_structured(
        prompt=prompt,
        response_schema=BROLL_SCRIPT_SCHEMA,
        system_instruction=system_instruction,
    )

    if not result or not result.get("sections"):
        print("[B-Roll Director] LLM trả về rỗng -> Sử dụng bộ kịch bản dự phòng chất lượng cao.")
        result = _fallback_script(topic, duration_mins)

    # Chuẩn hóa linh hoạt mọi cấu trúc section (narration_vn / content / text)
    sections = _normalize_sections(result.get("sections", []))
    if not sections:
        result = _fallback_script(topic, duration_mins)
        sections = _normalize_sections(result.get("sections", []))

    result["sections"] = sections
    total_words = sum(len(s.get("narration_vn", "").split()) for s in sections)
    result["actual_word_count"] = total_words

    print(f"✅ Kịch bản đã sẵn sàng: \"{result.get('title')}\"")
    print(f"   • Số phân đoạn : {len(sections)}")
    print(f"   • Tổng số từ   : {total_words} từ (Mục tiêu: {target_words} từ)")
    print(f"   • Từ khóa B-roll: {result.get('broll_search_queries', [])[:3]}")

    return result


def _fallback_script(topic: str, duration_mins: float) -> Dict[str, Any]:
    """Kịch bản dự phòng khi offline hoặc LLM nghẽn mạng."""
    clean_title = topic.strip()
    # Nếu là chủ đề Lăng mộ Tần Thủy Hoàng và có file kịch bản 3 phút chuẩn sâu sắc
    tth_script_file = Path(WORKSPACE_DIR) / "script_tan_thuy_hoang_3min.json"
    if any(k in clean_title.lower() for k in ("tần thủy hoàng", "tan thuy hoang", "tomb of qin")) and tth_script_file.exists():
        try:
            return json.loads(tth_script_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    en_queries = _translate_topic_to_english_queries(clean_title)

    return {
        "title": f"Hồ sơ tuyệt mật: {clean_title} và sự thật chấn động",
        "topic_summary_vn": f"Giải mã toàn cảnh những nghịch lý và bí mật kỳ lạ nhất về {clean_title}.",
        "duration_mins": duration_mins,
        "target_word_count": int(duration_mins * 135),
        "broll_search_queries": en_queries,
        "sections": [
            {
                "section_index": 1,
                "title": "Thời khắc bí ẩn",
                "narration_vn": f"Bên dưới lớp bụi mờ của thời gian, {clean_title} vẫn là một trong những hồ sơ bí ẩn nhất từng thách thức nhận thức của nhân loại. Mọi dữ liệu để lại đều dẫn tới một nghịch lý không lời giải đáp.",
                "visual_mood": "Cinematic slow aerial shot approaching the subject",
            },
            {
                "section_index": 2,
                "title": "Những dấu vết lịch sử",
                "narration_vn": f"Hồ sơ thực địa ghi nhận những chi tiết kỳ dị về {clean_title}, nơi mọi quy luật vật lý và tâm lý thông thường dường như bị bẻ cong hoàn toàn.",
                "visual_mood": "Ancient maps and close up details of old manuscripts",
            },
            {
                "section_index": 3,
                "title": "Nghịch lý khoa học",
                "narration_vn": "Khoa học hiện đại đã vào cuộc với những thiết bị tối tân nhất, nhưng càng đào sâu, các chuyên gia lại càng bối rối trước những hiện tượng dị thường không thể giải thích.",
                "visual_mood": "Modern scientific lab scans and 3D wireframe reconstruction",
            },
            {
                "section_index": 4,
                "title": "Lời cảnh tỉnh",
                "narration_vn": f"Cho đến ngày hôm nay, bức màn bao phủ {clean_title} vẫn là lời thách thức cho tương lai. Liệu nhân loại đã sẵn sàng đối mặt với câu trả lời thực sự?",
                "visual_mood": "Dramatic sunset over horizon with silhouette",
            },
        ],
    }


# =====================================================================
# 3. TỰ ĐỘNG TÌM & TẢI VIDEO B-ROLL (HOẶC NHẬN FOOTAGE CÓ SẴN)
# =====================================================================
def _generate_fallback_topic_broll(
    topic_text: str,
    footage_dir: Path,
    aspect_ratio: str = "9:16",
    count: int = 4,
) -> List[Path]:
    """Tự động sinh footage B-roll điện ảnh HD chuẩn 100% theo đúng chủ đề khi YouTube/yt-dlp gặp sự cố mạng."""
    print(f"\n🎨 [B-Roll Studio] Đang tự động kiến tạo video tư liệu điện ảnh HD đúng chuẩn chủ đề '{topic_text}'...")
    import requests
    import urllib.parse

    ff = _get_ffmpeg_bin()
    target_w, target_h = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)
    generated_clips: List[Path] = []

    en_queries = _translate_topic_to_english_queries(topic_text)
    base_terms = [q for q in en_queries if q.strip()]
    if not base_terms:
        base_terms = [topic_text]

    prompts = [
        f"{base_terms[0]}, photorealistic documentary photography, cinematic lighting, 8k, National Geographic style, no text, no watermark",
        f"{base_terms[min(1, len(base_terms)-1)]}, detailed close up shot, dramatic shadows, mysterious atmosphere, highly detailed documentary, 4k",
        f"{base_terms[min(2, len(base_terms)-1)]}, cinematic establishing wide shot, moody dark atmospheric lighting, documentary archival footage, 4k",
        f"{base_terms[0]}, high contrast cinematic scene, anamorphic lens, realistic historical documentary, 8k sharp",
    ]

    for idx, prompt_text in enumerate(prompts[:count], 1):
        try:
            encoded_p = urllib.parse.quote(prompt_text)
            img_url = f"https://image.pollinations.ai/prompt/{encoded_p}?width={target_w}&height={target_h}&model=flux&nologo=true&seed={idx * 311}"
            img_path = footage_dir / f"broll_topic_{idx}.jpg"
            vid_path = footage_dir / f"broll_topic_{idx}.mp4"

            resp = requests.get(img_url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200 and len(resp.content) > 15000:
                img_path.write_bytes(resp.content)
                # Dùng FFmpeg tạo video chuyển động zoom/pan 6.5s mượt mà
                zoom_expr = "min(zoom+0.0012,1.20)" if idx % 2 == 1 else "max(1.20-0.0012*on,1.0)"
                vf = (
                    f"zoompan=z='{zoom_expr}':d=195:s={target_w}x{target_h}:fps=30,"
                    f"scale={target_w}:{target_h},setsar=1"
                )
                cmd = [
                    ff, "-y", "-loop", "1", "-i", str(img_path),
                    "-vf", vf,
                    "-c:v", "libx264", "-t", "6.5", "-pix_fmt", "yuv420p",
                    "-preset", "ultrafast",
                    str(vid_path),
                ]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if res.returncode == 0 and vid_path.exists():
                    generated_clips.append(vid_path)
                    print(f"   ├─ ✅ Tạo thành công footage điện ảnh #{idx}: {vid_path.name}")
        except Exception as e:
            continue

    return generated_clips


_JUNK_TITLE_WORDS = [
    "mv", "official mv", "music video", "video music", "official audio", "karaoke",
    "lyrics", "lyric", "remix", "cover", "dance", "choreography", "gameplay",
    "walkthrough", "vlog", "reaction", "unboxing", "tiktok", "hài kịch", "hài tết",
    "parody", "prank", "bolero", "mashup", "phim ngắn", "tập ", "vietsub", "nhạc trẻ",
    "nhạc vàng", "nhạc sống", "tóm tắt phim", "review phim", "mukbang"
]

_DOC_BADGES = {
    "documentary", "history", "ancient", "science", "universe", "space", "earth",
    "nature", "wildlife", "exploration", "geology", "archaeology", "timelapse",
    "b-roll", "footage", "4k", "cinematic", "mystery", "discovery", "national geographic",
    "bbc", "pbs", "origin", "evolution", "prehistoric", "tài liệu", "khám phá", "lịch sử",
    "khoa học", "bí ẩn", "vũ trụ", "hydrothermal", "organism", "cell", "magma"
}


def _is_title_junk(title: str) -> bool:
    """Kiểm tra xem tiêu đề có phải video giải trí rác / ca nhạc / gameplay không."""
    t_low = title.lower()
    for w in _JUNK_TITLE_WORDS:
        if re.search(r"\b" + re.escape(w) + r"\b", t_low) or w in t_low:
            return True
    return False


def _is_title_topic_relevant(title: str, query: str) -> bool:
    """Xác minh tiêu đề video thực sự thuộc thể loại tư liệu/khoa học/lịch sử và khớp chủ đề."""
    if _is_title_junk(title):
        return False
    t_low = title.lower()
    if any(b in t_low for b in _DOC_BADGES):
        return True
    q_words = [w for w in re.findall(r"\b[a-zA-Z]{3,}\b", query.lower()) if w not in ("and", "the", "for", "with", "video", "footage", "drone", "4k", "broll")]
    matched = sum(1 for w in q_words if w in t_low)
    return matched >= 1


def fetch_broll_footage(
    search_queries: List[str],
    run_dir: Path,
    custom_footage: Optional[str] = None,
    min_total_duration_sec: float = 60.0,
    topic: str = "",
    aspect_ratio: str = "9:16",
) -> List[Path]:
    """
    Tự động tìm kiếm và tải B-roll video:
    1. Nếu người dùng chỉ định `--footage <file_hoặc_thư_mục>` -> Sử dụng trực tiếp video của người dùng.
    2. Nếu không chỉ định -> Tự động dùng `yt-dlp` tìm kiếm theo queries tiếng Anh chuẩn của LLM kịch bản.
       - KIỂM DUYỆT TIÊU ĐỀ: Loại bỏ 100% video ca nhạc, vlog, gameplay, giải trí rác không liên quan.
       - Chỉ tải những video được xác nhận là phim tài liệu/khoa học/lịch sử đúng chủ đề.
    3. Nếu YouTube nghẽn mạng hoặc không có video phù hợp -> Tự động kiến tạo footage điện ảnh HD đúng 100% chủ đề bằng AI Generator.
    """
    footage_dir = run_dir / "footage"
    footage_dir.mkdir(parents=True, exist_ok=True)
    valid_exts = {".mp4", ".mov", ".webm", ".mkv"}

    # Trường hợp 1: Người dùng tự cung cấp video
    if custom_footage:
        p = Path(custom_footage)
        if p.is_file() and p.suffix.lower() in valid_exts:
            dst = footage_dir / p.name
            if not dst.exists():
                try:
                    dst.symlink_to(p.resolve())
                except Exception:
                    shutil.copy2(p, dst)
            print(f"🎬 [B-Roll Footage] Sử dụng video do bạn cung cấp: {p.name}")
            return [dst]
        elif p.is_dir():
            found = [f for f in p.iterdir() if f.is_file() and f.suffix.lower() in valid_exts]
            if found:
                print(f"🎬 [B-Roll Footage] Tìm thấy {len(found)} video từ thư mục: {p}")
                return found

    # Kiểm tra xem trong footage_dir đã có video YouTube hợp lệ sẵn chưa (tránh tải lại trùng lặp)
    existing_videos = [
        f for f in footage_dir.iterdir()
        if f.is_file() and f.suffix.lower() in valid_exts
        and f.stat().st_size > 500_000
        and not f.name.startswith("broll_topic_")
    ]
    if len(existing_videos) >= 2:
        print(f"🎬 [B-Roll Auto-Fetch] Sử dụng {len(existing_videos)} video tư liệu thực tế có sẵn:")
        for ev in existing_videos:
            print(f"   ├─ Video: {ev.name} ({ev.stat().st_size / (1024*1024):.1f} MB)")
        return existing_videos

    # Trường hợp 2: Tự động tìm kiếm & tải qua yt-dlp
    ytdlp_cmd = _get_ytdlp_cmd()
    ff_bin = _get_ffmpeg_bin()
    downloaded_files: List[Path] = list(existing_videos)
    print(f"\n🔍 [B-Roll Auto-Fetch] Hệ thống tự động tìm và kiểm duyệt video tư liệu đúng chủ đề qua yt-dlp...")

    # ƯU TIÊN SỐ 1: Các từ khóa tiếng Anh chuyên sâu do LLM biên kịch tạo ra
    combined_queries: List[str] = []
    topic_text = (topic or "").strip()
    if not topic_text:
        topic_text = run_dir.name.replace("broll_", "").rsplit("_", 2)[0].replace("_", " ")

    for q in search_queries:
        if q and q.strip() and q.strip() not in combined_queries:
            combined_queries.append(q.strip())

    # ƯU TIÊN SỐ 2: Ánh xạ chuẩn từ điển theo chủ đề
    for en_q in _translate_topic_to_english_queries(topic_text):
        if en_q not in combined_queries:
            combined_queries.append(en_q)

    for query in combined_queries[:4]:
        clean_q = query.strip()
        if not clean_q:
            continue
        print(f"   ├─ Đang tìm kiếm: \"{clean_q}\"...")

        # BƯỚC A: Quét nhanh metadata (ID, Tiêu đề, Thời lượng) để lọc rác trước khi tải
        cand_list: List[Dict[str, Any]] = []
        search_cmd = [
            *ytdlp_cmd,
            "--flat-playlist",
            "--print", "%(id)s\t%(title)s\t%(duration)s",
            f"ytsearch6:{clean_q}",
        ]
        try:
            res_meta = subprocess.run(search_cmd, capture_output=True, text=True, timeout=25)
            if res_meta.returncode == 0 and res_meta.stdout.strip():
                for line in res_meta.stdout.splitlines():
                    parts = line.strip().split("\t")
                    if len(parts) >= 2:
                        vid_id = parts[0].strip()
                        vid_title = parts[1].strip()
                        vid_dur = 0.0
                        if len(parts) >= 3:
                            try:
                                vid_dur = float(parts[2])
                            except Exception:
                                pass
                        cand_list.append({"id": vid_id, "title": vid_title, "duration": vid_dur})
        except Exception:
            pass

        # BƯỚC B: Kiểm duyệt chất lượng & độ liên quan của tiêu đề
        valid_candidates: List[Dict[str, Any]] = []
        for cand in cand_list:
            v_id = cand["id"]
            v_title = cand["title"]
            v_dur = cand["duration"]
            if v_dur > 0 and (v_dur < 25 or v_dur > 1800):
                continue
            if not _is_title_topic_relevant(v_title, clean_q):
                print(f"   │  └─ ⚠️ Bỏ qua video không liên quan (ca nhạc/vlog/game): \"{v_title[:55]}...\"")
                continue
            valid_candidates.append(cand)

        # BƯỚC C: Tải video đã được kiểm duyệt chuẩn 100%
        if valid_candidates:
            for cand in valid_candidates[:1]:  # Lấy 1 video chất lượng nhất mỗi query
                vid_id = cand["id"]
                vid_title = cand["title"]
                out_path = footage_dir / f"broll_{vid_id}.mp4"
                if out_path.exists() and out_path.stat().st_size > 500_000:
                    if out_path not in downloaded_files:
                        downloaded_files.append(out_path)
                    continue

                dl_cmd = [
                    *ytdlp_cmd,
                    "--no-playlist",
                    "--extractor-args", "youtube:player_client=android",
                    "--download-sections", "*00:08-01:30",
                    "--max-filesize", "45M",
                    "--socket-timeout", "15",
                    "-f", "b[height<=720]/best[height<=720]/bv[height<=720]+ba/b",
                    "--merge-output-format", "mp4",
                    "--ffmpeg-location", ff_bin,
                    "--output", str(footage_dir / f"broll_%(id)s.%(ext)s"),
                    f"https://www.youtube.com/watch?v={vid_id}",
                ]
                try:
                    res_dl = subprocess.run(dl_cmd, capture_output=True, text=True, timeout=50)
                    for f in footage_dir.iterdir():
                        if f.is_file() and f.suffix.lower() in valid_exts and f.stat().st_size > 500_000:
                            if not f.name.startswith("broll_topic_") and f not in downloaded_files:
                                downloaded_files.append(f)
                                print(f"   │  └─ ✅ Đã duyệt & tải B-Roll chuẩn chủ đề: \"{vid_title[:50]}\" ({f.stat().st_size / (1024*1024):.1f} MB)")
                except Exception as e:
                    print(f"   │  └─ yt-dlp bỏ qua ({e})")
        else:
            # Fallback nếu flat-playlist không ra kết quả: dùng regex match-filter loại bỏ triệt để video ca nhạc/giải trí
            out_template = str(footage_dir / f"broll_%(id)s.%(ext)s")
            cmd = [
                *ytdlp_cmd,
                "--no-playlist",
                "--extractor-args", "youtube:player_client=android",
                "--match-filter", "!is_live & title !~* '(?i)(official\\s*mv|music\\s*video|karaoke|lyrics|remix|cover|dance|vlog|gameplay)'",
                "--download-sections", "*00:08-01:30",
                "--max-filesize", "45M",
                "--socket-timeout", "15",
                "-f", "b[height<=720]/best[height<=720]/bv[height<=720]+ba/b",
                "--merge-output-format", "mp4",
                "--ffmpeg-location", ff_bin,
                "--max-downloads", "1",
                "--output", out_template,
                f"ytsearch1:{clean_q}",
            ]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=50)
                for f in footage_dir.iterdir():
                    if f.is_file() and f.suffix.lower() in valid_exts and f.stat().st_size > 500_000:
                        if not f.name.startswith("broll_topic_") and f not in downloaded_files:
                            downloaded_files.append(f)
                            print(f"   │  └─ Tải thành công video: {f.name} ({f.stat().st_size / (1024*1024):.1f} MB)")
            except Exception as e:
                pass

        if len(downloaded_files) >= 2:
            break

    if downloaded_files:
        print(f"🎬 [B-Roll Auto-Fetch] Đã sẵn sàng {len(downloaded_files)} video tư liệu thực tế.")
        return downloaded_files

    # Trường hợp 3: Dự phòng các video sẵn có trong workspace/footage_{topic}
    ws_dir = run_dir.parent
    safe_topic_slug = _slugify(topic_text)[:20]
    ref_candidates = [
        ws_dir / f"footage_{safe_topic_slug}",
        ws_dir / "footage" / safe_topic_slug,
    ]
    for cand in ref_candidates:
        if cand.is_dir():
            found = [f for f in cand.iterdir() if f.is_file() and f.suffix.lower() in valid_exts]
            if found:
                print(f"🎬 [B-Roll Auto-Fetch] Sử dụng video từ thư mục tư liệu đúng chủ đề: {cand}")
                return found

    # Trường hợp 4: Tự động kiến tạo footage B-roll điện ảnh HD bằng AI đúng 100% chủ đề
    fallback_clips = _generate_fallback_topic_broll(topic_text, footage_dir, aspect_ratio=aspect_ratio, count=4)
    if fallback_clips:
        return fallback_clips

    raise RuntimeError(
        f"Không thể tải video B-roll phù hợp cho chủ đề '{topic_text}' qua yt-dlp (hãy kiểm tra kết nối mạng). "
        f"Hoặc bạn có thể tự thả video vào lệnh qua tham số: --footage <đường_dẫn_video_hoặc_thư_mục>."
    )


# =====================================================================
# 4. THU ÂM & PHỤ ĐỀ ĐỒNG BỘ CHÍNH XÁC
# =====================================================================
def synthesize_broll_narration(
    sections: List[Dict[str, Any]],
    run_dir: Path,
    voice_name: str = "vanthanhthu",
    speed_rate: float = 1.15,
    music_mood: str = "cinematic_mystery_suspense",
) -> Tuple[Path, List[Tuple[float, float]], float]:
    """
    Sinh file audio thuyết minh hoàn chỉnh từ danh sách các sections:
    - Trả về đường dẫn file `.wav`, mốc thời gian từng đoạn `(start, end)`, và tổng thời lượng audio.
    - Nhạc nền huyền bí được tự động hạ âm lượng (auto-ducking) khi có tiếng thuyết minh.
    """
    wav_path = run_dir / "voiceover_studio.wav"
    scene_texts = [_extract_narration(s) for s in sections if _extract_narration(s)]

    # Với giọng Clone, đặt tốc độ 0.68x để bù lại nhịp nói rất nhanh của file mẫu, giúp giọng trầm tĩnh, rõ chữ, chuẩn phim tài liệu (không bị tua nhanh)
    if voice_name.lower().strip() in ("clone", "f5tts", "offline_clone"):
        speed_rate = 0.68

    print(f"\n🎙️ [B-Roll Audio] Đang lồng tiếng {len(scene_texts)} phân đoạn (Giọng: {voice_name}, Tốc độ: {speed_rate}x)...")
    out_wav, timings = synthesize_scene_voiceover(
        scene_texts=scene_texts,
        output_filename=wav_path,
        voice_name=voice_name,
        speed_rate=speed_rate,
        music_mood=music_mood,
    )

    # Đo độ dài file WAV thực tế
    total_audio_sec = timings[-1][1] if timings else 0.0
    if total_audio_sec <= 0:
        import scipy.io.wavfile as wavfile
        sr, d = wavfile.read(str(out_wav))
        total_audio_sec = round(len(d) / float(sr), 2)

    print(f"✅ Thu âm hoàn tất: {total_audio_sec:.1f} giây (~{total_audio_sec/60:.2f} phút)")
    for i, (st, en) in enumerate(timings[:5]):
        print(f"   ├─ Đoạn {i+1:02d} [{st:.1f}s -> {en:.1f}s]: {scene_texts[i][:45]}...")
    if len(timings) > 5:
        print(f"   └─ ... và {len(timings) - 5} đoạn tiếp theo cho đến {total_audio_sec:.1f}s")

    return out_wav, timings, total_audio_sec


# =====================================================================
# 5. DỰNG PHIM THÔNG MINH: CẮT & GHÉP B-ROLL THEO NHỊP 3s - 5s
# =====================================================================
def _get_video_duration(video_path: Path) -> float:
    """Lấy thời lượng video bằng ffprobe/ffmpeg."""
    ff = _get_ffmpeg_bin()
    cmd = [
        ff, "-i", str(video_path),
    ]
    res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
    if m:
        hours, mins, secs = float(m.group(1)), float(m.group(2)), float(m.group(3))
        return hours * 3600 + mins * 60 + secs
    return 60.0


def _is_cut_usable(cut_path: Path, min_brightness: float = 12.0) -> bool:
    """
    Kiểm duyệt chất lượng hình ảnh của đoạn cắt:
    - Bỏ qua các đoạn cắt hỏng hoặc màn hình đen ngòm (độ sáng trung bình < min_brightness).
    """
    ff = _get_ffmpeg_bin()
    cmd = [
        ff, "-ss", "0.5", "-i", str(cut_path),
        "-vframes", "1", "-f", "image2pipe",
        "-vcodec", "rawvideo", "-pix_fmt", "gray", "-"
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        if not res.stdout:
            return False
        raw_bytes = res.stdout
        avg = sum(raw_bytes) / float(len(raw_bytes))
        if avg < min_brightness:
            return False
        return True
    except Exception:
        return True
    except Exception:
        return True


def assemble_broll_video(
    footage_files: List[Path],
    total_duration_sec: float,
    run_dir: Path,
    aspect_ratio: str = "9:16",
    shot_duration: float = 4.0,
) -> Path:
    """
    Cắt và đan xen các đoạn B-roll 3s - 5s để phủ kín toàn bộ thời lượng audio.
    - Chuẩn hóa về độ phân giải yêu cầu:
      + 9:16: 1080x1920 (TikTok/Shorts/Reels)
      + 16:9: 1920x1080 (YouTube/Facebook)
    """
    ff = _get_ffmpeg_bin()
    target_w, target_h = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)
    merged_output = run_dir / "raw_visual_merged.mp4"

    cuts_dir = run_dir / "cuts"
    cuts_dir.mkdir(parents=True, exist_ok=True)

    # Thu thập thời lượng từng video nguồn
    footage_info: List[Dict[str, Any]] = []
    for fp in footage_files:
        dur = _get_video_duration(fp)
        footage_info.append({"path": fp, "duration": dur})

    print(f"\n🎬 [B-Roll Video Assembler] Đang cắt ghép B-roll phủ kín {total_duration_sec:.1f}s (Khổ {aspect_ratio}: {target_w}x{target_h})...")

    # Tạo danh sách các cut
    current_time = 0.0
    shot_index = 0
    cut_files: List[Path] = []

    while current_time < total_duration_sec:
        rem = total_duration_sec - current_time
        curr_shot_dur = min(shot_duration, rem)
        if curr_shot_dur < 0.5:
            break

        # Chọn video nguồn luân phiên
        src_meta = footage_info[shot_index % len(footage_info)]
        src_path = src_meta["path"]
        src_dur = max(curr_shot_dur + 1.0, src_meta["duration"])

        # Tính start time trong video nguồn để lấy các đoạn khác nhau (không lặp một chỗ)
        # Sử dụng bước nhảy so le (stride)
        stride = 6.5
        start_sec = ((shot_index * stride) % max(1.0, (src_dur - curr_shot_dur - 1.0)))
        # Bỏ qua 2s đầu để tránh màn đen hoặc tiêu đề
        start_sec = max(2.0, start_sec)

        cut_filename = cuts_dir / f"cut_{shot_index:04d}.mp4"

        # Bộ lọc scale & crop chuyển sang 9:16 hoặc 16:9 sắc nét
        vf = (
            f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
            f"crop={target_w}:{target_h},setsar=1,fps={VIDEO_FPS}"
        )

        cut_ok = False
        attempt_start = start_sec
        for attempt in range(5):
            cmd = [
                ff, "-y",
                "-ss", f"{attempt_start:.2f}",
                "-t", f"{curr_shot_dur:.2f}",
                "-i", str(src_path),
                "-vf", vf,
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "22",
                "-an",
                str(cut_filename),
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode == 0 and cut_filename.exists() and _is_cut_usable(cut_filename):
                cut_ok = True
                break
            # Nếu đoạn cắt bị đen hoặc lỗi, nhảy tới 4.5s tiếp theo để tìm khung hình sáng đẹp
            attempt_start += 4.5
            if attempt_start > (src_dur - curr_shot_dur - 1.0):
                attempt_start = 3.0

        if cut_ok:
            cut_files.append(cut_filename)
            current_time += curr_shot_dur
            shot_index += 1
        else:
            shot_index += 1
            continue

    print(f"   ├─ Đã tạo {len(cut_files)} phân đoạn B-roll liên tiếp.")

    # Ghép tất cả các cuts bằng concat demuxer
    concat_list_file = run_dir / "concat_list.txt"
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for cf in cut_files:
            f.write(f"file '{cf.resolve()}'\n")

    print("   ├─ Đang kết nối các phân đoạn thành luồng video hoàn chỉnh...")
    concat_cmd = [
        ff, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_file),
        "-c", "copy",
        str(merged_output),
    ]
    res_concat = subprocess.run(concat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res_concat.returncode != 0 or not merged_output.exists():
        # Fallback encode lại
        fallback_cmd = [
            ff, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list_file),
            "-c:v", "libx264",
            "-preset", "veryfast",
            str(merged_output),
        ]
        subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    print(f"✅ Video B-roll thô đã dựng xong: {merged_output.name} ({current_time:.1f}s)")
    return merged_output


# =====================================================================
# 6. TẠO PHỤ ĐỀ ASS CHUẨN TIKTOK & RENDER FINAL MASTER
# =====================================================================
def build_broll_ass_subtitles(
    sections: List[Dict[str, Any]],
    timings: List[Tuple[float, float]],
    target_w: int,
    target_h: int,
    title: str,
    sub_style: str = "tiktok_yellow",
) -> str:
    """Tạo file subtitle .ass chuyên nghiệp cho TikTok."""
    font_size = int(target_h * 0.048)  # ~92px cho 1920h
    outline_px = max(4, target_h // 280)
    shadow_px = 2
    margin_v = int(target_h * 0.22)  # TikTok Safe Zone: cách đáy 420px tránh nút like/share & caption

    # Màu sắc BGR trong ASS format
    primary_color = "&H0000E5FF" if sub_style == "tiktok_yellow" else "&H00FFFFFF"  # Vàng rực
    secondary_color = "&H00FFFFFF"
    outline_color = "&H00000000"  # Viền đen

    lines = [
        "[Script Info]",
        f"Title: {title}",
        "ScriptType: v4.00+",
        f"PlayResX: {target_w}",
        f"PlayResY: {target_h}",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,Arial,{font_size},{primary_color},{secondary_color},{outline_color},&H90000000,-1,0,0,0,100,100,0,0,1,{outline_px},{shadow_px},2,60,60,{margin_v},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    def _fmt(sec: float) -> str:
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        cs = int(round((sec - int(sec)) * 100))
        if cs >= 100:
            cs = 99
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    for i, sec_item in enumerate(sections):
        if i >= len(timings):
            break
        st, en = timings[i]
        text = _extract_narration(sec_item)

        # Chia câu dài thành các cụm 6-8 từ dễ đọc trên điện thoại
        words = text.split()
        if len(words) <= 9:
            lines.append(f"Dialogue: 0,{_fmt(st)},{_fmt(en)},Default,,0,0,0,,{text}")
        else:
            # Chia đôi hoặc chia 3
            chunk_size = 7
            sub_chunks = [words[k:k+chunk_size] for k in range(0, len(words), chunk_size)]
            dur_per_chunk = (en - st) / len(sub_chunks)
            c_start = st
            for ch in sub_chunks:
                c_end = min(en, c_start + dur_per_chunk)
                sub_text = " ".join(ch)
                lines.append(f"Dialogue: 0,{_fmt(c_start)},{_fmt(c_end)},Default,,0,0,0,,{sub_text}")
                c_start = c_end

    return "\n".join(lines)


def render_final_master_video(
    video_path: Path,
    wav_path: Path,
    sections: List[Dict[str, Any]],
    timings: List[Tuple[float, float]],
    run_dir: Path,
    aspect_ratio: str = "9:16",
    sub_style: str = "none",
) -> Path:
    """Mux video, audio và burn subtitles thành final_master.mp4."""
    ff = _get_ffmpeg_bin()
    target_w, target_h = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)
    final_output = run_dir / "final_master.mp4"

    has_subs = bool(sections and timings and sub_style not in ("none", "off", "no_sub", "no-sub", "", "karaoke_off"))
    sub_filter = ""
    if has_subs:
        # 1. Xuất file phụ đề .ass
        ass_content = build_broll_ass_subtitles(
            sections=sections,
            timings=timings,
            target_w=target_w,
            target_h=target_h,
            title=sections[0].get("title", "Video"),
            sub_style=sub_style,
        )
        ass_path = run_dir / "subtitles.ass"
        ass_path.write_text(ass_content, encoding="utf-8")
        sub_filter = f"ass='{ass_path.name}'"
        print(f"\n🎨 [B-Roll Render] Đang hoàn thiện Master Video 1080p và ép phụ đề {sub_style}...")
    else:
        print("\n🎨 [B-Roll Render] Đang ghép luồng video B-Roll với âm thanh gốc 1080p...")

    vf_args = ["-vf", f"{sub_filter},format=yuv420p"] if sub_filter else []

    cmd = [
        ff, "-y",
        "-i", str(video_path),
        "-i", str(wav_path),
        *vf_args,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "19",
        "-pix_fmt", "yuv420p",
        "-r", str(VIDEO_FPS),
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-shortest",
        str(final_output),
    ]

    res = subprocess.run(cmd, cwd=str(run_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        cmd_no_sub = [
            ff, "-y",
            "-i", str(video_path),
            "-i", str(wav_path),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(final_output),
        ]
        subprocess.run(cmd_no_sub, cwd=str(run_dir), check=True)

    print(f"🎉 MASTER VIDEO ĐÃ HOÀN TẤT: {final_output.resolve()} ({final_output.stat().st_size / (1024*1024):.1f} MB)")
    return final_output


# =====================================================================
# 7. HÀM CHÍNH ĐIỀU PHỐI (LINEAR PIPELINE — ZERO GRAPH LIBRARIES)
# =====================================================================
def run_broll_pipeline(
    topic: str,
    duration_mins: float = 3.0,
    footage: Optional[str] = None,
    audio: Optional[str] = None,
    voice: str = "vanthanhthu",
    speed: float = 1.15,
    aspect_ratio: str = "9:16",
    sub_style: str = "none",
    output_dir: Optional[str] = None,
    script_file: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Điểm vào duy nhất cho chế độ B-Roll (Cắt video có sẵn/tự lấy + ghép Audio 3-5 phút + Subtitles).
    Hoàn toàn thuần Python tuyến tính, không dùng bất kỳ thư viện vẽ đồ thị hay DAG nào.
    - Hỗ trợ `--audio <file_video_hoặc_audio>`: Sử dụng trực tiếp giọng đọc từ video tham chiếu (như tiktok_ref.mp4).
    """
    ts = time.strftime("%m%d_%H%M%S")
    slug = _slugify(topic or "ref_audio")[:32]
    run_name = f"broll_{slug}_{ts}"

    run_dir = Path(output_dir) if output_dir else Path(WORKSPACE_DIR) / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 96)
    print(f"🚀 BẮT ĐẦU CHẾ ĐỘ B-ROLL (ZERO GRAPH LIBRARIES)")
    print(f"📌 Chủ đề      : {topic or '(Sử dụng âm thanh tham chiếu có sẵn)'}")
    if audio:
        print(f"🎙️ Âm thanh gốc: {audio}")
    else:
        print(f"⏱️  Thời lượng  : {duration_mins:.1f} phút")
    print(f"📁 Thư mục xuất: {run_dir.resolve()}")
    print("=" * 96)

    sections: List[Dict[str, Any]] = []
    timings: List[Tuple[float, float]] = []

    # TRƯỜNG HỢP A: Người dùng cung cấp trực tiếp file Audio/Video tham chiếu (như tiktok_ref.mp4)
    if audio:
        p_audio = Path(audio)
        if not p_audio.exists():
            raise FileNotFoundError(f"Không tìm thấy file audio/video: {audio}")
        wav_path = run_dir / "voiceover_studio.wav"
        ff = _get_ffmpeg_bin()
        print(f"\n🎙️ [B-Roll Audio] Đang trích xuất toàn bộ âm thanh từ: {p_audio.name}...")
        cmd_extract = [
            ff, "-y",
            "-i", str(p_audio),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "44100",
            "-ac", "1",
            str(wav_path),
        ]
        subprocess.run(cmd_extract, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        total_audio_sec = _get_video_duration(wav_path)
        print(f"✅ Đã trích xuất âm thanh: {total_audio_sec:.1f}s (~{total_audio_sec/60:.2f} phút)")

        # Tạo từ khóa tìm kiếm B-roll
        broll_query_topic = topic or p_audio.stem.replace("tiktok_ref", "stonehenge mystery")
        queries = [
            f"{broll_query_topic} 4k cinematic documentary b-roll",
            f"{broll_query_topic} aerial drone 4k footage",
            "ancient mysteries history documentary footage 4k",
        ]
        script_data = {
            "title": topic or p_audio.stem,
            "broll_search_queries": queries,
            "sections": [],
        }

    # TRƯỜNG HỢP B: LLM soạn kịch bản và sinh giọng đọc AI theo số phút yêu cầu
    else:
        # BƯỚC 1: LLM soạn kịch bản dài phù hợp số phút yêu cầu (hoặc lấy từ script_file)
        if script_file and Path(script_file).exists():
            print(f"\n📋 [B-Roll Director] Nạp kịch bản 3-5 phút từ file: {script_file}")
            script_data = json.loads(Path(script_file).read_text(encoding="utf-8"))
        else:
            script_data = generate_broll_script(
                topic=topic,
                duration_mins=duration_mins,
            )
        (run_dir / "broll_script.json").write_text(
            json.dumps(script_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # BƯỚC 2: Thu âm thuyết minh & nhạc nền auto-ducking
        sections = script_data.get("sections", [])
        wav_path, timings, total_audio_sec = synthesize_broll_narration(
            sections=sections,
            run_dir=run_dir,
            voice_name=voice,
            speed_rate=speed,
        )
        queries = script_data.get("broll_search_queries", [])

    # BƯỚC 3: Tự động tìm & tải B-roll footage (hoặc lấy từ tham số người dùng đưa vào)
    footage_files = fetch_broll_footage(
        search_queries=queries,
        run_dir=run_dir,
        custom_footage=footage,
        min_total_duration_sec=total_audio_sec,
        topic=topic,
        aspect_ratio=aspect_ratio,
    )

    # BƯỚC 4: Dựng & Cắt các đoạn B-roll 3-5s ghép liên tiếp phủ kín thời lượng audio
    merged_video = assemble_broll_video(
        footage_files=footage_files,
        total_duration_sec=total_audio_sec,
        run_dir=run_dir,
        aspect_ratio=aspect_ratio,
    )

    # BƯỚC 5: Mux hoàn thiện video, audio & ép phụ đề TikTok
    final_video = render_final_master_video(
        video_path=merged_video,
        wav_path=wav_path,
        sections=sections,
        timings=timings,
        run_dir=run_dir,
        aspect_ratio=aspect_ratio,
        sub_style=sub_style,
    )

    manifest = {
        "topic": topic,
        "title": script_data.get("title"),
        "duration_sec": total_audio_sec,
        "duration_mins": round(total_audio_sec / 60.0, 2),
        "aspect_ratio": aspect_ratio,
        "voice": voice,
        "speed": speed,
        "final_master_video": str(final_video),
        "audio_path": str(wav_path),
        "footage_sources": [str(f.name) for f in footage_files],
        "num_sections": len(sections),
    }
    (run_dir / "broll_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\n" + "=" * 96)
    print("✨ CHẾ ĐỘ B-ROLL HOÀN TẤT THÀNH CÔNG!")
    print(f"🎬 Video thành phẩm : {final_video.resolve()}")
    print(f"⏱️  Thời lượng thật   : {total_audio_sec:.1f}s ({total_audio_sec/60:.2f} phút)")
    print(f"📹 Footage sử dụng  : {[f.name for f in footage_files]}")
    print("=" * 96)

    return manifest
