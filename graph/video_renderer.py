"""
Dựng phim tài liệu ngắn 9:16 từ danh sách CẢNH (`graph/video_renderer.py`).

Khác biệt so với bản cũ (1 ảnh lưới 2x2 cắt 4 mảnh + vẽ vector đè lên):
  1. Mỗi cảnh có hình riêng, độ dài lấy từ MỐC THỜI GIAN THẬT của giọng đọc (không chia đều, không ước lượng theo ký tự).
  2. Chuyển động máy quay thật bằng `zoompan` trên ảnh phóng lớn 2x (zoom_in/out, pan, tilt) — mượt, không nhảy pixel.
     Cảnh video stock (Pexels) được cắt/crop về 9:16 và giữ chuyển động gốc.
  3. Chuyển cảnh `xfade` kết thúc đúng lúc cảnh kế bắt đầu được đọc (hình đi trước lời một nhịp, như phim tài liệu).
  4. Hậu kỳ: chỉnh màu theo thể loại + vignette + film grain nhẹ.
  5. Phụ đề kiểu CapCut: nhóm 3 từ, từ đang đọc đổi màu (karaoke `\\k`) + hiệu ứng "pop"; từ khoá cảnh hiện ở phía trên.
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple

from config.settings import IMAGE_WIDTH, IMAGE_HEIGHT, VIDEO_FPS

TRANSITION_SEC = 0.35
MIN_SCENE_SEC = 1.2

GRADE_BY_GENRE = {
    "history_war": "eq=contrast=1.12:saturation=0.78:gamma=0.96",
    "history_culture": "eq=contrast=1.08:saturation=0.88:gamma=0.98",
    "true_story_crime": "eq=contrast=1.15:saturation=0.75:gamma=0.92",
    "economics_business": "eq=contrast=1.10:saturation=0.92",
    "science_nature": "eq=contrast=1.06:saturation=1.05",
    "tech_future": "eq=contrast=1.06:saturation=0.95",
    "psychology_philosophy": "eq=contrast=1.05:saturation=0.85:gamma=0.98",
    "lifestyle_motivation": "eq=contrast=1.05:saturation=1.0",
}


def _ffmpeg() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def _run(cmd: List[str], cwd: Path | None = None) -> None:
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd) if cwd else None)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg lỗi ({res.returncode}): {res.stderr[-1200:]}")


def compute_scene_durations(timings: List[Tuple[float, float]], total_sec: float) -> List[float]:
    """Độ dài hiển thị từng cảnh sao cho chuyển cảnh kết thúc đúng lúc lời cảnh kế bắt đầu."""
    n = len(timings)
    if n == 1:
        return [total_sec]
    bounds: List[float] = []
    prev = 0.0
    for k in range(n - 1):
        b = max(timings[k + 1][0] - TRANSITION_SEC, prev + MIN_SCENE_SEC)
        bounds.append(b)
        prev = b
    durs = [bounds[0]] + [bounds[k] - bounds[k - 1] for k in range(1, n - 1)] + [total_sec - bounds[-1]]
    return [max(d, MIN_SCENE_SEC) for d in durs]


def _camera_filter(camera: str, frames: int, w: int, h: int, fps: int) -> str:
    d = max(2, frames)
    base = f"zoompan=d={d}:s={w}x{h}:fps={fps}"
    cx = "x='iw/2-iw/zoom/2'"
    cy = "y='ih/2-ih/zoom/2'"
    moves = {
        "zoom_in": f"z='1+0.16*on/{d}':{cx}:{cy}",
        "zoom_out": f"z='1.16-0.16*on/{d}':{cx}:{cy}",
        "pan_left": f"z='1.15':x='(iw-iw/zoom)*(1-on/{d})':{cy}",
        "pan_right": f"z='1.15':x='(iw-iw/zoom)*on/{d}':{cy}",
        "tilt_up": f"z='1.15':{cx}:y='(ih-ih/zoom)*(1-on/{d})'",
        "tilt_down": f"z='1.15':{cx}:y='(ih-ih/zoom)*on/{d}'",
    }
    return f"{base}:{moves.get(camera, moves['zoom_in'])}"


def _make_scene_clip(scene: Dict[str, Any], out_path: Path, length: float, w: int, h: int, fps: int) -> None:
    ff = _ffmpeg()
    frames = int(round(length * fps))
    if scene.get("media_type") == "video":
        harm = f",{scene['color_harm_vf']}" if scene.get("color_harm_vf") else ""
        vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}{harm},fps={fps},setsar=1"
        cmd = [ff, "-y", "-stream_loop", "-1", "-i", scene["media_path"], "-t", f"{length:.3f}", "-vf", vf, "-an"]
    else:
        big_w, big_h = w * 2, h * 2
        vf = (
            f"scale={big_w}:{big_h}:force_original_aspect_ratio=increase:flags=lanczos,crop={big_w}:{big_h},"
            f"{_camera_filter(scene.get('camera', 'zoom_in'), frames, w, h, fps)},setsar=1"
        )
        cmd = [ff, "-y", "-i", scene["media_path"], "-vf", vf, "-frames:v", str(frames), "-an"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(fps), str(out_path)]
    _run(cmd)


def _to_ass_time(sec: float) -> str:
    sec = max(0.0, sec)
    cs_total = int(round(sec * 100))
    h, rem = divmod(cs_total, 360000)
    m, rem = divmod(rem, 6000)
    s, cs = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _word_weights(words: List[str]) -> List[float]:
    out = []
    for w in words:
        wt = max(2.0, float(len(w)))
        if w.endswith((".", "?", "!")):
            wt += 6.0
        elif w.endswith((",", ";", ":")):
            wt += 3.0
        out.append(wt)
    return out


def build_ass(
    scenes: List[Dict[str, Any]],
    timings: List[Tuple[float, float]],
    durations: List[float],
    w: int,
    h: int,
    title: str,
) -> str:
    font_size = int(h * 0.050)
    kicker_size = int(h * 0.030)
    lines = [
        "[Script Info]",
        f"Title: {title}",
        "ScriptType: v4.00+",
        f"PlayResX: {w}",
        f"PlayResY: {h}",
        "WrapStyle: 2",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Sub,DejaVu Sans,{font_size},&H0000D6FF,&H00FFFFFF,&H00101010,&H90000000,-1,0,0,0,100,100,0,0,1,{max(3, h // 220)},2,2,40,40,{int(h * 0.20)},1",
        f"Style: Kicker,DejaVu Sans,{kicker_size},&H0000D6FF,&H00FFFFFF,&H00101010,&H90000000,-1,0,0,0,100,100,4,0,1,3,1,8,40,40,{int(h * 0.085)},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    for sc, (t0, t1), dur in zip(scenes, timings, durations):
        kw = sc.get("overlay_keyword_vn", "").strip()
        if kw:
            k_start = t0
            k_end = min(t1, k_start + 2.6)
            lines.append(
                f"Dialogue: 1,{_to_ass_time(k_start)},{_to_ass_time(k_end)},Kicker,,0,0,0,,{{\\fad(220,220)}}{kw}"
            )

        sub_text = str(sc.get("subtitle_vn") or sc["narration_vn"]).strip()
        words = [x for x in re.sub(r"[{}\\]", "", sub_text).split() if x]
        if not words:
            continue
        weights = _word_weights(words)
        total_w = sum(weights)
        span = max(0.3, t1 - t0)
        starts, acc = [], t0
        for wt in weights:
            starts.append(acc)
            acc += span * wt / total_w
        ends = starts[1:] + [t1]

        i = 0
        while i < len(words):
            group_idx = [i]
            chars = len(words[i])
            while len(group_idx) < 3 and i + len(group_idx) < len(words) and chars + 1 + len(words[i + len(group_idx)]) <= 20:
                chars += 1 + len(words[i + len(group_idx)])
                group_idx.append(i + len(group_idx))
            g_start, g_end = starts[group_idx[0]], ends[group_idx[-1]]
            parts = []
            for j in group_idx:
                cs = max(1, int(round((ends[j] - starts[j]) * 100)))
                parts.append(f"{{\\k{cs}}}{words[j]}")
            pop = "{\\fad(40,30)\\fscx88\\fscy88\\t(0,110,\\fscx104\\fscy104)\\t(110,200,\\fscx100\\fscy100)}"
            lines.append(
                f"Dialogue: 0,{_to_ass_time(g_start)},{_to_ass_time(g_end + 0.04)},Sub,,0,0,0,,{pop}{' '.join(parts)}"
            )
            i = group_idx[-1] + 1
    return "\n".join(lines)


def _probe_clip_duration(video_path: Path) -> float:
    res = subprocess.run([_ffmpeg(), "-i", str(video_path)], capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
    if not m:
        return 0.0
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def _finalize_master_video(
    run_dir: Path,
    merged: Path,
    wav_path: Path,
    scenes: List[Dict[str, Any]],
    timings: List[Tuple[float, float]],
    durations: List[float],
    total_audio_sec: float,
    topic_title: str,
    genre: str,
    w: int,
    h: int,
    fps: int,
    cleanup_intermediates: bool,
    clips_to_clean: List[Path],
    delete_scene_media: bool = True,
) -> Dict[str, Any]:
    ff = _ffmpeg()
    ass_path = run_dir / "subtitles.ass"
    ass_path.write_text(build_ass(scenes, timings, durations, w, h, topic_title), encoding="utf-8")

    grade = GRADE_BY_GENRE.get(genre, "eq=contrast=1.06:saturation=0.95")
    vf = (
        f"{grade},vignette=angle=PI/5,noise=alls=4:allf=t,"
        f"fade=t=in:st=0:d=0.25,fade=t=out:st={max(0.0, total_audio_sec - 0.6):.2f}:d=0.6,"
        f"ass=subtitles.ass,format=yuv420p"
    )
    final_mp4 = run_dir / "final_master.mp4"
    _run(
        [ff, "-y", "-i", merged.name if merged.parent == run_dir else str(merged), "-i", str(wav_path), "-vf", vf,
         "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "medium", "-crf", "22", "-maxrate", "6M", "-bufsize", "12M", "-pix_fmt", "yuv420p",
         "-r", str(fps), "-c:a", "aac", "-b:a", "192k", "-shortest", final_mp4.name],
        cwd=run_dir,
    )

    timeline = [
        {
            "scene": i + 1,
            "narration_vn": sc["narration_vn"],
            "subtitle_vn": sc.get("subtitle_vn", sc["narration_vn"]),
            "voice_start": timings[i][0],
            "voice_end": timings[i][1],
            "visible_sec": round(durations[i], 2),
            "camera": sc.get("camera"),
            "sfx_cue": sc.get("sfx_cue", "none"),
            "media_type": sc.get("media_type"),
            "media_source": sc.get("media_source"),
            "image_prompt_en": sc["image_prompt_en"],
        }
        for i, sc in enumerate(scenes)
    ]
    (run_dir / "scene_timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")

    if cleanup_intermediates and final_mp4.exists() and final_mp4.stat().st_size > 100_000:
        resolved_run = run_dir.resolve()
        for c in clips_to_clean:
            if c.resolve().parent == resolved_run:
                c.unlink(missing_ok=True)
        merged_file = run_dir / "raw_visual_merged.mp4"
        if merged_file.resolve().parent == resolved_run:
            merged_file.unlink(missing_ok=True)
        if delete_scene_media:
            for sc in scenes:
                mp = Path(str(sc.get("media_path", "")))
                if mp.name.startswith("scene_") and mp.resolve().parent == resolved_run:
                    mp.unlink(missing_ok=True)

    return {
        "final_master_video_path": str(final_mp4),
        "subtitles_ass_path": str(ass_path),
        "prepped_visual_path": "",
        "contact_sheet_path": "",
        "scene_timeline_path": str(run_dir / "scene_timeline.json"),
        "video_fps": fps,
        "duration_sec": total_audio_sec,
    }


def _merge_clips_xfade(clips: List[Path], clip_durations: List[float], out_path: Path, fps: int) -> Path:
    if len(clips) == 1:
        return clips[0]
    ff = _ffmpeg()
    inputs: List[str] = []
    for c in clips:
        inputs += ["-i", str(c)]
    chain, prev_label, offset = [], "[0:v]", 0.0
    for k in range(1, len(clips)):
        offset += clip_durations[k - 1]
        out_label = f"[x{k}]" if k < len(clips) - 1 else "[vout]"
        chain.append(f"{prev_label}[{k}:v]xfade=transition=fade:duration={TRANSITION_SEC}:offset={offset:.3f}{out_label}")
        prev_label = out_label
    _run(
        [ff, "-y", *inputs, "-filter_complex", ";".join(chain), "-map", "[vout]", "-c:v", "libx264",
         "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(fps), str(out_path)]
    )
    return out_path


def render_flow_video(
    run_dir: Path,
    wav_path: Path,
    scenes: List[Dict[str, Any]],
    blocks: List[Dict[str, Any]],
    timings: List[Tuple[float, float]],
    total_audio_sec: float,
    topic_title: str,
    genre: str = "",
    fps: int = VIDEO_FPS,
    cleanup_intermediates: bool = True,
) -> Dict[str, Any]:
    """Dựng `final_master.mp4` từ các clip liền mạch (Google Flow) giữ nguyên mạch chạy của từng Block."""
    w, h = IMAGE_WIDTH, IMAGE_HEIGHT
    ff = _ffmpeg()
    durations = compute_scene_durations(timings, total_audio_sec)
    n_blocks = len(blocks)

    prep_clips: List[Path] = []
    block_durs: List[float] = []
    for i, blk in enumerate(blocks):
        b_dur = float(blk["duration_sec"])
        block_durs.append(b_dur)
        target_len = b_dur + (TRANSITION_SEC if i < n_blocks - 1 else 0.0)
        src_path = Path(blk["media_path"])
        src_dur = _probe_clip_duration(src_path)
        harm = f",{blk['color_harm_vf']}" if blk.get("color_harm_vf") else ""

        out_clip = run_dir / f"flow_prep_clip_{i + 1}.mp4"
        if 0.0 < src_dur < target_len and src_dur >= target_len * 0.65:
            ratio = target_len / src_dur
            vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}{harm},setpts={ratio:.4f}*PTS,fps={fps},setsar=1"
            cmd = [ff, "-y", "-i", str(src_path), "-t", f"{target_len:.3f}", "-vf", vf, "-an"]
        elif 0.0 < src_dur < target_len * 0.65:
            vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}{harm},fps={fps},setsar=1"
            cmd = [ff, "-y", "-stream_loop", "-1", "-i", str(src_path), "-t", f"{target_len:.3f}", "-vf", vf, "-an"]
        else:
            vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}{harm},fps={fps},setsar=1"
            cmd = [ff, "-y", "-i", str(src_path), "-t", f"{target_len:.3f}", "-vf", vf, "-an"]
        cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(fps), str(out_clip)]
        _run(cmd)
        prep_clips.append(out_clip)

    merged = _merge_clips_xfade(prep_clips, block_durs, run_dir / "raw_visual_merged.mp4", fps)
    return _finalize_master_video(
        run_dir=run_dir,
        merged=merged,
        wav_path=wav_path,
        scenes=scenes,
        timings=timings,
        durations=durations,
        total_audio_sec=total_audio_sec,
        topic_title=topic_title,
        genre=genre,
        w=w,
        h=h,
        fps=fps,
        cleanup_intermediates=cleanup_intermediates,
        clips_to_clean=prep_clips,
        delete_scene_media=False,
    )


def render_documentary_video(
    run_dir: Path,
    wav_path: Path,
    scenes: List[Dict[str, Any]],
    timings: List[Tuple[float, float]],
    total_audio_sec: float,
    topic_title: str,
    genre: str = "",
    fps: int = VIDEO_FPS,
    cleanup_intermediates: bool = True,
) -> Dict[str, Any]:
    """Dựng `final_master.mp4` từ các cảnh đã có `media_path`, `camera`, `narration_vn`."""
    w, h = IMAGE_WIDTH, IMAGE_HEIGHT
    durations = compute_scene_durations(timings, total_audio_sec)
    n = len(scenes)

    clips: List[Path] = []
    for i, (sc, dur) in enumerate(zip(scenes, durations)):
        length = dur + (TRANSITION_SEC if i < n - 1 else 0.0)
        clip = run_dir / f"clip_{i + 1}.mp4"
        _make_scene_clip(sc, clip, length, w, h, fps)
        clips.append(clip)

    merged = _merge_clips_xfade(clips, durations, run_dir / "raw_visual_merged.mp4", fps)
    return _finalize_master_video(
        run_dir=run_dir,
        merged=merged,
        wav_path=wav_path,
        scenes=scenes,
        timings=timings,
        durations=durations,
        total_audio_sec=total_audio_sec,
        topic_title=topic_title,
        genre=genre,
        w=w,
        h=h,
        fps=fps,
        cleanup_intermediates=cleanup_intermediates,
        clips_to_clean=clips,
        delete_scene_media=True,
    )
