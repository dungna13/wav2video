"""
NODE 4: `media_generator_node` — Từ danh sách cảnh tới video hoàn chỉnh.
  1. Giọng đọc VITS theo TỪNG CẢNH -> nhận mốc thời gian thật (start/end) của mỗi cảnh.
  2. Lấy hình cho từng cảnh (`graph/asset_fetcher.py`: Pexels video -> ảnh AI -> dự phòng) và ghi rõ nguồn.
  3. Đo chất lượng hình THẬT (độ nét Laplacian, liên tục màu giữa các cảnh, tỉ lệ cảnh dùng dự phòng) — không còn
     chấm trên khung hình giả lập như trước.
  4. Dựng phim tài liệu (`graph/video_renderer.py`): camera zoom/pan, xfade, chỉnh màu, grain, phụ đề karaoke.
"""

import json
import re
import time
import unicodedata
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
from PIL import Image

from config.settings import IMAGE_WIDTH, IMAGE_HEIGHT, WORKSPACE_DIR, VIDEO_FPS
from graph.audio_sync import synthesize_scene_voiceover, extract_waveform_sync_features
from graph.asset_fetcher import fetch_scene_assets
from graph.video_renderer import render_documentary_video
from graph.state import ChristianVideoState


def _slugify_vn(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "_", norm).strip("_")[:36] or "topic"


def _laplacian_var(gray: np.ndarray) -> float:
    lap = (
        -4.0 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:]
    )
    return float(lap.var())


def evaluate_real_visual_quality(scenes: List[Dict[str, Any]], asset_report: Dict[str, Any]) -> Dict[str, Any]:
    """Đo trên ảnh thật của từng cảnh (cảnh video stock bị bỏ qua vì chưa có khung hình tĩnh)."""
    sharp, means = [], []
    for sc in scenes:
        if sc.get("media_type") != "image":
            continue
        im = Image.open(sc["media_path"]).convert("RGB").resize((270, 480))
        arr = np.asarray(im, dtype=np.float32)
        sharp.append(_laplacian_var(arr.mean(axis=2)))
        means.append(arr.reshape(-1, 3).mean(axis=0) / 255.0)

    sharpness = float(np.clip(np.mean(sharp) / 120.0, 0.0, 1.0)) if sharp else 1.0
    if len(means) > 1:
        diffs = [float(np.abs(means[i] - means[i - 1]).mean()) for i in range(1, len(means))]
        continuity = float(np.clip(1.0 - np.mean(diffs) * 2.0, 0.0, 1.0))
    else:
        continuity = 1.0
    total_scenes = max(1, len(scenes))
    real_ratio = asset_report.get("real_scenes", total_scenes) / total_scenes
    total = round(0.5 * real_ratio + 0.3 * sharpness + 0.2 * continuity, 3)

    reasons = []
    if asset_report.get("fallback_scenes"):
        reasons.append(f"{asset_report['fallback_scenes']}/{total_scenes} cảnh dùng ảnh dự phòng (không khớp lời)")
    if sharpness < 0.35:
        reasons.append("ảnh thiếu nét")
    return {
        "clip_prompt_score": None,  # chưa có mô hình CLIP thật -> không bịa số
        "continuity_score": round(continuity, 3),
        "identity_pose_score": None,
        "sharpness_score": round(sharpness, 3),
        "real_scene_ratio": round(real_ratio, 3),
        "visual_total_score": total,
        "failure_reason": "; ".join(reasons) or None,
    }


def media_generator_node(state: ChristianVideoState) -> Dict[str, Any]:
    topic_title = state.get("topic_title") or state.get("user_request", "Topic")[:40]
    scenes: List[Dict[str, Any]] = [dict(s) for s in (state.get("scenes") or [])]
    if not scenes:
        raise RuntimeError("media_generator_node: state không có `scenes` — prompt_architect_node chưa chạy hoặc thất bại.")
    style_anchor = state.get("style_anchor_en", "")
    genre = state.get("genre", "")

    seed = abs(hash(topic_title)) % 800000 + 100000
    run_id = f"run_{_slugify_vn(topic_title)}_{time.strftime('%m%d_%H%M%S')}"
    run_dir = WORKSPACE_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # 1. Giọng đọc theo cảnh + mốc thời gian thật (+ sfx_cue nếu có)
    wav_path, timings = synthesize_scene_voiceover(
        [s["narration_vn"] for s in scenes],
        output_filename=run_dir / "audio_16k_mono.wav",
        sfx_cues=[str(s.get("sfx_cue", "none")) for s in scenes],
    )
    hook = state.get("hook_and_context_vn", "") or scenes[0]["narration_vn"]
    deep = state.get("deep_explanation_vn", "") or " ".join(s["narration_vn"] for s in scenes[1:-1])
    outro = state.get("outro_takeaway_vn", "") or scenes[-1]["narration_vn"]
    audio_sync_features = extract_waveform_sync_features(
        wav_path=wav_path, scene_narration=hook, outro_reflection=deep, closing_prayer=outro, fps=VIDEO_FPS
    )
    total_audio_sec = float(audio_sync_features["duration_sec"])

    # 2. Hình cho từng cảnh
    print(f"[Node 4: media_generator_node] Lấy hình cho {len(scenes)} cảnh (mode={state.get('effective_intent_mode')})...")
    asset_report = fetch_scene_assets(scenes, style_anchor, run_dir, seed, IMAGE_WIDTH, IMAGE_HEIGHT)

    # 3. Đo chất lượng hình thật
    visual_scores = evaluate_real_visual_quality(scenes, asset_report)
    (run_dir / "visual_score_report.json").write_text(
        json.dumps({**visual_scores, "asset_report": asset_report}, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 4. Dựng phim
    rendered = render_documentary_video(
        run_dir=run_dir,
        wav_path=wav_path,
        scenes=scenes,
        timings=timings,
        total_audio_sec=total_audio_sec,
        topic_title=topic_title,
        genre=genre,
    )

    print(
        f"[Node 4: media_generator_node] {len(scenes)} cảnh | thật={asset_report['real_scenes']} dự phòng={asset_report['fallback_scenes']} "
        f"| VisualScore={visual_scores['visual_total_score']} | {total_audio_sec}s | Video={rendered['final_master_video_path']}"
    )

    return {
        "video_generation_mode": state.get("effective_intent_mode") or "NO_HUMAN_BROLL",
        "final_prompt": scenes[0]["image_prompt_en"],
        "generated_media_url": scenes[0]["media_path"],
        "active_seed": seed,
        "scenes": scenes,
        "scene_narration_vn": hook,
        "outro_reflection_vn": deep,
        "closing_prayer_vn": outro,
        "voiceover_wav_path": str(wav_path),
        "subtitles_ass_path": rendered["subtitles_ass_path"],
        "prepped_visual_path": rendered["prepped_visual_path"],
        "final_master_video_path": rendered["final_master_video_path"],
        "audio_duration_sec": total_audio_sec,
        "audio_sync_features": audio_sync_features,
        "prev_scene_frame_path": scenes[-1]["media_path"],
        "continuity_harmonized": False,
        "visual_scores": visual_scores,
        "asset_report": {**asset_report, "contact_sheet": rendered["contact_sheet_path"], "timeline": rendered["scene_timeline_path"]},
    }
