"""
NODE 4: `media_generator_node`
Nhận kịch bản 3 phần (`hook_and_context_vn`, `deep_explanation_vn`, `outro_takeaway_vn`) và `visual_archetype`
do LLM thiết kế ở `prompt_architect_node`, sau đó:
  1. Sinh giọng đọc Neural tiếng Việt truyền cảm (`vi-VN-NamMinhNeural` qua `edge-tts`) ra chuẩn `audio_16k_mono.wav`.
  2. Trích xuất đặc trưng sóng âm (`rms_envelope_per_frame`, `timeline_phases`) ở tốc độ 30fps.
  3. Chấm điểm Visual Feature Gate 1 (`evaluate_visual_feature_scores`).
  4. Kết xuất Video Motion Graphics / Manim 30fps (`final_master.mp4`) khớp trực tiếp với `visual_archetype`,
     `visual_labels` và lời bình 3 phần của chủ đề.
"""

import json
import re
import urllib.parse
import unicodedata
from typing import Dict, Any

from config.settings import POLLINATIONS_MODEL, IMAGE_WIDTH, IMAGE_HEIGHT, WORKSPACE_DIR
from graph.audio_sync import synthesize_voiceover_waveform, extract_waveform_sync_features
from graph.wav2vid_metrics import evaluate_visual_feature_scores
from graph.video_renderer import render_complete_scenery_video_with_audio
from graph.state import ChristianVideoState


def _slugify_vn(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "_", norm).strip("_")[:36] or "topic"


def media_generator_node(state: ChristianVideoState) -> Dict[str, Any]:
    topic_title = state.get("topic_title") or state.get("user_request", "Topic")[:40]
    visual_archetype = state.get("visual_archetype", "probability_trajectory")
    visual_labels = state.get("visual_labels") or ["Phần 1: Đặt vấn đề", "Phần 2: Cơ chế Cốt lõi", "Phần 3: Đúc kết"]
    scene_action = state.get("scene_action_prompt", "")

    # Lấy trực tiếp kịch bản 3 phần mà LLM đã viết ở Node 2
    scene_narration_vn = state.get("hook_and_context_vn", "").strip()
    outro_reflection_vn = state.get("deep_explanation_vn", "").strip()
    closing_prayer_vn = state.get("outro_takeaway_vn", "").strip()

    seed = abs(hash(topic_title)) % 800000 + 100000
    encoded_prompt = urllib.parse.quote(scene_action)
    generated_media_url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?model={POLLINATIONS_MODEL}&width={IMAGE_WIDTH}&height={IMAGE_HEIGHT}&seed={seed}&nologo=true"
    )

    # -----------------------------------------------------------------
    # BƯỚC 1: TẠO FILE DẠNG SÓNG `.WAV` TRONG `workspace/<run_id>/` & TRÍCH XUẤT FEATURE 30FPS
    # -----------------------------------------------------------------
    full_voiceover_script = f"{scene_narration_vn} ... {outro_reflection_vn} ... {closing_prayer_vn}"
    safe_slug = _slugify_vn(topic_title)
    run_id = f"run_{safe_slug}_{seed}"
    run_dir = WORKSPACE_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    wav_filename = f"{run_id}/audio_16k_mono.wav"

    wav_path = synthesize_voiceover_waveform(
        full_voiceover_text=full_voiceover_script,
        output_filename=wav_filename,
    )

    audio_sync_features = extract_waveform_sync_features(
        wav_path=wav_path,
        scene_narration=scene_narration_vn,
        outro_reflection=outro_reflection_vn,
        closing_prayer=closing_prayer_vn,
    )

    # -----------------------------------------------------------------
    # BƯỚC 2: CHỐT CHẶN 1 (`VisualFeatureScorer` + `ContinuityHarmonizer`)
    # -----------------------------------------------------------------
    visual_scores, last_frame_path, harmonized = evaluate_visual_feature_scores(
        scene_action_prompt=scene_action,
        seed=seed,
    )

    (run_dir / "visual_score_report.json").write_text(
        json.dumps(visual_scores, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # -----------------------------------------------------------------
    # BƯỚC 3: KẾT XUẤT VIDEO MOTION GRAPHICS 30FPS THEO `visual_archetype` CỦA LLM
    # -----------------------------------------------------------------
    video_mode = state.get("video_generation_mode") or "cinematic_3d_animation"
    rendered_files = render_complete_scenery_video_with_audio(
        run_dir=run_dir,
        wav_path=wav_path,
        audio_sync_features=audio_sync_features,
        scripture_reference=topic_title,
        retrieved_scripture=full_voiceover_script,
        visual_archetype=visual_archetype,
        visual_labels=visual_labels,
        scene_action_prompt=scene_action,
        seed=seed,
    )

    print(
        f"[Node 4: media_generator_node] Archetype={visual_archetype} | VisualScore={visual_scores['visual_total_score']} "
        f"| MasterClock={audio_sync_features['duration_sec']}s ({audio_sync_features['total_video_frames']} frames @ 30fps) "
        f"| Video={rendered_files['final_master_video_path']}"
    )

    return {
        "video_generation_mode": video_mode,
        "final_prompt": scene_action,
        "generated_media_url": generated_media_url,
        "active_seed": seed,
        "scene_narration_vn": scene_narration_vn,
        "outro_reflection_vn": outro_reflection_vn,
        "closing_prayer_vn": closing_prayer_vn,
        "voiceover_wav_path": str(wav_path),
        "subtitles_ass_path": rendered_files["subtitles_ass_path"],
        "prepped_visual_path": rendered_files["prepped_visual_path"],
        "final_master_video_path": rendered_files["final_master_video_path"],
        "audio_duration_sec": audio_sync_features["duration_sec"],
        "audio_sync_features": audio_sync_features,
        "prev_scene_frame_path": last_frame_path,
        "continuity_harmonized": harmonized,
        "visual_scores": visual_scores,
    }
