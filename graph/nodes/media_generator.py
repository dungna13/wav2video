"""
NODE 4: `media_generator_node` — Từ danh sách cảnh tới video hoàn chỉnh.
  1. Giọng đọc VITS theo TỪNG CẢNH -> nhận mốc thời gian thật (start/end) của mỗi cảnh.
  2. Lấy hình/video đa ứng viên, chống trùng ID (`graph/asset_fetcher.py`).
  3. Đo chất lượng hình THẬT trên CẢ video stock lẫn ảnh AI qua `VisualFeatureScorer` (0-token API:
     keyframe `ffmpeg`, độ nét Laplacian, khung hình tối/đứng hình, liên tục màu và local CLIP nếu sẵn có).
  4. Dựng phim tài liệu (`graph/video_renderer.py`): camera zoom/pan, xfade, chỉnh màu, grain, phụ đề karaoke.
"""

import json
import re
import time
import unicodedata
from pathlib import Path
from typing import Dict, Any, List, Optional

import numpy as np

from config.settings import (
    IMAGE_WIDTH,
    IMAGE_HEIGHT,
    MIN_CLIP_PROMPT_SCORE,
    MIN_CONTINUITY_SCORE,
    VIDEO_FPS,
    WORKSPACE_DIR,
)
from graph.audio_sync import synthesize_scene_voiceover, extract_waveform_sync_features
from graph.asset_fetcher import fetch_scene_assets
from graph.visual_scorer import (
    VisualFeatureScorer,
    compute_pair_continuity,
    harmonize_scene_continuity,
)
from graph.video_renderer import render_documentary_video
from graph.state import ChristianVideoState


def _slugify_vn(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "_", norm).strip("_")[:36] or "topic"


def evaluate_real_visual_quality(
    scenes: List[Dict[str, Any]],
    asset_report: Dict[str, Any],
    intent_mode: str = "NO_HUMAN_BROLL",
    scorer: Optional[VisualFeatureScorer] = None,
    pre_evals: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Đo chất lượng thật trên TẤT CẢ các cảnh (trích keyframe cho video stock + đọc ảnh tĩnh)."""
    local_scorer = scorer or VisualFeatureScorer()
    no_human = intent_mode == "NO_HUMAN_BROLL"

    sharp_vals: List[float] = []
    clip_vals: List[float] = []
    valid_evals: List[Dict[str, Any]] = []

    human_violations = 0
    dark_scenes = 0
    static_scenes = 0
    corrupt_scenes = 0
    scored_videos = 0
    scored_images = 0

    for idx, sc in enumerate(scenes):
        mpath = Path(sc["media_path"])
        mtype = sc.get("media_type", "image")
        ev = (
            pre_evals[idx]
            if pre_evals is not None and idx < len(pre_evals)
            else local_scorer.inspect_media(
                mpath,
                media_type=mtype,
                prompt_en=sc.get("image_prompt_en", ""),
                intent_mode=intent_mode,
                color_harm_params=sc.get("color_harm_params"),
            )
        )
        # Lưu bản gọn không chứa numpy array để LangGraph SqliteSaver serialize an toàn
        sc["visual_eval"] = {
            "media_type": mtype,
            "sharpness_score": ev["sharpness_score"],
            "brightness_mean": ev["brightness_mean"],
            "motion_diff": ev["motion_diff"],
            "clip_prompt_score": ev["clip_prompt_score"],
            "human_detected": ev["human_detected"],
            "is_dark": ev["is_dark"],
            "is_static": ev["is_static"],
            "continuity_harmonized": bool(sc.get("continuity_harmonized", False)),
            "reject_reasons": ev["reject_reasons"],
        }
        if ev["is_corrupt"]:
            corrupt_scenes += 1
            continue
        if mtype == "video":
            scored_videos += 1
        else:
            scored_images += 1

        sharp_vals.append(float(ev["sharpness_score"]))
        if ev["clip_prompt_score"] is not None:
            clip_vals.append(float(ev["clip_prompt_score"]))
        if ev["mean_rgb"] is not None and ev["hist_rgb"] is not None:
            valid_evals.append(ev)
        if no_human and ev.get("human_detected") is True:
            human_violations += 1
        if ev["is_dark"]:
            dark_scenes += 1
        if ev["is_static"]:
            static_scenes += 1

    sharpness = float(np.mean(sharp_vals)) if sharp_vals else 0.0
    if len(valid_evals) > 1:
        cont_pairs = [compute_pair_continuity(valid_evals[idx - 1], valid_evals[idx]) for idx in range(1, len(valid_evals))]
        continuity = float(np.mean(cont_pairs))
    else:
        continuity = 1.0

    clip_score: Optional[float] = round(float(np.mean(clip_vals)), 4) if clip_vals else None
    total_scenes = max(1, len(scenes))
    real_ratio = asset_report.get("real_scenes", total_scenes) / total_scenes

    if clip_score is not None:
        norm_clip = min(1.0, max(0.0, clip_score / 0.35))
        base_total = 0.35 * norm_clip + 0.30 * real_ratio + 0.20 * continuity + 0.15 * sharpness
    else:
        base_total = 0.50 * real_ratio + 0.30 * sharpness + 0.20 * continuity

    penalty = human_violations * 0.08 + (dark_scenes + static_scenes + corrupt_scenes) * 0.06
    total = round(float(np.clip(base_total - penalty, 0.0, 1.0)), 3)

    reasons: List[str] = []
    if asset_report.get("fallback_scenes"):
        reasons.append(f"{asset_report['fallback_scenes']}/{total_scenes} cảnh dùng ảnh dự phòng (không khớp lời)")
    if corrupt_scenes:
        reasons.append(f"{corrupt_scenes} cảnh lỗi không đọc được frame")
    if sharpness < 0.35:
        reasons.append("hình/video thiếu nét")
    if clip_score is not None and clip_score < MIN_CLIP_PROMPT_SCORE:
        reasons.append(f"S_clip thấp ({clip_score} < {MIN_CLIP_PROMPT_SCORE})")
    if continuity < MIN_CONTINUITY_SCORE:
        reasons.append(f"lệch tông màu giữa các cảnh ({continuity:.3f} < {MIN_CONTINUITY_SCORE})")
    if human_violations:
        reasons.append(f"{human_violations} cảnh nghi dính người ở mode NO_HUMAN_BROLL")
    if dark_scenes:
        reasons.append(f"{dark_scenes} cảnh quá tối")
    if static_scenes:
        reasons.append(f"{static_scenes} clip video bị đứng hình")

    return {
        "clip_prompt_score": clip_score,
        "continuity_score": round(continuity, 3),
        "identity_pose_score": None,
        "sharpness_score": round(sharpness, 3),
        "real_scene_ratio": round(real_ratio, 3),
        "scored_videos": scored_videos,
        "scored_images": scored_images,
        "human_violation_scenes": human_violations,
        "dark_or_static_scenes": dark_scenes + static_scenes,
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
    effective_mode = state.get("effective_intent_mode") or "NO_HUMAN_BROLL"

    seed = abs(hash(topic_title)) % 800000 + 100000
    run_id = f"run_{_slugify_vn(topic_title)}_{time.strftime('%m%d_%H%M%S')}"
    run_dir = WORKSPACE_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # 1. Giọng đọc theo cảnh + mốc thời gian thật (+ sfx_cue, music_mood, -14 LUFS)
    wav_path, timings = synthesize_scene_voiceover(
        [s["narration_vn"] for s in scenes],
        output_filename=run_dir / "audio_16k_mono.wav",
        sfx_cues=[str(s.get("sfx_cue", "none")) for s in scenes],
        music_mood=str(state.get("music_mood", "")),
    )
    hook = state.get("hook_and_context_vn", "") or scenes[0]["narration_vn"]
    deep = state.get("deep_explanation_vn", "") or " ".join(s["narration_vn"] for s in scenes[1:-1])
    outro = state.get("outro_takeaway_vn", "") or scenes[-1]["narration_vn"]
    audio_sync_features = extract_waveform_sync_features(
        wav_path=wav_path, scene_narration=hook, outro_reflection=deep, closing_prayer=outro, fps=VIDEO_FPS
    )
    total_audio_sec = float(audio_sync_features["duration_sec"])

    # 2. Hình/video đa ứng viên cho từng cảnh + chống trùng + chấm 0-token
    scorer = VisualFeatureScorer()
    print(f"[Node 4: media_generator_node] Lấy hình cho {len(scenes)} cảnh (mode={effective_mode})...")
    asset_report = fetch_scene_assets(
        scenes,
        style_anchor,
        run_dir,
        seed,
        IMAGE_WIDTH,
        IMAGE_HEIGHT,
        intent_mode=effective_mode,
        scorer=scorer,
    )

    # 3. ContinuityHarmonizer (cân bằng màu giữa cảnh lệch tông) + Đo chất lượng thật
    harm_count, harm_evals = harmonize_scene_continuity(
        scenes,
        run_dir=run_dir,
        scorer=scorer,
        intent_mode=effective_mode,
        min_continuity=MIN_CONTINUITY_SCORE,
    )
    if harm_count:
        print(f"[Node 4: media_generator_node] ContinuityHarmonizer đã cân bằng màu {harm_count} cảnh.")

    visual_scores = evaluate_real_visual_quality(
        scenes,
        asset_report,
        intent_mode=effective_mode,
        scorer=scorer,
        pre_evals=harm_evals,
    )
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

    clip_tag = f" | CLIP={visual_scores['clip_prompt_score']}" if visual_scores.get("clip_prompt_score") is not None else ""
    print(
        f"[Node 4: media_generator_node] {len(scenes)} cảnh | thật={asset_report['real_scenes']} dự phòng={asset_report['fallback_scenes']} "
        f"| VisualScore={visual_scores['visual_total_score']}{clip_tag} | {total_audio_sec}s | Video={rendered['final_master_video_path']}"
    )

    return {
        "video_generation_mode": effective_mode,
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
        "continuity_harmonized": bool(harm_count > 0),
        "visual_scores": visual_scores,
        "asset_report": {**asset_report, "contact_sheet": rendered["contact_sheet_path"], "timeline": rendered["scene_timeline_path"]},
    }
