"""Unit tests for Phase 2 Step 1 & Step 2 (multi-candidate anti-duplicate fetcher & VisualFeatureScorer)."""

import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import imageio_ffmpeg
import numpy as np
from PIL import Image

from graph import asset_fetcher
from graph.flow_bundler import prepare_flow_workspace, render_from_flow_clips
from graph.nodes import media_generator
from graph.nodes.media_generator import evaluate_real_visual_quality, media_generator_node
from graph.nodes.visual_judge import visual_judge_and_update_registry_node
from graph.visual_scorer import (
    VisualFeatureScorer,
    compute_pair_continuity,
    harmonize_scene_continuity,
)


def _make_test_mp4(path: Path, dark: bool = False, static: bool = False) -> None:
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    if dark:
        src = "color=c=black:s=270x480:d=2.2"
    elif static:
        src = "testsrc2=s=270x480:r=15:d=0.1,tpad=stop_mode=clone:stop_duration=2.1"
    else:
        src = "testsrc2=s=270x480:r=15:d=2.2"
    cmd = [ff, "-y", "-v", "error", "-f", "lavfi", "-i", src, "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)]
    subprocess.run(cmd, check=True)


def _make_test_jpg(path: Path, color=(180, 130, 80)) -> None:
    arr = np.zeros((480, 270, 3), dtype=np.uint8)
    arr[:, :] = color
    arr[50:400:12, 30:240] = (230, 210, 170)
    Image.fromarray(arr).save(path)


class TestVisualPhase2(unittest.TestCase):
    def test_mixkit_terms_and_human_hint(self):
        terms_no_human = asset_fetcher._mixkit_terms("soldier walking military", no_human=True)
        self.assertNotIn("man", terms_no_human)
        self.assertNotIn("crowd", terms_no_human)
        self.assertIn("helmet", terms_no_human)
        self.assertTrue(asset_fetcher._has_human_hint("portrait-of-smiling-woman-123"))
        self.assertFalse(asset_fetcher._has_human_hint("golden-sand-dunes-sunset-456"))

    def test_scorer_detects_dark_static_and_moving_video(self):
        scorer = VisualFeatureScorer(use_clip=False)
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            dark_mp4 = t / "dark.mp4"
            static_mp4 = t / "static.mp4"
            good_mp4 = t / "good.mp4"
            _make_test_mp4(dark_mp4, dark=True)
            _make_test_mp4(static_mp4, static=True)
            _make_test_mp4(good_mp4, dark=False, static=False)

            ev_dark = scorer.inspect_media(dark_mp4, "video")
            self.assertTrue(ev_dark["is_dark"])
            self.assertIn("frame_qua_toi", ev_dark["reject_reasons"])

            ev_static = scorer.inspect_media(static_mp4, "video")
            self.assertTrue(ev_static["is_static"])
            self.assertIn("video_dung_hinh", ev_static["reject_reasons"])

            ev_good = scorer.inspect_media(good_mp4, "video")
            self.assertFalse(ev_good["is_corrupt"])
            self.assertFalse(ev_good["is_dark"])
            self.assertFalse(ev_good["is_static"])
            self.assertGreater(ev_good["sharpness_score"], 0.5)
            self.assertGreater(ev_good["motion_diff"], 1.2)

    def test_multi_candidate_anti_duplicate_and_visual_eval(self):
        scorer = VisualFeatureScorer(use_clip=False)
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            dark_mp4 = t / "src_dark.mp4"
            good1_mp4 = t / "src_good1.mp4"
            good2_mp4 = t / "src_good2.mp4"
            _make_test_mp4(dark_mp4, dark=True)
            _make_test_mp4(good1_mp4)
            _make_test_mp4(good2_mp4)

            cands = [
                {"provider": "mixkit_video", "asset_id": "mixkit:100", "url": "mock://dark", "label": "desert"},
                {"provider": "mixkit_video", "asset_id": "mixkit:200", "url": "mock://good1", "label": "desert"},
                {"provider": "mixkit_video", "asset_id": "mixkit:300", "url": "mock://good2", "label": "temple"},
            ]

            def fake_collect(query, width, height, used_ids, no_human, limit=5):
                return [c for c in cands if c["asset_id"] not in used_ids]

            def fake_download(url, dest: Path) -> bool:
                src_map = {"mock://dark": dark_mp4, "mock://good1": good1_mp4, "mock://good2": good2_mp4}
                dest.write_bytes(src_map[url].read_bytes())
                return True

            scenes = [
                {"narration_vn": "Cảnh 1 sa mạc", "image_prompt_en": "wide golden desert", "stock_query_en": "desert"},
                {"narration_vn": "Cảnh 2 đền cổ", "image_prompt_en": "ancient stone temple", "stock_query_en": "temple"},
            ]

            run_dir = t / "run"
            run_dir.mkdir()
            with (
                patch.object(asset_fetcher, "_online", return_value=False),
                patch.object(asset_fetcher, "_collect_stock_candidates", side_effect=fake_collect),
                patch.object(asset_fetcher, "_download_video", side_effect=fake_download),
            ):
                report = asset_fetcher.fetch_scene_assets(
                    scenes,
                    style_anchor_en="cinematic",
                    run_dir=run_dir,
                    seed=42,
                    width=270,
                    height=480,
                    intent_mode="NO_HUMAN_BROLL",
                    scorer=scorer,
                )

            self.assertEqual(scenes[0]["asset_id"], "mixkit:200")
            self.assertEqual(scenes[1]["asset_id"], "mixkit:300")
            self.assertEqual(report["unique_stock_assets"], 2)
            self.assertEqual(report["fallback_scenes"], 0)

            scores = evaluate_real_visual_quality(scenes, report, intent_mode="NO_HUMAN_BROLL", scorer=scorer)
            self.assertEqual(scores["scored_videos"], 2)
            self.assertIsNone(scores["clip_prompt_score"])
            self.assertGreater(scores["visual_total_score"], 0.7)
            json.dumps(scenes)  # Bảo đảm serialize được vào SqliteSaver của LangGraph

    def test_clip_human_rejection_and_scoring(self):
        scorer = VisualFeatureScorer(use_clip=True)
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            human_mp4 = t / "human.mp4"
            clean_mp4 = t / "clean.mp4"
            _make_test_mp4(human_mp4)
            _make_test_mp4(clean_mp4)

            cands = [
                {"provider": "mixkit_video", "asset_id": "mixkit:1", "url": "mock://human", "label": "street"},
                {"provider": "mixkit_video", "asset_id": "mixkit:2", "url": "mock://clean", "label": "desert"},
            ]

            def fake_clip(frames, prompt_en, check_human):
                # Lần đầu (human_mp4) trả về dính người; lần 2 (clean_mp4) khớp prompt sạch
                if not hasattr(fake_clip, "calls"):
                    fake_clip.calls = 0
                fake_clip.calls += 1
                if fake_clip.calls == 1:
                    return (0.29, True, 0.85)
                return (0.31, False, 0.12)

            def fake_download(url, dest: Path) -> bool:
                dest.write_bytes((human_mp4 if url == "mock://human" else clean_mp4).read_bytes())
                return True

            scenes = [{"narration_vn": "Sa mạc", "image_prompt_en": "golden desert dunes", "stock_query_en": "desert"}]
            run_dir = t / "run"
            run_dir.mkdir()
            with (
                patch.object(scorer, "_clip_scores", side_effect=fake_clip),
                patch.object(asset_fetcher, "_online", return_value=False),
                patch.object(asset_fetcher, "_collect_stock_candidates", return_value=cands),
                patch.object(asset_fetcher, "_download_video", side_effect=fake_download),
            ):
                report = asset_fetcher.fetch_scene_assets(
                    scenes,
                    style_anchor_en="cinematic",
                    run_dir=run_dir,
                    seed=7,
                    width=270,
                    height=480,
                    intent_mode="NO_HUMAN_BROLL",
                    scorer=scorer,
                )
                scores = evaluate_real_visual_quality(scenes, report, intent_mode="NO_HUMAN_BROLL", scorer=scorer)

            self.assertEqual(scenes[0]["asset_id"], "mixkit:2")
            self.assertEqual(scores["clip_prompt_score"], 0.31)
            self.assertEqual(scores["human_violation_scenes"], 0)
            self.assertIsNone(scores["failure_reason"])

    def test_continuity_harmonizer_and_lutrgb_render(self):
        scorer = VisualFeatureScorer(use_clip=False)
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            img1 = t / "scene_1.jpg"
            _make_test_jpg(img1, color=(225, 165, 85))

            vid2 = t / "scene_2.mp4"
            ff = imageio_ffmpeg.get_ffmpeg_exe()
            subprocess.run(
                [ff, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=0x1E468C:s=270x480:d=2.2", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(vid2)],
                check=True,
            )

            scenes = [
                {"narration_vn": "Cảnh ấm", "image_prompt_en": "warm sunlit sand", "media_path": str(img1), "media_type": "image", "camera": "zoom_in"},
                {"narration_vn": "Cảnh chuyển", "image_prompt_en": "night canyon", "media_path": str(vid2), "media_type": "video", "camera": "pan_left"},
            ]
            before_e0 = scorer.inspect_media(img1, "image")
            before_e1 = scorer.inspect_media(vid2, "video")
            before_cont = compute_pair_continuity(before_e0, before_e1)

            harm_count, evals = harmonize_scene_continuity(scenes, run_dir=t, scorer=scorer, min_continuity=0.75)
            after_cont = compute_pair_continuity(evals[0], evals[1])

            self.assertGreaterEqual(harm_count, 1)
            self.assertTrue(scenes[1].get("continuity_harmonized"))
            self.assertIn("lutrgb=", scenes[1].get("color_harm_vf", ""))
            self.assertGreater(after_cont, before_cont)

    def test_e2e_phase2_audio_lufs_and_media_node(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            ws = t / "workspace"
            ws.mkdir()

            def _make_fake_assets(scenes, style_anchor, run_dir, seed, w, h, intent_mode="NO_HUMAN_BROLL", scorer=None):
                p1 = run_dir / "scene_1.jpg"
                p2 = run_dir / "scene_2.mp4"
                _make_test_jpg(p1, color=(190, 145, 90))
                _make_test_mp4(p2)
                scenes[0].update(media_path=str(p1), media_type="image", media_source="ai_image")
                scenes[1].update(media_path=str(p2), media_type="video", media_source="mixkit_video")
                return {"sources": ["ai_image", "mixkit_video"], "fallback_scenes": 0, "real_scenes": 2}

            state_in = {
                "user_request": "Kiểm thử toàn trình tầng 2",
                "topic_title": "Test Phase 2 E2E",
                "genre": "history_culture",
                "effective_intent_mode": "NO_HUMAN_BROLL",
                "intent_mode": "NO_HUMAN_BROLL",
                "style_anchor_en": "warm documentary",
                "music_mood": "calm contemplation",
                "story_moral": "Kiểm thử đồng bộ âm thanh và hình ảnh.",
                "scenes": [
                    {
                        "narration_vn": "Sa mạc luôn giữ im lặng.",
                        "subtitle_vn": "Sa mạc luôn giữ im lặng.",
                        "image_prompt_en": "golden sand dunes at sunset",
                        "stock_query_en": "desert sunset",
                        "camera": "zoom_in",
                        "overlay_keyword_vn": "SA MẠC",
                        "sfx_cue": "wind_swell",
                    },
                    {
                        "narration_vn": "Nhưng bên trong là cả hành trình.",
                        "subtitle_vn": "Nhưng bên trong là cả hành trình.",
                        "image_prompt_en": "ancient stone path",
                        "stock_query_en": "stone path",
                        "camera": "pan_right",
                        "overlay_keyword_vn": "HÀNH TRÌNH",
                        "sfx_cue": "low_thud",
                    },
                ],
            }

            with (
                patch.object(media_generator, "WORKSPACE_DIR", ws),
                patch.object(media_generator, "fetch_scene_assets", side_effect=_make_fake_assets),
                patch.object(media_generator, "VisualFeatureScorer", return_value=VisualFeatureScorer(use_clip=False)),
            ):
                out_m = media_generator_node(state_in)

            # Kiểm tra chuẩn -14 LUFS trên audio_16k_mono.wav bằng ffmpeg loudnorm measure
            ff = imageio_ffmpeg.get_ffmpeg_exe()
            probe = subprocess.run(
                [ff, "-i", out_m["voiceover_wav_path"], "-af", "loudnorm=I=-14:TP=-1.0:LRA=11:print_format=summary", "-f", "null", "-"],
                capture_output=True,
                text=True,
                check=True,
            )
            m_lufs = re.search(r"Input Integrated:\s*(-?\d+\.\d+)\s*LUFS", probe.stderr)
            self.assertIsNotNone(m_lufs)
            measured_lufs = float(m_lufs.group(1))
            self.assertGreaterEqual(measured_lufs, -16.5)
            self.assertLessEqual(measured_lufs, -11.5)

            # Chạy Node 5 (visual_judge) kiểm định đầu ra video thật
            judge_out = visual_judge_and_update_registry_node({**state_in, **out_m})
            self.assertTrue(Path(out_m["final_master_video_path"]).exists())
            self.assertLessEqual(abs(judge_out["output_scores"]["av_offset_frames"]), 10)
            self.assertEqual(judge_out["tiktok_publish_status"], "READY_FOR_MANUAL_REVIEW")

    def test_flow_prep_and_flow_render_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            ws = t / "workspace"
            ws.mkdir()
            state_in = {
                "user_request": "Flow test",
                "topic_title": "Flow Test Sahara",
                "genre": "science_nature",
                "intent_mode": "NO_HUMAN_BROLL",
                "effective_intent_mode": "NO_HUMAN_BROLL",
                "style_anchor_en": "National Geographic documentary lighting, 9:16 vertical",
                "music_mood": "ambient",
                "story_moral": "Kiểm thử Google Flow pipeline.",
                "scenes": [
                    {
                        "narration_vn": "Sa mạc luôn ẩn chứa bí mật.",
                        "subtitle_vn": "Sa mạc luôn ẩn chứa bí mật.",
                        "image_prompt_en": "golden desert dunes at dawn",
                        "camera": "zoom_in",
                        "overlay_keyword_vn": "BÍ MẬT",
                        "sfx_cue": "wind_swell",
                    },
                    {
                        "narration_vn": "Bên dưới lớp cát là dấu tích cổ đại.",
                        "subtitle_vn": "Bên dưới lớp cát là dấu tích cổ đại.",
                        "image_prompt_en": "ancient carved stone ruins under sand",
                        "camera": "pan_left",
                        "overlay_keyword_vn": "DẤU TÍCH",
                        "sfx_cue": "low_thud",
                    },
                    {
                        "narration_vn": "Thiên nhiên thay đổi nhanh hơn ta tưởng.",
                        "subtitle_vn": "Thiên nhiên thay đổi nhanh hơn ta tưởng.",
                        "image_prompt_en": "rain clouds gathering over arid canyon",
                        "camera": "zoom_out",
                        "overlay_keyword_vn": "THAY ĐỔI",
                        "sfx_cue": "none",
                    },
                ],
            }

            prep = prepare_flow_workspace(state_in, target_block_sec=3.5, base_dir=ws)
            run_dir = Path(prep["run_dir"])
            clips_dir = Path(prep["clips_dir"])
            self.assertTrue(Path(prep["prompts_path"]).exists())
            self.assertTrue(Path(prep["manifest_path"]).exists())
            self.assertGreaterEqual(len(prep["blocks"]), 2)
            prompts_text = Path(prep["prompts_path"]).read_text(encoding="utf-8")
            self.assertIn("BLOCK 1/", prompts_text)
            self.assertIn("seamless continuation", prompts_text)

            # Tạo các clip giả lập tải từ Google Flow (1.mp4, 2.mp4, ...)
            for b in prep["blocks"]:
                _make_test_mp4(clips_dir / f"{b['block_index']}.mp4")

            res = render_from_flow_clips(run_dir)
            self.assertTrue(Path(res["rendered"]["final_master_video_path"]).exists())
            self.assertLessEqual(abs(res["output_scores"]["av_offset_frames"]), 10)
            self.assertEqual(res["tiktok_publish_status"], "READY_FOR_MANUAL_REVIEW")


if __name__ == "__main__":
    unittest.main()
