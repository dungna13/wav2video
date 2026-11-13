"""
Luồng bán tự động Google Flow (`graph/flow_bundler.py`).

1. `prepare_flow_workspace`:
   - Chạy sau Tầng 1 (`--flow-prep`): sinh audio VITS (`-14 LUFS`) + đo mốc thời gian thật từng cảnh.
   - Tự động gom các cảnh liên tiếp thành các Block vừa khít giới hạn giây của Google Flow (mặc định ~14s hoặc ~8s).
   - Xuất `flow_prompts.txt` (có Style Lock + Continuity Anchor nối tiếp từ frame cuối block trước) và `flow_manifest.json`.
2. `render_from_flow_clips`:
   - Đọc các clip `.mp4` bạn tải từ Google Flow vào `flow_clips/` (`1.mp4`, `2.mp4`, ...).
   - Không đánh giá để reject hay bắt tạo lại clip Flow (tránh tốn credit). Chỉ kiểm tra kỹ thuật + cân bằng màu
     nhẹ `ContinuityHarmonizer` + co giãn/cắt khớp audio + burn phụ đề karaoke CapCut -> `final_master.mp4`.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config.settings import MIN_CONTINUITY_SCORE, VIDEO_FPS, WORKSPACE_DIR
from graph.audio_sync import extract_waveform_sync_features, synthesize_scene_voiceover
from graph.nodes.media_generator import evaluate_real_visual_quality
from graph.nodes.visual_judge import visual_judge_and_update_registry_node
from graph.video_renderer import compute_scene_durations, render_flow_video
from graph.visual_scorer import VisualFeatureScorer, harmonize_scene_continuity


def _slugify_vn(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "_", norm).strip("_")[:36] or "topic"


def _natural_sort_key(path: Path) -> Tuple[int, str]:
    m = re.match(r"^(\d+)", path.stem)
    return (int(m.group(1)) if m else 10**9, path.name.lower())


def _assign_clips_to_blocks(
    found_clips: List[Path],
    blocks: List[Dict[str, Any]],
    total_audio_sec: float,
) -> List[Dict[str, Any]]:
    """
    Ghép clip Flow vào đúng Block:
      - Nếu file đặt tên kiểu `1.mp4`, `2.mp4`... -> ghép theo số thứ tự.
      - Nếu là tên gốc do Google Flow tự đặt (`Camera_pans_across_desert...mp4`) -> khớp theo từ khóa prompt của Block.
      - Nếu số clip ít hơn số Block (VD 6 clip cho 7 block) -> tự gộp phần thời lượng còn lại vào block cuối để không bị lỗi.
    """
    if len(found_clips) == 1:
        return [
            {
                "block_index": 1,
                "scene_indices": sorted({i for b in blocks for i in b["scene_indices"]}),
                "duration_sec": total_audio_sec,
                "media_path": str(found_clips[0]),
                "media_type": "video",
                "image_prompt_en": blocks[0]["flow_prompt"],
            }
        ]

    n_assign = min(len(found_clips), len(blocks))
    has_numeric_names = all(re.match(r"^\d+", p.stem) for p in found_clips[:n_assign])

    if has_numeric_names:
        ordered_clips = sorted(found_clips, key=_natural_sort_key)[:n_assign]
    else:
        stop_words = {"camera", "pans", "across", "tilts", "up", "down", "close", "of", "the", "a", "an", "with", "in", "on"}
        block_tokens = [set(re.findall(r"[a-z]{3,}", b["flow_prompt"].lower())) - stop_words for b in blocks[:n_assign]]
        clip_tokens = [set(re.findall(r"[a-z]{3,}", p.stem.lower())) - stop_words for p in found_clips]

        remaining_clips = list(range(len(found_clips)))
        assigned: List[Optional[Path]] = [None] * n_assign
        # Ưu tiên ghép cặp có độ khớp từ khóa cao nhất (tránh trùng 1 clip cho 2 block)
        pairs = []
        for bi in range(n_assign):
            for ci in remaining_clips:
                overlap = len(block_tokens[bi] & clip_tokens[ci])
                pairs.append((overlap, -ci, bi, ci))
        pairs.sort(reverse=True)
        used_b, used_c = set(), set()
        for overlap, _, bi, ci in pairs:
            if overlap <= 0 or bi in used_b or ci in used_c:
                continue
            assigned[bi] = found_clips[ci]
            used_b.add(bi)
            used_c.add(ci)
        leftover_clips = [found_clips[ci] for ci in range(len(found_clips)) if ci not in used_c]
        for bi in range(n_assign):
            if assigned[bi] is None and leftover_clips:
                assigned[bi] = leftover_clips.pop(0)
        ordered_clips = [p for p in assigned if p is not None]

    render_blocks: List[Dict[str, Any]] = []
    for idx in range(n_assign):
        blk = blocks[idx]
        render_blocks.append(
            {
                **blk,
                "media_path": str(ordered_clips[idx]),
                "media_type": "video",
                "image_prompt_en": blk["flow_prompt"],
            }
        )

    if len(blocks) > n_assign and render_blocks:
        extra_dur = sum(float(b["duration_sec"]) for b in blocks[n_assign:])
        extra_scenes = [i for b in blocks[n_assign:] for i in b["scene_indices"]]
        render_blocks[-1]["duration_sec"] = round(float(render_blocks[-1]["duration_sec"]) + extra_dur, 3)
        render_blocks[-1]["scene_indices"] = render_blocks[-1]["scene_indices"] + extra_scenes

    return render_blocks


def _split_balanced_groups(durations: List[float], k: int) -> List[List[int]]:
    """Chia `durations` thành đúng `k` nhóm liên tiếp sao cho độ dài mỗi nhóm cân bằng nhất."""
    n = len(durations)
    k = max(1, min(k, n))
    if k == n:
        return [[i] for i in range(n)]
    total = sum(durations)
    target = total / float(k)
    groups: List[List[int]] = []
    cur: List[int] = []
    acc = 0.0
    for idx, dur in enumerate(durations):
        rem_items = n - idx
        rem_groups = k - len(groups)
        if cur and rem_groups > 1 and (acc + dur * 0.5 > target or rem_items <= rem_groups - 1):
            groups.append(cur)
            cur = [idx]
            acc = dur
            # Cập nhật lại target theo phần thời lượng còn lại để các block cuối không bị dồn cục
            rem_total = sum(durations[idx:])
            target = rem_total / float(k - len(groups))
        else:
            cur.append(idx)
            acc += dur
    if cur:
        groups.append(cur)
    return groups


def bundle_scenes_for_flow(
    scenes: List[Dict[str, Any]],
    durations: List[float],
    style_anchor_en: str,
    intent_mode: str = "NO_HUMAN_BROLL",
    target_block_sec: float = 14.0,
    max_blocks: int = 4,
) -> List[Dict[str, Any]]:
    """Gom các cảnh liên tiếp thành tối đa `max_blocks` Block cân bằng (hoặc theo `target_block_sec`)."""
    if max_blocks > 0:
        groups = _split_balanced_groups(durations, max_blocks)
    else:
        groups = []
        cur_group: List[int] = []
        cur_dur = 0.0
        for idx, dur in enumerate(durations):
            if cur_group and (cur_dur + dur > target_block_sec):
                groups.append(cur_group)
                cur_group = [idx]
                cur_dur = dur
            else:
                cur_group.append(idx)
                cur_dur += dur
        if cur_group:
            groups.append(cur_group)

    no_human_suffix = ", no humans, no people, no faces" if intent_mode == "NO_HUMAN_BROLL" else ""
    style = (style_anchor_en or "cinematic documentary photography, natural lighting").strip().rstrip(".")

    blocks: List[Dict[str, Any]] = []
    t_cursor = 0.0
    for b_idx, idxs in enumerate(groups, 1):
        b_dur = round(sum(durations[i] for i in idxs), 3)
        t_start = round(t_cursor, 2)
        t_end = round(t_cursor + b_dur, 2)
        t_cursor += b_dur

        scene_descs = []
        for pos, sc_idx in enumerate(idxs):
            sc = scenes[sc_idx]
            cam = sc.get("camera", "zoom_in").replace("_", " ")
            p = str(sc.get("image_prompt_en", "")).strip().rstrip(".")
            if pos == 0:
                scene_descs.append(f"({cam}) {p}")
            else:
                scene_descs.append(f"smoothly transitioning ({cam}) into {p}")
        seq = "; ".join(scene_descs)

        if b_idx == 1:
            flow_prompt = (
                f"9:16 vertical cinematic documentary shot, {style}. "
                f"Continuous evolving camera sequence: {seq}. "
                f"No text, no watermark{no_human_suffix}."
            )
        else:
            flow_prompt = (
                f"9:16 vertical seamless continuation from the exact ending frame and lighting of the previous shot, {style}. "
                f"Continuous camera motion: {seq}. "
                f"Maintain identical color palette and atmosphere, no hard cut, no text, no watermark{no_human_suffix}."
            )

        blocks.append(
            {
                "block_index": b_idx,
                "scene_indices": [i + 1 for i in idxs],
                "start_sec": t_start,
                "end_sec": t_end,
                "duration_sec": b_dur,
                "narration_vn": " ".join(scenes[i]["narration_vn"] for i in idxs),
                "flow_prompt": flow_prompt,
            }
        )
    return blocks


def format_flow_prompts_txt(
    topic_title: str,
    intent_mode: str,
    total_audio_sec: float,
    blocks: List[Dict[str, Any]],
    clips_dir: Path,
    run_dir: Path,
) -> str:
    lines = [
        "=" * 88,
        f"GOOGLE FLOW PROMPTS — {topic_title}",
        f"Mode: {intent_mode} | Tổng audio: {total_audio_sec:.2f}s | Số block: {len(blocks)}",
        "=" * 88,
        "HƯỚNG DẪN:",
        f"  1. Mở Google Flow -> chọn tỷ lệ dọc 9:16.",
        f"  2. Block 1: tạo clip mới bằng Prompt Block 1.",
        f"  3. Từ Block 2 trở đi: bấm EXTEND trên clip trước (hoặc dùng frame cuối làm Start Frame)",
        f"     rồi dán Prompt Block tương ứng để giữ chuyển động liền mạch không vết cắt.",
        f"  4. Tải các clip về thư mục: {clips_dir}",
        f"     Đặt tên theo thứ tự: 1.mp4, 2.mp4, ... (hoặc 1 file dài duy nhất nếu bạn Extend liên hoàn).",
        f"  5. Chạy lệnh dựng phim:",
        f"     python main.py --flow-render \"{run_dir}\"",
        "=" * 88,
        "",
    ]
    for b in blocks:
        sc_range = f"Cảnh {b['scene_indices'][0]}" if len(b["scene_indices"]) == 1 else f"Cảnh {b['scene_indices'][0]}–{b['scene_indices'][-1]}"
        action = "TẠO CLIP MỚI" if b["block_index"] == 1 else "BẤM EXTEND / START FRAME TỪ CLIP TRƯỚC"
        lines += [
            f"--- BLOCK {b['block_index']}/{len(blocks)} | {sc_range} | Cần: {b['duration_sec']:.2f}s ({b['start_sec']}s -> {b['end_sec']}s) | [{action}] ---",
            f"Lời đọc: {b['narration_vn']}",
            "PROMPT COPY:",
            b["flow_prompt"],
            "",
        ]
    return "\n".join(lines)


def prepare_flow_workspace(
    state: Dict[str, Any],
    target_block_sec: float = 14.0,
    max_blocks: int = 4,
    base_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Chuẩn bị audio VITS (`-14 LUFS`), tính timeline từng cảnh, chia Block và xuất `flow_prompts.txt`."""
    topic_title = state.get("topic_title") or state.get("user_request", "Topic")[:40]
    scenes: List[Dict[str, Any]] = [dict(s) for s in (state.get("scenes") or [])]
    if not scenes:
        raise RuntimeError("prepare_flow_workspace: không có `scenes` từ Tầng 1.")

    root_ws = base_dir or WORKSPACE_DIR
    run_dir = root_ws / f"flow_{_slugify_vn(topic_title)}_{time.strftime('%m%d_%H%M%S')}"
    clips_dir = run_dir / "flow_clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

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
    durations = compute_scene_durations(timings, total_audio_sec)

    effective_mode = state.get("effective_intent_mode") or "NO_HUMAN_BROLL"
    blocks = bundle_scenes_for_flow(
        scenes=scenes,
        durations=durations,
        style_anchor_en=state.get("style_anchor_en", ""),
        intent_mode=effective_mode,
        target_block_sec=target_block_sec,
        max_blocks=max_blocks,
    )

    manifest = {
        "topic_title": topic_title,
        "genre": state.get("genre", ""),
        "narrative_model": state.get("narrative_model", ""),
        "intent_mode": state.get("intent_mode", effective_mode),
        "effective_intent_mode": effective_mode,
        "style_anchor_en": state.get("style_anchor_en", ""),
        "story_moral": state.get("story_moral", ""),
        "claims_to_verify": state.get("claims_to_verify", []),
        "average_score": state.get("average_score", 0.0),
        "book_id": state.get("book_id", ""),
        "book_chunk_idx": state.get("book_chunk_idx", 0),
        "wav_path": str(wav_path),
        "audio_duration_sec": total_audio_sec,
        "audio_sync_features": audio_sync_features,
        "timings": timings,
        "durations": durations,
        "scenes": scenes,
        "blocks": blocks,
        "clips_dir": str(clips_dir),
    }
    manifest_path = run_dir / "flow_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    prompts_txt = format_flow_prompts_txt(
        topic_title=topic_title,
        intent_mode=effective_mode,
        total_audio_sec=total_audio_sec,
        blocks=blocks,
        clips_dir=clips_dir,
        run_dir=run_dir,
    )
    prompts_path = run_dir / "flow_prompts.txt"
    prompts_path.write_text(prompts_txt, encoding="utf-8")

    return {
        "run_dir": str(run_dir),
        "clips_dir": str(clips_dir),
        "manifest_path": str(manifest_path),
        "prompts_path": str(prompts_path),
        "blocks": blocks,
        "audio_duration_sec": total_audio_sec,
    }


def render_from_flow_clips(
    run_dir: Path,
    clips_dir: Optional[Path] = None,
    sub_mode: str = "narration_full",
) -> Dict[str, Any]:
    """Dựng `final_master.mp4` từ các clip Google Flow (không reject/bắt tạo lại clip)."""
    manifest_path = run_dir / "flow_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Không tìm thấy `flow_manifest.json` trong: {run_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    src_dir = Path(clips_dir) if clips_dir else Path(manifest["clips_dir"])
    if not src_dir.exists():
        raise FileNotFoundError(f"Không tìm thấy thư mục chứa clip Google Flow: {src_dir}")

    exts = {".mp4", ".mov", ".webm", ".mkv"}
    found_clips = sorted([p for p in src_dir.iterdir() if p.is_file() and p.suffix.lower() in exts], key=_natural_sort_key)
    if not found_clips:
        raise RuntimeError(f"Thư mục `{src_dir}` chưa có file video nào (.mp4/.mov/.webm).")

    blocks: List[Dict[str, Any]] = [dict(b) for b in manifest["blocks"]]
    scenes: List[Dict[str, Any]] = [dict(s) for s in manifest["scenes"]]
    total_audio_sec = float(manifest["audio_duration_sec"])

    render_blocks = _assign_clips_to_blocks(found_clips, blocks, total_audio_sec)
    for b in render_blocks:
        print(f"   ├─ Block {b['block_index']} ({b['duration_sec']:.2f}s, cảnh {b['scene_indices']}): {Path(b['media_path']).name}")

    # Gắn nhãn nguồn cho từng scene để timeline/báo cáo rõ ràng
    for blk in render_blocks:
        for sc_num in blk["scene_indices"]:
            sc = scenes[sc_num - 1]
            sc["media_path"] = blk["media_path"]
            sc["media_type"] = "video"
            sc["media_source"] = f"google_flow({Path(blk['media_path']).name})"

    # Chỉ chạy ContinuityHarmonizer + đo kỹ thuật local (không dùng CLIP reject để tránh tốn credit Flow)
    scorer = VisualFeatureScorer(use_clip=False)
    harm_count, harm_evals = harmonize_scene_continuity(
        render_blocks,
        run_dir=run_dir,
        scorer=scorer,
        intent_mode=manifest.get("effective_intent_mode", "NO_HUMAN_BROLL"),
        min_continuity=MIN_CONTINUITY_SCORE,
    )
    if harm_count:
        print(f"[Flow Render] ContinuityHarmonizer đã cân bằng màu {harm_count} block clip.")

    asset_report = {
        "sources": [Path(b["media_path"]).name for b in render_blocks],
        "fallback_scenes": 0,
        "real_scenes": len(scenes),
        "flow_blocks": len(render_blocks),
        "stock_enabled": False,
    }
    visual_scores = evaluate_real_visual_quality(
        render_blocks,
        {**asset_report, "real_scenes": len(render_blocks)},
        intent_mode=manifest.get("effective_intent_mode", "NO_HUMAN_BROLL"),
        scorer=scorer,
        pre_evals=harm_evals,
    )
    (run_dir / "visual_score_report.json").write_text(
        json.dumps({**visual_scores, "asset_report": asset_report}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    rendered = render_flow_video(
        run_dir=run_dir,
        wav_path=Path(manifest["wav_path"]),
        scenes=scenes,
        blocks=render_blocks,
        timings=[tuple(t) for t in manifest["timings"]],
        total_audio_sec=total_audio_sec,
        topic_title=manifest["topic_title"],
        genre=manifest.get("genre", ""),
        sub_mode=sub_mode,
    )

    judge_state = visual_judge_and_update_registry_node(
        {
            "final_master_video_path": rendered["final_master_video_path"],
            "audio_duration_sec": total_audio_sec,
            "asset_report": asset_report,
            "visual_scores": visual_scores,
            "intent_mode": manifest.get("intent_mode", "NO_HUMAN_BROLL"),
            "audio_sync_features": manifest.get("audio_sync_features", {}),
            "story_moral": manifest.get("story_moral", ""),
            "visual_retry_count": 0,
        }
    )

    return {
        "manifest": manifest,
        "rendered": rendered,
        "visual_scores": visual_scores,
        "output_scores": judge_state["output_scores"],
        "tiktok_publish_status": judge_state["tiktok_publish_status"],
        "tiktok_caption": judge_state["tiktok_caption"],
        "continuity_harmonized": bool(harm_count > 0),
    }

