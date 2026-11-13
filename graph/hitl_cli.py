"""
Giao diện HITL CLI (Human-in-the-Loop) duyệt & tinh chỉnh clip (`graph/hitl_cli.py`).

Cung cấp CLI tương tác trực quan trên terminal cho người dùng:
  1. Xem danh sách toàn bộ các Block / Cảnh (thời lượng, lời đọc, file clip đang gán, điểm đánh giá).
  2. Trích xuất ảnh thumbnail / preview (hoặc mở trực tiếp file video bằng xdg-open/ffplay nếu có).
  3. Hoán đổi (Swap) hoặc thay thế file clip cho riêng 1 block mà KHÔNG cần chạy lại LLM hay TTS.
  4. Bật/tắt phụ đề (--sub-mode narration_full / none / keyword_only).
  5. Bấm Render lại ngay lập tức chỉ trong vài giây.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from graph.flow_bundler import _assign_clips_to_blocks, _natural_sort_key, render_from_flow_clips
from graph.video_renderer import _ffmpeg, _probe_clip_duration


def _clear_screen() -> None:
    # Không xóa hẳn trên môi trường non-interactive, chỉ in dòng phân cách
    if os.isatty(0):
        print("\033[H\033[J", end="")
    else:
        print("\n" + "=" * 70 + "\n")


def _generate_thumbnail(video_path: Path, out_thumb: Path, at_sec: float = 1.0) -> bool:
    """Trích xuất 1 frame ảnh làm thumbnail preview."""
    ff = _ffmpeg()
    cmd = [
        ff, "-y", "-ss", f"{at_sec:.2f}", "-i", str(video_path),
        "-frames:v", "1", "-vf", "scale=360:640:force_original_aspect_ratio=decrease",
        str(out_thumb)
    ]
    res = subprocess.run(cmd, capture_output=True)
    return out_thumb.exists() and out_thumb.stat().st_size > 1000


def list_workspace_blocks(run_dir: Path) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Đọc thông tin phiên chạy flow_manifest và danh sách block."""
    manifest_path = run_dir / "flow_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Không tìm thấy `flow_manifest.json` trong: {run_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    clips_dir = run_dir / "flow_clips"
    if not clips_dir.exists():
        clips_dir.mkdir(parents=True, exist_ok=True)

    exts = {".mp4", ".mov", ".webm", ".mkv"}
    found_clips = sorted([p for p in clips_dir.iterdir() if p.is_file() and p.suffix.lower() in exts], key=_natural_sort_key)

    blocks = [dict(b) for b in manifest.get("blocks", [])]
    total_audio_sec = float(manifest.get("audio_duration_sec", 0.0))

    if found_clips and blocks:
        assigned = _assign_clips_to_blocks(found_clips, blocks, total_audio_sec)
        return manifest, assigned
    return manifest, blocks


def print_blocks_dashboard(manifest: Dict[str, Any], blocks: List[Dict[str, Any]], run_dir: Path) -> None:
    """In bảng điều khiển chi tiết từng Block lên terminal."""
    topic = manifest.get("topic_title", "Không tiêu đề")
    audio_dur = float(manifest.get("audio_duration_sec", 0.0))
    master_path = run_dir / "final_master.mp4"
    master_status = f"✅ ĐÃ DỰNG ({master_path.stat().st_size / (1024*1024):.1f} MB)" if master_path.exists() else "⏳ CHƯA DỰNG"

    print("╔" + "═" * 72 + "╗")
    print(f"║ 🎬 BẢNG ĐIỀU KHIỂN DUYỆT VIDEO (HITL CLI) - WAV2VIDEO".ljust(72) + "║")
    print(f"║ Chủ đề: {topic[:58]}".ljust(72) + "║")
    print(f"║ Tổng thời lượng âm thanh: {audio_dur:.2f}s | Trạng thái: {master_status}".ljust(72) + "║")
    print("╚" + "═" * 72 + "╝\n")

    print(f"{'BLOCK':<7} | {'CẢNH':<8} | {'THỜI LƯỢNG':<10} | {'CLIP ĐANG DÙNG':<25} | {'TRẠNG THÁI'}")
    print("-" * 74)

    for b in blocks:
        b_idx = b.get("block_index", "?")
        scenes = str(b.get("scene_indices", []))
        dur = f"{float(b.get('duration_sec', 0.0)):.2f}s"
        clip_p = b.get("media_path")
        if clip_p and Path(clip_p).exists():
            c_name = Path(clip_p).name
            if len(c_name) > 24:
                c_name = c_name[:10] + "..." + c_name[-11:]
            c_dur = _probe_clip_duration(Path(clip_p))
            status = f"Khớp ({c_dur:.1f}s)" if c_dur >= float(b.get("duration_sec", 0.0)) * 0.9 else f"Ngắn ({c_dur:.1f}s)"
        else:
            c_name = "(Chưa có clip)"
            status = "❌ Thiếu clip"

        print(f"Block {b_idx:<2} | {scenes:<8} | {dur:<10} | {c_name:<25} | {status}")
        narr = b.get("narration_vn", "")
        if narr:
            short_narr = (narr[:65] + "...") if len(narr) > 65 else narr
            print(f"  └─ Lời đọc: \"{short_narr}\"")
    print("-" * 74)


def preview_block_clip(block: Dict[str, Any], run_dir: Path) -> None:
    """Hiển thị thông tin chi tiết và tạo ảnh thumbnail hoặc mở video."""
    clip_p = block.get("media_path")
    if not clip_p or not Path(clip_p).exists():
        print(f"\n❌ Block {block.get('block_index')} chưa có file clip để preview.")
        return

    path = Path(clip_p)
    dur = _probe_clip_duration(path)
    thumbs_dir = run_dir / "thumbnails"
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    thumb_file = thumbs_dir / f"block_{block.get('block_index')}_thumb.jpg"

    has_thumb = _generate_thumbnail(path, thumb_file)

    print("\n" + "=" * 50)
    print(f"🔍 PREVIEW BLOCK {block.get('block_index')}:")
    print(f" - File video  : {path}")
    print(f" - Kích thước  : {path.stat().st_size / (1024*1024):.2f} MB")
    print(f" - Thời lượng  : {dur:.2f}s (Cần: {float(block.get('duration_sec', 0.0)):.2f}s)")
    if has_thumb:
        print(f" - Thumbnail   : {thumb_file}")
    print(f" - Lời đọc     : {block.get('narration_vn', '')}")
    print(f" - Prompt Flow : {block.get('flow_prompt', '')[:120]}...")
    print("=" * 50)

    # Thử mở bằng xdg-open nếu có môi trường đồ họa
    if os.environ.get("DISPLAY") and shutil.which("xdg-open"):
        try:
            subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("🚀 Đã mở clip trong trình phát video của hệ thống.")
        except Exception:
            pass


def swap_block_clip(block: Dict[str, Any], run_dir: Path, new_clip_path_str: str) -> bool:
    """Thay thế clip cho riêng 1 block bằng 1 file mp4 khác."""
    new_path = Path(new_clip_path_str.strip().strip("'\""))
    if not new_path.exists() or not new_path.is_file():
        print(f"❌ File không tồn tại: {new_path}")
        return False

    clips_dir = run_dir / "flow_clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    b_idx = block.get("block_index", 1)
    target_name = f"{b_idx}{new_path.suffix.lower()}"
    dest = clips_dir / target_name

    shutil.copy2(new_path, dest)
    block["media_path"] = str(dest)
    print(f"✅ Đã thay thế thành công Block {b_idx} bằng clip mới: {dest.name}")
    return True


def run_hitl_cli(run_dir_str: str, sub_mode: str = "narration_full") -> None:
    """Vòng lặp menu CLI tương tác HITL."""
    run_dir = Path(run_dir_str)
    if not run_dir.exists():
        print(f"❌ Không tìm thấy thư mục: {run_dir}")
        return

    while True:
        try:
            manifest, blocks = list_workspace_blocks(run_dir)
        except Exception as e:
            print(f"❌ Lỗi đọc manifest: {e}")
            break

        _clear_screen()
        print_blocks_dashboard(manifest, blocks, run_dir)

        print("\n🛠️  TÙY CHỌN THAO TÁC:")
        print("  [1-4]    : Xem chi tiết (Preview & Thumbnail) của Block tương ứng")
        print("  s [1-4]  : Thay đổi (Swap) file clip cho Block (vd: s 2 /path/to/new_clip.mp4)")
        print("  p        : Xem trước video thành phẩm `final_master.mp4`")
        print("  sub      : Đổi chế độ phụ đề (hiện tại: " + sub_mode + ")")
        print("  r        : 🚀 RENDER GHÉP VIDEO NGAY BÂY GIỜ")
        print("  q        : Thoát")

        try:
            cmd = input("\n👉 Nhập lựa chọn của bạn: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nĐã thoát HITL CLI.")
            break

        if not cmd:
            continue

        cmd_lower = cmd.lower()
        if cmd_lower in ("q", "quit", "exit"):
            print("Tạm biệt!")
            break

        if cmd.isdigit():
            idx = int(cmd)
            target = next((b for b in blocks if b.get("block_index") == idx), None)
            if target:
                preview_block_clip(target, run_dir)
                input("\nBấm Enter để quay lại menu...")
            else:
                print(f"Không có Block {idx}!")
                input("Bấm Enter...")
            continue

        if cmd_lower.startswith("s ") or cmd_lower.startswith("swap "):
            parts = cmd.split(maxsplit=2)
            if len(parts) >= 3 and parts[1].isdigit():
                b_idx = int(parts[1])
                target = next((b for b in blocks if b.get("block_index") == b_idx), None)
                if target:
                    swap_block_clip(target, run_dir, parts[2])
                else:
                    print(f"Không tìm thấy Block {b_idx}!")
            else:
                print("Cú pháp đúng: s <số_block> <đường_dẫn_file_video>")
            input("Bấm Enter...")
            continue

        if cmd_lower == "p":
            master_p = run_dir / "final_master.mp4"
            if master_p.exists():
                print(f"\n🎬 File video thành phẩm: {master_p}")
                print(f"   Dung lượng: {master_p.stat().st_size / (1024*1024):.2f} MB")
                if os.environ.get("DISPLAY") and shutil.which("xdg-open"):
                    subprocess.Popen(["xdg-open", str(master_p)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                print("\n❌ Chưa có file `final_master.mp4`. Hãy bấm 'r' để render trước.")
            input("Bấm Enter...")
            continue

        if cmd_lower == "sub":
            print("\nChọn kiểu phụ đề:")
            print("  1. narration_full (Hiện đầy đủ 100% lời đọc)")
            print("  2. none           (Video sạch, không chữ)")
            print("  3. keyword_only   (Chỉ hiện từ khóa tóm tắt)")
            c_sub = input("Chọn (1/2/3): ").strip()
            if c_sub == "1":
                sub_mode = "narration_full"
            elif c_sub == "2":
                sub_mode = "none"
            elif c_sub == "3":
                sub_mode = "keyword_only"
            print(f"Đã chuyển sang: {sub_mode}")
            input("Bấm Enter...")
            continue

        if cmd_lower == "r":
            print("\n🚀 Bắt đầu quá trình render ghép video...")
            try:
                res = render_from_flow_clips(run_dir=run_dir, sub_mode=sub_mode)
                print(f"\n🎉 HOÀN THÀNH! Video master tại: {res['final_master_video_path']}")
            except Exception as ex:
                print(f"\n❌ Render thất bại: {ex}")
            input("\nBấm Enter để xem cập nhật trên bảng điều khiển...")
            continue

        print(f"Lệnh không hợp lệ: {cmd}")
        input("Bấm Enter...")

