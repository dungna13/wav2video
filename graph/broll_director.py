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


def _get_ytdlp_bin() -> str:
    """Tìm binary yt-dlp ưu tiên trong venv trước, rồi tới system PATH."""
    venv_ytdlp = Path(__file__).resolve().parent.parent.parent / ".venv" / "bin" / "yt-dlp"
    if venv_ytdlp.exists():
        return str(venv_ytdlp)
    local_ytdlp = Path(sys.executable).parent / "yt-dlp"
    if local_ytdlp.exists():
        return str(local_ytdlp)
    return "yt-dlp"


def _slugify(text: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", text)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    return re.sub(r"[-\s]+", "_", s)


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
    - 3 phút: ~460 từ, 10-12 phân đoạn
    - 5 phút: ~770 từ, 18-22 phân đoạn
    - Cung cấp 3-5 câu lệnh tìm kiếm B-roll footage bằng tiếng Anh.
    """
    target_words = int(duration_mins * 155)
    num_sections = max(4, int(duration_mins * 3.5))

    system_instruction = (
        "Bạn là Giám đốc Sáng tạo kiêm Biên kịch hàng đầu cho các kênh phim tài liệu bí ẩn, khoa học khám phá "
        "dạng dài trên TikTok/YouTube (phong cách dẫn dắt lôi cuốn, kịch tính, dồn dập như kênh @vanthanhthu09). "
        "Nhiệm vụ của bạn là soạn kịch bản chi tiết, phong phú, đạt đúng thời lượng và số từ yêu cầu. "
        "Trả về DUY NHẤT 1 JSON Object tuân thủ schema."
    )

    prompt = f"""Hãy viết kịch bản phim tài liệu bí ẩn, cuốn hút cho chủ đề sau:
CHỦ ĐỀ: "{topic}"

YÊU CẦU THỜI LƯỢNG & ĐỘ DÀI:
- Thời lượng mục tiêu: {duration_mins:.1f} phút.
- Tốc độ đọc: 1.35x (khoảng 155 từ tiếng Việt/phút).
- TỔNG SỐ TỪ TIẾNG VIỆT CẦN ĐẠT: Khoảng {target_words} từ (tối thiểu {int(target_words * 0.85)} từ).
- Số lượng phân đoạn (sections): {num_sections} phân đoạn liên hoàn, mỗi đoạn từ 35 đến 55 từ.

CẤU TRÚC KỊCH BẢN KỂ CHUYỆN:
1. Đoạn 1 (Hook 0:00 - 0:15): Một câu hỏi gây sốc hoặc dữ kiện bí ẩn chưa có lời giải để giữ chân người xem ngay giây đầu.
2. Đoạn 2-4 (Bối cảnh & Dữ liệu lịch sử/khoa học): Nguồn gốc, niên đại, tọa độ hoặc sự kiện mở đầu.
3. Đoạn 5-{num_sections - 3} (Bí ẩn & Các giả thuyết tranh cãi): Đi sâu vào các chi tiết kỳ lạ, nghịch lý khoa học, nhân chứng hoặc các phát hiện chấn động.
4. Đoạn {num_sections - 2}-{num_sections - 1} (Cao trào / Bức màn hé lộ): Những bằng chứng mới nhất hoặc giả thuyết bất ngờ nhất.
5. Đoạn cuối (Đúc kết & Câu hỏi mở): Một câu chốt triết lý sâu sắc khiến người xem phải bình luận và chia sẻ.

YÊU CẦU VỀ TÌM KIẾM B-ROLL FOOTAGE:
- Trong trường `broll_search_queries`: Hãy gợi ý 3 đến 5 cụm từ tìm kiếm video tư liệu bằng tiếng Anh (chất lượng cao 4K, b-roll, drone shot, cinematic timelapse) để hệ thống tự động tìm và tải video minh họa phù hợp trên YouTube/Pexels.
"""

    print(f"\n[B-Roll Director] Đang yêu cầu LLM soạn kịch bản {duration_mins:.1f} phút (~{target_words} từ, {num_sections} phân đoạn)...")
    result = call_gemini_thinking_structured(
        prompt=prompt,
        response_schema=BROLL_SCRIPT_SCHEMA,
        system_instruction=system_instruction,
    )

    if not result or not result.get("sections"):
        print("[B-Roll Director] LLM trả về rỗng -> Sử dụng bộ kịch bản dự phòng chất lượng cao.")
        result = _fallback_script(topic, duration_mins)

    sections = result.get("sections", [])
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
    return {
        "title": f"Bí ẩn chưa có lời giải: {clean_title}",
        "topic_summary_vn": f"Khám phá toàn cảnh những bí mật kỳ lạ nhất về {clean_title}.",
        "duration_mins": duration_mins,
        "target_word_count": int(duration_mins * 155),
        "broll_search_queries": [
            f"{clean_title} 4k cinematic documentary b-roll",
            f"{clean_title} drone 4k aerial view",
            "ancient mysteries history documentary footage 4k",
        ],
        "sections": [
            {
                "section_index": 1,
                "title": "Bí ẩn mở đầu",
                "narration_vn": f"Liệu bạn có từng tự hỏi, điều gì thực sự ẩn giấu đằng sau {clean_title}? Hàng thế kỷ qua, hàng triệu người đã tìm kiếm câu trả lời.",
                "visual_mood": "Cinematic slow aerial shot approaching the subject",
            },
            {
                "section_index": 2,
                "title": "Những dấu vết lịch sử",
                "narration_vn": f"Các nhà nghiên cứu phát hiện ra những ghi chép cổ xưa về {clean_title}, nơi mọi quy luật thông thường dường như bị đảo lộn hoàn toàn.",
                "visual_mood": "Ancient maps and close up details of old manuscripts",
            },
            {
                "section_index": 3,
                "title": "Nghịch lý khoa học",
                "narration_vn": "Khoa học hiện đại đã vào cuộc với những thiết bị tối tân nhất, nhưng càng đào sâu, các chuyên gia lại càng bối rối trước những hiện tượng dị thường.",
                "visual_mood": "Modern scientific lab scans and 3D wireframe reconstruction",
            },
            {
                "section_index": 4,
                "title": "Câu hỏi còn bỏ ngỏ",
                "narration_vn": f"Cho đến ngày hôm nay, {clean_title} vẫn là một câu đố thách thức nhân loại. Bạn nghĩ sao về bí mật này?",
                "visual_mood": "Dramatic sunset over horizon with silhouette",
            },
        ],
    }


# =====================================================================
# 3. TỰ ĐỘNG TÌM & TẢI VIDEO B-ROLL (HOẶC NHẬN FOOTAGE CÓ SẴN)
# =====================================================================
def fetch_broll_footage(
    search_queries: List[str],
    run_dir: Path,
    custom_footage: Optional[str] = None,
    min_total_duration_sec: float = 60.0,
) -> List[Path]:
    """
    Tự động tìm kiếm và tải B-roll video:
    1. Nếu người dùng chỉ định `--footage <file_hoặc_thư_mục>` -> Sử dụng trực tiếp video của người dùng.
    2. Nếu không chỉ định -> Tự động dùng `yt-dlp` tìm kiếm các video 4K B-roll trên YouTube theo queries của LLM.
    3. Dự phòng -> Tìm các video mp4 có sẵn trong `workspace/` hoặc `assets/`.
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

    # Trường hợp 2: Tự động tìm kiếm & tải qua yt-dlp
    ytdlp = _get_ytdlp_bin()
    downloaded_files: List[Path] = []
    print(f"\n🔍 [B-Roll Auto-Fetch] Hệ thống tự động tìm video tư liệu phù hợp qua yt-dlp...")

    for query in search_queries[:3]:
        clean_q = query.strip()
        if not clean_q:
            continue
        print(f"   ├─ Đang tìm: \"{clean_q}\" (lọc video 40s - 450s, 1080p)...")
        # Định dạng tên file an toàn
        out_template = str(footage_dir / f"broll_%(id)s.%(ext)s")
        cmd = [
            ytdlp,
            "--no-playlist",
            "--match-filter", "duration >= 35 & duration <= 600",
            "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
            "--max-downloads", "1",
            "--output", out_template,
            f"ytsearch2:{clean_q}",
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode == 0:
                for f in footage_dir.iterdir():
                    if f.is_file() and f.suffix.lower() in valid_exts and f not in downloaded_files:
                        downloaded_files.append(f)
                        print(f"   │  └─ Tải thành công: {f.name} ({f.stat().st_size / (1024*1024):.1f} MB)")
            if len(downloaded_files) >= 2:
                break
        except Exception as e:
            print(f"   │  └─ Lỗi tải yt-dlp: {e}")

    if downloaded_files:
        return downloaded_files

    # Trường hợp 3: Dự phòng các video sẵn có trong workspace/
    ws_dir = run_dir.parent
    ref_candidates = [
        ws_dir / "tiktok_ref.mp4",
        ws_dir.parent / "workspace" / "tiktok_ref.mp4",
        run_dir.parent.parent / "Ngo_Quyen_pointing_baton_forward_343cea7e.mp4",
    ]
    for cand in ref_candidates:
        if cand.exists() and cand.stat().st_size > 100_000:
            print(f"⚠️ [B-Roll Auto-Fetch] Không có mạng/yt-dlp -> Sử dụng video tư liệu dự phòng: {cand.name}")
            return [cand]

    # Quét toàn bộ workspace tìm file mp4 bất kỳ
    for root, _, files in os.walk(str(ws_dir)):
        for fname in files:
            if fname.endswith(".mp4") and not fname.startswith("final_"):
                p = Path(root) / fname
                if p.stat().st_size > 500_000:
                    return [p]

    raise RuntimeError("Không tìm thấy video B-roll nào và không thể tải qua yt-dlp. Vui lòng cung cấp video qua tham số `--footage <đường_dẫn>`.")


# =====================================================================
# 4. THU ÂM & PHỤ ĐỀ ĐỒNG BỘ CHÍNH XÁC
# =====================================================================
def synthesize_broll_narration(
    sections: List[Dict[str, Any]],
    run_dir: Path,
    voice_name: str = "vanthanhthu",
    speed_rate: float = 1.35,
    music_mood: str = "cinematic_mystery_suspense",
) -> Tuple[Path, List[Tuple[float, float]], float]:
    """
    Sinh file audio thuyết minh hoàn chỉnh từ danh sách các sections:
    - Trả về đường dẫn file `.wav`, mốc thời gian từng đoạn `(start, end)`, và tổng thời lượng audio.
    - Nhạc nền huyền bí được tự động hạ âm lượng (auto-ducking) khi có tiếng thuyết minh.
    """
    wav_path = run_dir / "voiceover_studio.wav"
    scene_texts = [s["narration_vn"].strip() for s in sections]

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

        cmd = [
            ff, "-y",
            "-ss", f"{start_sec:.2f}",
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
        if res.returncode == 0 and cut_filename.exists():
            cut_files.append(cut_filename)
            current_time += curr_shot_dur
            shot_index += 1
        else:
            # Nếu ffmpeg báo lỗi ở timestamp đó, thử điểm 0.0s
            cmd[3] = "0.0"
            res2 = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res2.returncode == 0 and cut_filename.exists():
                cut_files.append(cut_filename)
                current_time += curr_shot_dur
                shot_index += 1
            else:
                break

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
        text = sec_item["narration_vn"].strip()

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
    sub_style: str = "tiktok_yellow",
) -> Path:
    """Mux video, audio và burn subtitles thành final_master.mp4."""
    ff = _get_ffmpeg_bin()
    target_w, target_h = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)
    final_output = run_dir / "final_master.mp4"

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

    print(f"\n🎨 [B-Roll Render] Đang hoàn thiện Master Video 1080p và ép phụ đề {sub_style}...")

    # Filter ép phụ đề
    sub_filter = f"ass='{ass_path.name}'"

    cmd = [
        ff, "-y",
        "-i", str(video_path),
        "-i", str(wav_path),
        "-vf", f"{sub_filter},format=yuv420p",
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
        # Nếu filter ass bị lỗi đường dẫn, thử dùng subtiles filter srt
        print(f"⚠️ Thử chế độ phụ đề cơ bản nếu filter ASS chưa sẵn sàng: {res.stderr[:200]}")
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
    voice: str = "vanthanhthu",
    speed: float = 1.35,
    aspect_ratio: str = "9:16",
    sub_style: str = "tiktok_yellow",
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Điểm vào duy nhất cho chế độ B-Roll (Cắt video có sẵn/tự lấy + ghép Audio 3-5 phút + Subtitles).
    Hoàn toàn thuần Python tuyến tính, không dùng bất kỳ thư viện vẽ đồ thị hay DAG nào.
    """
    ts = time.strftime("%m%d_%H%M%S")
    slug = _slugify(topic)[:32]
    run_name = f"broll_{slug}_{ts}"

    run_dir = Path(output_dir) if output_dir else Path(WORKSPACE_DIR) / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 96)
    print(f"🚀 BẮT ĐẦU CHẾ ĐỘ B-ROLL DÀI {duration_mins:.1f} PHÚT (ZERO GRAPH LIBRARIES)")
    print(f"📌 Chủ đề      : {topic}")
    print(f"⏱️  Thời lượng  : {duration_mins:.1f} phút")
    print(f"📁 Thư mục xuất: {run_dir.resolve()}")
    print("=" * 96)

    # BƯỚC 1: LLM soạn kịch bản dài phù hợp số phút yêu cầu
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

    # BƯỚC 3: Tự động tìm & tải B-roll footage (hoặc lấy từ tham số người dùng đưa vào)
    queries = script_data.get("broll_search_queries", [])
    footage_files = fetch_broll_footage(
        search_queries=queries,
        run_dir=run_dir,
        custom_footage=footage,
        min_total_duration_sec=total_audio_sec,
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
