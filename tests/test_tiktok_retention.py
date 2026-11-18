"""
Unit & Integration Tests for TikTok Retention Enhancements (`tests/test_tiktok_retention.py`).

Kiểm thử toàn bộ các tính năng P1 và TikTok Retention:
  1. Voice Profiles & CLI Switcher (`graph/audio_sync.py`)
  2. Subtitle Styles & Safe Zone ASS generation (`graph/video_renderer.py`)
  3. TikTok Cover Thumbnail Auto-generation (`generate_tiktok_cover`)
  4. Post Info & Caption Exporter (`export_post_info`)
  5. CLI Argument Parsing for TikTok flags (`main.py`)
"""

import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from PIL import Image

import imageio_ffmpeg

from graph.audio_sync import list_available_voices, print_voices_table, VOICE_PROFILES
from graph.video_renderer import (
    SUBTITLE_STYLES,
    build_ass,
    generate_tiktok_cover,
    export_post_info,
)
from main import _parse_args


def _make_dummy_mp4(out_path: Path, width: int = 720, height: int = 1280, duration: float = 2.0) -> None:
    """Tạo một file video MP4 nhẹ 9:16 để phục vụ kiểm thử."""
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    src = f"testsrc=size={width}x{height}:rate=24"
    cmd = [
        ff, "-y", "-v", "error",
        "-f", "lavfi", "-i", src,
        "-t", f"{duration:.2f}",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)


class TestTikTokVoiceProfiles(unittest.TestCase):
    """Kiểm tra kho giọng đọc tiếng Việt và bộ hiển thị CLI."""

    def test_voice_profiles_complete(self):
        voices = list_available_voices()
        required_keys = [
            "review_phim", "gen_z", "giat_gan", "nam_review",
            "hoai_my", "nam_tram", "nu_nhe_nhang", "nu_tre", "nam_tre", "nam_minh"
        ]
        for key in required_keys:
            self.assertIn(key, voices, f"Thiếu profile giọng: {key}")
            self.assertIn("voice", voices[key])
            self.assertIn("pitch", voices[key])
            self.assertIn("desc", voices[key])

    def test_default_voice_is_hoai_my(self):
        self.assertEqual(VOICE_PROFILES["hoai_my"]["voice"], "vi-VN-HoaiMyNeural")
        self.assertEqual(VOICE_PROFILES["hoai_my"]["pitch"], "+0Hz")

    def test_print_voices_table_runs(self):
        # Đảm bảo hàm in bảng tra cứu chạy thành công không ném ngoại lệ
        try:
            print_voices_table()
        except Exception as e:
            self.fail(f"print_voices_table() gặp lỗi: {e}")


class TestTikTokSubtitles(unittest.TestCase):
    """Kiểm tra định dạng phụ đề ASS, vùng an toàn (Safe Zone) và phong cách màu sắc."""

    def test_subtitle_styles_exist(self):
        self.assertIn("tiktok_yellow", SUBTITLE_STYLES)
        self.assertIn("tiktok_white", SUBTITLE_STYLES)
        self.assertIn("tiktok_cyan", SUBTITLE_STYLES)

    def test_build_ass_safe_zone_and_formatting(self):
        w, h = 720, 1280
        scenes = [
            {
                "scene_idx": 1,
                "narration_vn": "Sự thật trớ trêu đằng sau thành công mà 99% mọi người đều hiểu sai.",
                "subtitle_vn": "Sự thật trớ trêu đằng sau thành công mà 99% mọi người đều hiểu sai.",
            }
        ]
        timings = [(0.0, 3.5)]
        durations = [3.5]

        ass_content = build_ass(
            scenes=scenes,
            timings=timings,
            durations=durations,
            w=w,
            h=h,
            title="TEST TIKTOK",
            sub_style="tiktok_yellow",
        )

        self.assertIn("[Script Info]", ass_content)
        self.assertIn("[V4+ Styles]", ass_content)
        self.assertIn("Style: Sub,Arial", ass_content)

        # Kiểm tra Safe Zone: MarginV >= 280px để không bị che bởi caption/thanh seekbar TikTok
        expected_margin_v = int(h * 0.22)  # 281px
        self.assertIn(f",55,55,{expected_margin_v},1", ass_content)

        # Kiểm tra màu vàng TikTok rực rỡ (&H0000E5FF)
        self.assertIn(SUBTITLE_STYLES["tiktok_yellow"]["primary"], ass_content)

        # Kiểm tra sự xuất hiện của tag karaoke {\k...}
        self.assertIn(r"{\k", ass_content)


class TestTikTokCoverAndPostInfo(unittest.TestCase):
    """Kiểm tra tạo ảnh bìa TikTok Thumbnail và xuất file thông tin đăng post_info.txt."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_generate_tiktok_cover(self):
        mp4_path = self.dir_path / "test_video.mp4"
        _make_dummy_mp4(mp4_path, width=720, height=1280, duration=2.0)

        cover_path = self.dir_path / "cover.jpg"
        res = generate_tiktok_cover(mp4_path, "BÍ MẬT CỦA SỰ THÀNH CÔNG", cover_path)

        self.assertIsNotNone(res)
        self.assertTrue(cover_path.exists())
        self.assertGreater(cover_path.stat().st_size, 1000)

        # Kiểm tra kích thước ảnh đúng chuẩn 720x1280
        with Image.open(cover_path) as im:
            self.assertEqual(im.size, (720, 1280))

    def test_export_post_info(self):
        mp4_path = self.dir_path / "final_master_clean.mp4"
        mp4_path.touch()

        scenes = [
            {
                "narration_vn": "99% chúng ta đang lãng phí 80% thời gian vào những việc vô nghĩa.",
            }
        ]
        post_path = export_post_info(
            run_dir=self.dir_path,
            topic_title="ĐỊNH LUẬT 80 20 VÀ NGHỊCH LÝ THỜI GIAN",
            scenes=scenes,
            total_audio_sec=28.5,
            video_path=mp4_path,
        )

        self.assertTrue(post_path.exists())
        content = post_path.read_text(encoding="utf-8")

        # Kiểm tra các mục trọng tâm trong file post_info.txt
        self.assertIn("THÔNG TIN ĐĂNG TIKTOK", content)
        self.assertIn("ĐỊNH LUẬT 80 20 VÀ NGHỊCH LÝ THỜI GIAN", content)
        self.assertIn("HOOK 3 GIÂY ĐẦU TIÊN", content)
        self.assertIn("#learnontiktok", content)
        self.assertIn("MẸO ĐĂNG TRÊN ĐIỆN THOẠI ĐỂ 100% KHÔNG BỊ GẮN NHÃN AI", content)


class TestCliArgsParsing(unittest.TestCase):
    """Kiểm tra phân tích cú pháp tham số CLI trong main.py."""

    def test_voice_flag(self):
        opts = _parse_args(["--voice", "nam_tram", "Chủ đề thử nghiệm"])
        self.assertEqual(opts["voice"], "nam_tram")
        self.assertEqual(opts["topic"], "Chủ đề thử nghiệm")

    def test_list_voices_flag(self):
        opts = _parse_args(["--list-voices"])
        self.assertTrue(opts["list_voices"])

    def test_sub_style_flag(self):
        opts = _parse_args(["--sub-style", "tiktok_white", "Chủ đề"])
        self.assertEqual(opts["sub_style"], "tiktok_white")

    def test_batch_flag(self):
        opts = _parse_args(["--batch", "my_topics.txt", "--sub-style", "tiktok_yellow"])
        self.assertEqual(opts["batch"], "my_topics.txt")
        self.assertTrue(opts["flow_prep"])


class TestOmniFlowPromptSanitization(unittest.TestCase):
    """Kiểm tra bộ lọc prompt cho Google Flow (Gemini Omni 1.2 Flash) chống dính markdown / chữ lên video."""

    def test_strip_markdown_and_parentheses(self):
        from graph.flow_bundler import _clean_for_omni, _camera_to_natural_prose

        raw_text = "**cinematic** photo of (zoom in) [sharp focus] `a businessman` talking #startup."
        clean = _clean_for_omni(raw_text)
        self.assertNotIn("*", clean)
        self.assertNotIn("(", clean)
        self.assertNotIn(")", clean)
        self.assertNotIn("[", clean)
        self.assertNotIn("]", clean)
        self.assertNotIn("`", clean)
        self.assertNotIn("#", clean)

        cam_first = _camera_to_natural_prose("zoom_in", is_first=True)
        self.assertIn("The camera slowly zooms in", cam_first)
        self.assertNotIn("(", cam_first)

        cam_next = _camera_to_natural_prose("pan_right", is_first=False)
        self.assertIn("smoothly panning right", cam_next)
        self.assertNotIn("(", cam_next)

    def test_bundle_scenes_pure_natural_prose(self):
        from graph.flow_bundler import bundle_scenes_for_flow

        scenes = [
            {
                "narration_vn": "Năm 1954 tại lòng chảo Điện Biên Phủ.",
                "image_prompt_en": "**historical** trenches with (smoke) under overcast sky",
                "camera": "zoom_in",
            },
            {
                "narration_vn": "Những khẩu đại pháo được kéo qua dốc núi.",
                "image_prompt_en": "soldiers hauling heavy artillery through deep mud",
                "camera": "pan_right",
            },
        ]
        durations = [7.0, 7.0]
        blocks = bundle_scenes_for_flow(
            scenes=scenes,
            durations=durations,
            style_anchor_en="35mm documentary photography",
            max_blocks=1,
        )

        self.assertEqual(len(blocks), 1)
        prompt = blocks[0]["flow_prompt"]

        # Tuyệt đối không chứa ký tự markdown
        self.assertNotIn("*", prompt)
        self.assertNotIn("(", prompt)
        self.assertNotIn(")", prompt)
        self.assertNotIn("[", prompt)
        self.assertNotIn("]", prompt)
        self.assertNotIn("`", prompt)
        self.assertNotIn("#", prompt)

        # Tuyệt đối không chứa các từ ngữ nhạy cảm kích hoạt attention in chữ của LLM Omni
        self.assertNotIn("markdown", prompt.lower())
        self.assertNotIn("subtitles", prompt.lower())
        self.assertNotIn("typography", prompt.lower())
        self.assertIn("photorealistic 35mm motion picture", prompt)


if __name__ == "__main__":
    unittest.main()

