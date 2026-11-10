"""
NODE 5: `visual_judge_and_update_registry_node` — Kiểm định đầu ra THẬT.

Trước đây node này trả về các điểm SyncNet/FaceSim gán cứng (9.2, LSE-C ~6.2...) cho cả video không có khuôn mặt,
nên "đạt" 100% bất kể video ra sao. Nay chỉ báo những gì đo được:
  - file video tồn tại, đúng độ dài giọng đọc (|chênh| <= 0.35s), có cả hình lẫn tiếng;
  - tỉ lệ cảnh dùng ảnh dự phòng (không khớp lời) và điểm hình ảnh thật từ `media_generator_node`;
  - chế độ HUMAN_WITH_LIPSYNC: ghi rõ CHƯA có nhép môi (không chấm điểm giả).
Không đăng TikTok tự động; chỉ tạo caption từ `story_moral` để người dùng duyệt thủ công.
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Dict, Any

from config.settings import MIN_OUTPUT_TOTAL_SCORE
from graph.state import ChristianVideoState


def _probe_duration(video_path: str) -> float:
    import imageio_ffmpeg

    res = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-i", video_path], capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
    if not m:
        return 0.0
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def visual_judge_and_update_registry_node(state: ChristianVideoState) -> Dict[str, Any]:
    video_path = state.get("final_master_video_path", "")
    audio_sec = float(state.get("audio_duration_sec", 0.0))
    asset_report = state.get("asset_report", {}) or {}
    visual = state.get("visual_scores", {}) or {}
    intent = state.get("intent_mode", "NO_HUMAN_BROLL")

    exists = bool(video_path) and Path(video_path).exists() and Path(video_path).stat().st_size > 100_000
    video_sec = _probe_duration(video_path) if exists else 0.0
    offset_sec = round(video_sec - audio_sec, 3)
    fps = int(state.get("audio_sync_features", {}).get("video_fps", 30))

    problems = []
    if not exists:
        problems.append("không có file video hợp lệ")
    if exists and abs(offset_sec) > 0.35:
        problems.append(f"video lệch giọng đọc {offset_sec}s")
    if asset_report.get("fallback_scenes"):
        problems.append(f"{asset_report['fallback_scenes']} cảnh dùng ảnh dự phòng")
    if intent == "HUMAN_WITH_LIPSYNC":
        problems.append("nhép môi chưa được cài đặt (đã render như HUMAN_NO_LIPSYNC)")

    sync_score = 1.0 if exists and abs(offset_sec) <= 0.35 else 0.0
    total = round(0.4 * sync_score + 0.6 * float(visual.get("visual_total_score", 0.0)), 3)

    output_scores = {
        "lse_c": None,
        "lse_d": None,
        "av_offset_frames": int(round(offset_sec * fps)),
        "mouth_sharp_ratio": None,
        "bbox_jitter_px": None,
        "output_total_score": total,
        "failure_reason": "; ".join(problems) or None,
    }
    if video_path:
        (Path(video_path).parent / "output_score_report.json").write_text(
            json.dumps(output_scores, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    caption = state.get("story_moral", "").strip()
    status = "READY_FOR_MANUAL_REVIEW" if total >= MIN_OUTPUT_TOTAL_SCORE else "NEEDS_ATTENTION"
    print(f"[Node 5: visual_judge] OutputScore={total} | video={video_sec:.2f}s vs audio={audio_sec:.2f}s | {status} | {problems or 'không có vấn đề'}")

    return {
        "face_similarity_score": 0.0,
        "wav2lip_pads": [],
        "face_restored_applied": False,
        "output_scores": output_scores,
        "tiktok_publish_status": status,
        "tiktok_caption": caption,
        "characters": {},
        "visual_retry_count": state.get("visual_retry_count", 0),
    }


def should_retry_output_gate(state: ChristianVideoState) -> str:
    """Render lại không sửa được lỗi kịch bản/ảnh nên không vòng lặp; kết quả được báo thẳng cho người dùng."""
    return "done"
