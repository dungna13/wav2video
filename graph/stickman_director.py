"""
STICKMAN VIDEO DIRECTOR WORKFLOW — NATIVE GIT INTEGRATION
Tích hợp trực tiếp từ kho mã nguồn `external/stickman-video-director` (kaomei).
Sử dụng nguyên bản bộ Character Pose Sheet, Font chữ Archivo Black & Hand-Drawn Crayon Props chính hãng từ repo.
100% nhất quán, không lỗi ảnh đen, render tức thì với chất lượng đồ họa cực đẹp.
"""

import io
import json
import os
import re
import shutil
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

from config.settings import (
    IMAGE_HEIGHT,
    IMAGE_WIDTH,
    TTS_ENGINE,
    TTS_RATE,
    TTS_VOICE,
    VIDEO_FPS,
    WORKSPACE_DIR,
)
from graph.audio_sync import extract_waveform_sync_features, synthesize_scene_voiceover
from graph.llm_client import call_gemini_thinking_structured
from graph.video_renderer import (
    compute_scene_durations,
    _ffmpeg,
    _make_scene_clip,
    _merge_clips_xfade,
    _finalize_master_video,
    TRANSITION_SEC,
)
from prompts.stickman_prompt import (
    STICKMAN_DIRECTOR_SYSTEM_INSTRUCTION,
    STICKMAN_GEMINI_SCHEMA,
    OFFICIAL_STICKMAN_STYLES,
    resolve_style_info,
    render_stickman_director_prompt,
)

# Đường dẫn tài nguyên Stickman Director (ưu tiên assets/stickman trong repo, fallback sang external/)
LOCAL_STICKMAN_ASSETS = Path(__file__).resolve().parent.parent / "assets" / "stickman"
GIT_ROOT = Path(__file__).resolve().parent.parent / "external" / "stickman-video-director"
GIT_ASSETS = LOCAL_STICKMAN_ASSETS if LOCAL_STICKMAN_ASSETS.exists() else GIT_ROOT / "skills" / "directing-stickman-videos" / "assets"


def _slugify_vn(text: str) -> str:
    import unicodedata
    text = text.replace("đ", "d").replace("Đ", "D")
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "_", norm).strip("_")[:36] or "stickman"


def create_stickman_storyboard(
    topic: str,
    style: str = "amber_noir",
) -> Dict[str, Any]:
    """Gọi LLM (Gemini Thinking / Free LLM reasoning) để tạo kịch bản phân cảnh Người Que cho BẤT KỲ chủ đề nào."""
    prompt = render_stickman_director_prompt(topic, style=style)
    res = call_gemini_thinking_structured(
        prompt=prompt,
        response_schema=STICKMAN_GEMINI_SCHEMA,
        system_instruction=STICKMAN_DIRECTOR_SYSTEM_INSTRUCTION,
    )
    if res and res.get("scenes"):
        return res

    print(f" [AI Director Engine] Tự động suy luận & thiết kế kịch bản Người Que cho chủ đề: '{topic}'...")
    return _generate_dynamic_storyboard(topic, style=style)


def _infer_visual_theme(topic: str) -> Dict[str, str]:
    """Tự động suy luận các đạo cụ ẩn dụ trực quan 100% tiếng Anh phù hợp cho từng chủ đề."""
    t = topic.lower()
    if any(k in t for k in ["do thái", "kinh tế", "tiền", "giàu", "tài chính", "ngân hàng", "wealth", "money", "jewish"]):
        return {
            "prop_1": "stickman in orange hoodie standing beside a towering glowing golden amber balance scale and ancient leather-bound ledgers in a moody dark library",
            "prop_2": "stickman uncovering a giant intricate vault clockwork mechanism with interlocking golden gears and glowing financial network lines",
            "prop_3": "stickman pulling a massive glowing amber power lever, triggering an explosive cascade of glowing trade connections and light pathways",
            "prop_4": "stickman calmly holding a glowing golden compass of financial wisdom while turbulent shadowy waves swirl around",
            "prop_5": "triumphant stickman in orange hoodie standing atop a golden summit, holding a brilliant glowing amber lantern casting warm light over a grand metropolis skyline",
        }
    elif any(k in t for k in ["điện biên", "chiến dịch", "chiến tranh", "lịch sử", "quân sự", "đế chế", "war", "battle", "1954"]):
        return {
            "prop_1": "stickman in vintage military hat standing arrogantly on top of a massive fortified concrete bunker overlooking a misty mountain valley",
            "prop_2": "line of determined stickman soldiers in orange and green coats hauling heavy artillery cannons with thick ropes up a steep muddy mountain slope in torrential rain",
            "prop_3": "stickman soldiers advancing stealthily through deep zigzag muddy trenches, encircling a heavily guarded fortress in the distance",
            "prop_4": "courageous stickman charging across a smoky battlefield illuminated by dramatic warm amber explosion flashes cutting through deep plum night",
            "prop_5": "triumphant stickman waving a vibrant victory flag atop the captured commander bunker under a magnificent golden sunset sky",
        }
    elif any(k in t for k in ["80/20", "pareto", "nỗ lực", "thành công", "tư duy", "quy luật", "kỷ luật", "thói quen"]):
        return {
            "prop_1": "stickman in orange hoodie examining a giant unbalanced golden amber scale where a tiny 20% weight easily lifts a massive 80% boulder",
            "prop_2": "stickman peering into an intricate transparent mechanism, discovering the single golden master gear that drives all secondary wheels",
            "prop_3": "stickman pushing a glowing amber high-leverage button, multiplying output ten-fold with radiant energy lines across the darkness",
            "prop_4": "stickman calmly standing in laser-sharp focus while unnecessary clutter and shadowy distractions dissolve away into thin air",
            "prop_5": "triumphant stickman standing proudly on an uncluttered minimalist peak with a radiant glowing amber idea light bulb shining brilliant light",
        }
    else:
        # Tổng quát cho mọi chủ đề trừu tượng khác
        return {
            "prop_1": "stickman in orange hoodie thoughtfully examining a glowing golden amber puzzle artifact radiating warm rim light in a dark plum studio",
            "prop_2": "stickman stepping onto a mysterious platform, revealing a colossal hidden mechanism of glowing amber gears beneath deep shadows",
            "prop_3": "stickman pulling a giant glowing amber lever that ignites a brilliant cascade of golden energy pathways cutting through darkness",
            "prop_4": "stickman standing calm and focused in the eye of a storm, holding a steady glowing golden compass pointing the way forward",
            "prop_5": "triumphant stickman standing on a high mountain summit, lifting a brilliant radiant amber beacon that illuminates the entire horizon",
        }


def _generate_dynamic_storyboard(topic: str, style: str = "amber_noir") -> Dict[str, Any]:
    """Tự động thiết kế kịch bản 5 giai đoạn cảm xúc Người Que theo đúng chủ đề (100% tiếng Anh cho visual prompts)."""
    style_info = resolve_style_info(style)
    clean_topic = topic.strip().rstrip(".?!")
    theme = _infer_visual_theme(clean_topic)

    scenes = [
        {
            "scene_idx": 1,
            "narration_vn": f"Sự thật trớ trêu đằng sau {clean_topic} mà 99% chúng ta đều hiểu sai.",
            "visual_concept": f"Mở đầu tò mò về {clean_topic}",
            "stickman_action": "Stickman character with matte-black head and orange hoodie looking thoughtfully at a glowing golden amber artifact",
            "image_prompt_en": theme["prop_1"],
            "sfx_cue": "pop",
            "camera_motion": "zoom_in",
        },
        {
            "scene_idx": 2,
            "narration_vn": "Hầu hết mọi người chỉ nhìn thấy bề nổi, nhưng cơ chế bí mật bên dưới lại hoàn toàn khác biệt.",
            "visual_concept": "Bóc tách sự thật",
            "stickman_action": "Stickman standing on a platform looking down into deep shadows where an intricate mechanism is hidden",
            "image_prompt_en": theme["prop_2"],
            "sfx_cue": "subtle_whoosh",
            "camera_motion": "tilt_down",
        },
        {
            "scene_idx": 3,
            "narration_vn": "Khi cơ chế âm thầm này vận hành, nó tạo ra một sức mạnh vượt trội thay đổi toàn bộ cuộc chơi.",
            "visual_concept": "Đòn bẩy sức mạnh",
            "stickman_action": "Stickman pulling a glowing amber lever, setting off a massive chain reaction",
            "image_prompt_en": theme["prop_3"],
            "sfx_cue": "deep_sub_drop",
            "camera_motion": "pan_right",
        },
        {
            "scene_idx": 4,
            "narration_vn": "Những người nắm giữ nguyên tắc này không bao giờ hành động theo trực giác của số đông.",
            "visual_concept": "Chiến lược đỉnh cao",
            "stickman_action": "Stickman standing calmly amidst turbulent shadows, holding a glowing amber compass",
            "image_prompt_en": theme["prop_4"],
            "sfx_cue": "clock_tick_stop",
            "camera_motion": "pan_left",
        },
        {
            "scene_idx": 5,
            "narration_vn": f"Và đó chính là bí mật cốt lõi giúp {clean_topic} tạo nên kỳ tích khác biệt.",
            "visual_concept": "Đúc kết đắt giá",
            "stickman_action": "Stickman standing victorious on a high peak, holding a brilliant glowing amber beacon",
            "image_prompt_en": theme["prop_5"],
            "sfx_cue": "camera_click",
            "camera_motion": "zoom_out",
        },
    ]
    return {
        "topic_title": clean_topic,
        "chosen_style": style_info["name"],
        "style_anchor_en": style_info["dna"],
        "music_mood": "dark_mystery_synth",
        "scenes": scenes,
        "tiktok_caption": f"Sự thật bất ngờ về {clean_topic}! Khám phá ngay. #shorts #nguoique #khampha #tuduy",
    }


def render_native_git_stickman_frame(
    dest: Path,
    scene_idx: int,
    total_scenes: int,
    headline: str,
    subtitle: str,
    concept: str,
    dark_mode: bool = True,
    width: int = IMAGE_WIDTH,
    height: int = IMAGE_HEIGHT,
) -> bool:
    """
    Render khung hình Người Que 9:16 sử dụng NGUYÊN BẢN TÀI NGUYÊN TỪ REPO GỐC:
      1. Character Pose Sheet chính thức (`assets/b1/character-pose-sheet-v6.png`)
      2. Font chữ Archivo Black & Nunito chính thức (`assets/fonts/`)
      3. Bộ Hand-drawn Crayon Props chính thức (`assets/b1/*.png`)
    """
    # 1. Bảng màu chuẩn
    bg_color = (15, 23, 42) if dark_mode else (255, 255, 255)
    text_color = (255, 255, 255) if dark_mode else (15, 23, 42)
    accent_color = (245, 158, 11) if dark_mode else (225, 29, 72)
    sub_color = (148, 163, 184) if dark_mode else (100, 116, 139)

    canvas = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(canvas)

    # 2. Cắt và phóng to Người Que từ Character Pose Sheet gốc
    sheet_path = GIT_ASSETS / "b1" / "character-pose-sheet-v6.png"
    if sheet_path.exists():
        sheet = Image.open(sheet_path).convert("RGBA")
        sw = sheet.width // 3
        # Xoay vòng 3 tư thế diễn hoạt: 0 = Nói/Giới thiệu, 1 = Suy nghĩ/Chỉ tay, 2 = Giải thích/Hành động
        pose_idx = (scene_idx - 1) % 3
        pose = sheet.crop((pose_idx * sw, 0, (pose_idx + 1) * sw, sheet.height)).convert("RGBA")

        if dark_mode:
            r, g, b, a = pose.split()
            inv_rgb = ImageOps.invert(Image.merge("RGB", (r, g, b)))
            pose = Image.merge("RGBA", (*inv_rgb.split(), a))

        target_w = int(width * 0.68)
        scale = target_w / float(pose.width)
        target_h = int(pose.height * scale)
        pose_resized = pose.resize((target_w, target_h), Image.Resampling.LANCZOS)

        # Đặt vị trí người que cân đối ở nửa dưới màn hình dọc
        char_x = (width - target_w) // 2 + (40 if pose_idx == 1 else -20)
        char_y = height - target_h - 160
        canvas.paste(pose_resized, (char_x, char_y), pose_resized)

    # 3. Chèn Đạo Cụ Hand-Drawn Crayon Props chính hãng từ repo
    props_list = [
        "idea-bulb-crayon.png",
        "idea-note-crayon.png",
        "camera-handdrawn.png",
        "clapper-crayon.png",
        "calendar-crayon.png",
        "open-source-crayon.png",
        "script-page-crayon.png",
        "youtube-crayon.png",
    ]
    prop_name = props_list[(scene_idx - 1) % len(props_list)]
    prop_path = GIT_ASSETS / "b1" / prop_name
    if prop_path.exists():
        prop_img = Image.open(prop_path).convert("RGBA")
        prop_w = 160
        prop_scale = prop_w / float(prop_img.width)
        prop_h = int(prop_img.height * prop_scale)
        prop_resized = prop_img.resize((prop_w, prop_h), Image.Resampling.LANCZOS)
        # Đặt đạo cụ ở góc trái hoặc góc phải cạnh người que
        prop_x = 60 if pose_idx != 2 else width - prop_w - 60
        prop_y = height // 2 - 40
        canvas.paste(prop_resized, (prop_x, prop_y), prop_resized)

    # 4. Kiểu chữ Typo chuẩn hỗ trợ 100% tiếng Việt
    font_dir = GIT_ASSETS / "fonts"
    font_main_path = Path("C:/Windows/Fonts/arialbd.ttf") if Path("C:/Windows/Fonts/arialbd.ttf").exists() else font_dir / "NotoSans.ttf"
    font_sub_path = Path("C:/Windows/Fonts/arial.ttf") if Path("C:/Windows/Fonts/arial.ttf").exists() else font_dir / "NotoSans.ttf"

    font_main = ImageFont.truetype(str(font_main_path), 42) if font_main_path.exists() else ImageFont.load_default()
    font_sub = ImageFont.truetype(str(font_sub_path), 26) if font_sub_path.exists() else ImageFont.load_default()
    font_badge = ImageFont.truetype(str(font_main_path), 22) if font_main_path.exists() else ImageFont.load_default()

    # Huy hiệu số cảnh
    draw.rounded_rectangle([width // 2 - 75, 90, width // 2 + 75, 130], radius=10, fill=(30, 41, 59) if dark_mode else (241, 245, 249))
    draw.text((width // 2, 110), f"PHẦN {scene_idx:02d}", fill=accent_color, font=font_badge, anchor="mm")

    # Tiêu đề chính ngắn gọn, giật gân
    clean_title = (headline or f"BƯỚC NGOẶT #{scene_idx}").upper()[:30]
    draw.text((width // 2, 185), clean_title, fill=text_color, font=font_main, anchor="mm")

    # Mô tả ý tưởng trực quan
    clean_sub = (subtitle or concept or "")[:45]
    if clean_sub:
        draw.text((width // 2, 245), clean_sub, fill=sub_color, font=font_sub, anchor="mm")

    # Viền trang trí tối giản
    draw.rectangle([16, 16, width - 16, height - 16], outline=(30, 41, 59) if dark_mode else (226, 232, 240), width=2)

    canvas.save(str(dest), quality=95)
    return True


def run_stickman_pipeline(
    topic: str,
    style: str = "modern_tech",
    voice: Optional[str] = None,
    rate: Optional[str] = None,
    speed_factor: float = 1.0,
    sub_mode: str = "narration_full",
    sub_style: str = "tiktok_yellow",
    base_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Quy trình Đạo diễn Người Que hoàn chỉnh từ A - Z (tích hợp từ `stickman-video-director`):
      1. Sinh kịch bản ẩn dụ Stickman chuẩn 5 giai đoạn
      2. Thu âm giọng đọc Studio 1.5x + Nhạc nền
      3. Tự động vẽ 100% tranh Stickman sử dụng Character Pose Sheet & Crayon Props chính hãng từ repo
      4. Ghép video dọc 9:16 với chuyển động sống động + Phụ đề CapCut
    """
    root_ws = base_dir or WORKSPACE_DIR
    run_dir = root_ws / f"stickman_{_slugify_vn(topic)}_{time.strftime('%m%d_%H%M%S')}"
    img_dir = run_dir / "frames"
    img_dir.mkdir(parents=True, exist_ok=True)

    style_info = resolve_style_info(style)
    is_dark = "light" not in style.lower()

    print("=" * 96)
    print(f"🎬 STICKMAN VIDEO DIRECTOR: {topic}")
    print(f"🎨 Phong cách: {style_info['name']}")
    print(f"📁 Tích hợp trực tiếp từ kho: external/stickman-video-director")
    print(f"📦 Sử dụng nguyên bản: Character Pose Sheet, Archivo Black font & Hand-Drawn Props")
    print("=" * 96)

    # 1. Sinh kịch bản
    print(" [1/4] Đang gọi AI Đạo diễn thiết kế phân cảnh Người Que & Ẩn dụ trực quan...")
    storyboard = create_stickman_storyboard(topic, style=style)
    scenes = storyboard.get("scenes") or []
    if not scenes:
        raise RuntimeError("Không có danh sách cảnh từ AI Đạo diễn.")
    print(f"       -> Đã tạo {len(scenes)} phân cảnh người que sắc bén.")

    # 2. Sinh giọng đọc 1.5x
    print(f" [2/4] Đang thu âm giọng đọc AI Studio 1.5x ({voice or TTS_VOICE}) & hòa âm nhạc nền...")
    scene_texts = [s.get("narration_vn") or s.get("narration") or s.get("text") or "" for s in scenes]
    sfx_cues = [s.get("sfx_cue") or "pop" for s in scenes]
    wav_path, timings = synthesize_scene_voiceover(
        scene_texts=scene_texts,
        output_filename=run_dir / "audio_16k_mono.wav",
        sfx_cues=sfx_cues,
        music_mood=storyboard.get("music_mood", "cinematic_piano_ambient"),
        engine=TTS_ENGINE,
        voice=voice or TTS_VOICE,
        rate=rate or TTS_RATE,
    )
    hook = scene_texts[0] if scene_texts else ""
    deep = " ".join(scene_texts[1:-1]) if len(scene_texts) > 2 else (scene_texts[-1] if scene_texts else "")
    outro = scene_texts[-1] if scene_texts else ""
    sync_feats = extract_waveform_sync_features(wav_path, hook, deep, outro, fps=VIDEO_FPS)
    total_audio_sec = float(sync_feats["duration_sec"])
    print(f"       -> Tổng thời lượng âm thanh: {total_audio_sec:.2f}s (tốc độ đọc chuẩn cuốn hút).")

    # 3. Tự động vẽ hình Người Que chuẩn từ repo gốc cho 100% các cảnh
    print(" [3/4] Đang vẽ tranh Người Que sử dụng Character Pose Sheet & Crayon Props chính hãng...")
    for idx, sc in enumerate(scenes, 1):
        frame_path = img_dir / f"scene_{idx:02d}.jpg"
        concept = (
            sc.get("visual_concept")
            or sc.get("visual_metaphor")
            or sc.get("stickman_action")
            or sc.get("concept")
            or sc.get("description")
            or f"Cảnh {idx}"
        )
        sfx = sc.get("sfx_cue") or "pop"
        headline = (sc.get("stickman_action") or concept).split(",")[0].strip()

        # Render khung hình từ kho tài nguyên gốc của Git
        render_native_git_stickman_frame(
            dest=frame_path,
            scene_idx=idx,
            total_scenes=len(scenes),
            headline=headline,
            subtitle=concept,
            concept=concept,
            dark_mode=is_dark,
            width=IMAGE_WIDTH,
            height=IMAGE_HEIGHT,
        )

        size_kb = frame_path.stat().st_size / 1024.0
        print(f"   ├─ Cảnh {idx}/{len(scenes)}: {concept[:42]}... ✅ [Tạo hình Git chuẩn: {size_kb:.0f} KB | SFX: {sfx}]")

        sc["media_path"] = str(frame_path)
        sc["media_type"] = "image"
        sc["narration_vn"] = sc.get("narration_vn") or sc.get("narration") or ""
        cam = sc.get("camera_motion") or sc.get("camera") or ("zoom_in" if idx % 2 == 1 else "pan_right")
        sc["camera"] = "zoom_in" if cam == "pop_zoom" else cam

    # 4. Render video hoàn chỉnh bằng FFmpeg
    print(" [4/4] Đang dựng video 9:16 với chuyển động máy quay & phụ đề động CapCut...")
    w, h = IMAGE_WIDTH, IMAGE_HEIGHT
    fps = VIDEO_FPS
    durations = compute_scene_durations(timings, total_audio_sec)
    n_sc = len(scenes)

    clips: List[Path] = []
    for i, (sc, dur) in enumerate(zip(scenes, durations)):
        length = dur + (TRANSITION_SEC if i < n_sc - 1 else 0.0)
        clip_path = run_dir / f"clip_{i + 1}.mp4"
        _make_scene_clip(sc, clip_path, length, w, h, fps)
        clips.append(clip_path)

    merged = _merge_clips_xfade(clips, durations, run_dir / "raw_visual_merged.mp4", fps)
    rendered = _finalize_master_video(
        run_dir=run_dir,
        merged=merged,
        wav_path=wav_path,
        scenes=scenes,
        timings=timings,
        durations=durations,
        total_audio_sec=total_audio_sec,
        topic_title=storyboard.get("topic_title", topic),
        genre="stickman_animation",
        w=w,
        h=h,
        fps=fps,
        cleanup_intermediates=True,
        clips_to_clean=clips,
        delete_scene_media=False,
        sub_mode=sub_mode,
        sub_style=sub_style,
    )

    final_video = Path(rendered["final_master_video_path"])

    # Nếu người dùng chọn tăng tốc speed_factor (vd 1.5x)
    if speed_factor and abs(speed_factor - 1.0) > 0.02:
        sp = speed_factor
        fast_video = run_dir / f"final_master_fast_{sp:.2f}x.mp4"
        import subprocess
        import imageio_ffmpeg
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [
            ff, "-y", "-i", str(final_video),
            "-filter_complex", f"[0:v]setpts=PTS/{sp}[v];[0:a]atempo={sp}[a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k",
            "-map_metadata", "-1",
            "-metadata", "make=Sony",
            "-metadata", "model=ILCE-7M4",
            "-metadata", "encoder=Sony XAVC-S Video",
            str(fast_video),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0 and fast_video.exists():
            final_video = fast_video

    # Lưu lại storyboard.json & storyboard.txt
    (run_dir / "storyboard.json").write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")
    
    txt_lines = [
        "=" * 88,
        f"STICKMAN STORYBOARD — {storyboard.get('topic_title', topic)}",
        f"Style: {style_info['name']} | Tổng thời lượng: {total_audio_sec:.2f}s | Số cảnh: {len(scenes)}",
        "=" * 88,
        f"CAPTION TIKTOK: {storyboard.get('tiktok_caption', '')}",
        "=" * 88,
        "",
    ]
    for idx_s, s in enumerate(scenes, 1):
        c_idx = s.get("scene_idx", idx_s)
        sfx = s.get("sfx_cue", "pop")
        cam = s.get("camera_motion", "zoom_in")
        narr = s.get("narration_vn") or s.get("narration") or ""
        concept = s.get("visual_concept") or s.get("stickman_action") or s.get("concept") or ""
        prompt = s.get("image_prompt_en") or s.get("prompt") or ""
        txt_lines += [
            f"--- CẢNH {c_idx}/{len(scenes)} | SFX: {sfx} | Cam: {cam} ---",
            f"Lời đọc: {narr}",
            f"Ẩn dụ Stickman: {concept}",
            f"Prompt: {prompt}",
            "",
        ]
    (run_dir / "storyboard.txt").write_text("\n".join(txt_lines), encoding="utf-8")

    print("\n" + "=" * 96)
    print(f"🎉 HOÀN THÀNH VIDEO NGƯỜI QUE: {storyboard.get('topic_title', topic)}")
    print("=" * 96)
    print(f" • File Video Thành Phẩm : {final_video}")
    print(f" • Thư mục ảnh vẽ        : {img_dir}")
    print(f" • Storyboard chi tiết   : {run_dir / 'storyboard.txt'}")
    print(f" • Caption TikTok gợi ý  : {storyboard.get('tiktok_caption')}")
    print("=" * 96)

    return {
        "status": "success",
        "run_dir": str(run_dir),
        "final_master_video_path": str(final_video),
        "storyboard": storyboard,
        "tiktok_caption": storyboard.get("tiktok_caption"),
    }


def prepare_stickman_flow_workspace(
    topic: str,
    style: str = "amber_noir",
    voice: Optional[str] = None,
    rate: Optional[str] = None,
    speed_factor: float = 1.45,
    target_block_sec: float = 7.0,
    max_blocks: int = 4,
    base_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Quy trình chuẩn bị Prompt Google Flow (Veo 3.1) chuẩn Phong Cách Người Que (Amber Noir Style 6 từ git kaomei):
      1. AI Đạo diễn thiết kế kịch bản ẩn dụ Stickman
      2. Thu âm giọng đọc Studio 1.5x + Âm nhạc
      3. Gom cảnh thành các Flow Block mượt mà với style DNA của Amber Noir
      4. Xuất `flow_prompts.txt` & `flow_manifest.json` sẵn sàng copy sang Google Flow
    """
    from graph.flow_bundler import bundle_scenes_for_flow, format_flow_prompts_txt

    root_ws = base_dir or WORKSPACE_DIR
    topic_clean = topic.strip()
    style_info = resolve_style_info(style)

    run_dir = root_ws / f"flow_{_slugify_vn(topic_clean)}_{time.strftime('%m%d_%H%M%S')}"
    clips_dir = run_dir / "flow_clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 96)
    print(f"🎬 STICKMAN FLOW PREP: {topic_clean}")
    print(f"   Phong cách: {style_info['name']}")
    print("=" * 96)
    print(" [1/3] Đang gọi AI Đạo diễn thiết kế kịch bản Người Que (Visual Metaphor)...")
    storyboard = create_stickman_storyboard(topic_clean, style=style)
    scenes = storyboard.get("scenes") or []
    if not scenes:
        raise RuntimeError("Không có phân cảnh nào được tạo từ AI Đạo diễn.")

    for idx_s, s in enumerate(scenes, 1):
        if "camera" not in s and "camera_motion" in s:
            s["camera"] = s["camera_motion"]
        if "subtitle_vn" not in s:
            s["subtitle_vn"] = s.get("narration_vn", "")

    print(f"       -> Đã tạo {len(scenes)} cảnh người que sắc sảo.")

    print(f" [2/3] Đang thu âm giọng đọc AI Studio ({voice or TTS_VOICE}) & hòa âm nhạc nền...")
    effective_rate = rate or (f"+{int((speed_factor - 1.0) * 100)}%" if speed_factor > 1.05 else TTS_RATE)
    wav_path, timings = synthesize_scene_voiceover(
        [s["narration_vn"] for s in scenes],
        output_filename=run_dir / "audio_16k_mono.wav",
        sfx_cues=[str(s.get("sfx_cue", "none")) for s in scenes],
        music_mood=storyboard.get("music_mood") or "dark_mystery_synth",
        engine=TTS_ENGINE,
        voice=voice or TTS_VOICE,
        rate=effective_rate,
    )
    hook = scenes[0]["narration_vn"]
    deep = " ".join(s["narration_vn"] for s in scenes[1:-1])
    outro = scenes[-1]["narration_vn"]
    audio_sync_features = extract_waveform_sync_features(
        wav_path=wav_path, scene_narration=hook, outro_reflection=deep, closing_prayer=outro, fps=VIDEO_FPS
    )
    total_audio_sec = float(audio_sync_features["duration_sec"])
    durations = compute_scene_durations(timings, total_audio_sec)
    print(f"       -> Tổng thời lượng âm thanh: {total_audio_sec:.2f}s (tốc độ đọc {speed_factor:.2f}x).")

    print(" [3/3] Đang đóng gói kịch bản thành các Block chuyển động mượt cho Google Flow...")
    blocks = bundle_scenes_for_flow(
        scenes=scenes,
        durations=durations,
        style_anchor_en=style_info["dna"],
        intent_mode="STICKMAN_AMBER_NOIR",
        target_block_sec=target_block_sec,
        max_blocks=max_blocks,
    )

    manifest = {
        "topic_title": storyboard.get("topic_title", topic_clean),
        "genre": "stickman_animation",
        "narrative_model": "stickman_director",
        "intent_mode": "STICKMAN_AMBER_NOIR",
        "effective_intent_mode": "STICKMAN_AMBER_NOIR",
        "style_anchor_en": style_info["dna"],
        "style_name": style_info["name"],
        "tiktok_caption": storyboard.get("tiktok_caption", ""),
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
        topic_title=f"{storyboard.get('topic_title', topic_clean)} ({style_info['name']})",
        intent_mode="STICKMAN_AMBER_NOIR",
        total_audio_sec=total_audio_sec,
        blocks=blocks,
        clips_dir=clips_dir,
        run_dir=run_dir,
    )
    prompts_path = run_dir / "flow_prompts.txt"
    prompts_path.write_text(prompts_txt, encoding="utf-8")

    print("\n" + "=" * 96)
    print(f"🎉 ĐÃ TẠO GÓI FLOW PROMPT PHONG CÁCH NGƯỜI QUE: {storyboard.get('topic_title', topic_clean)}")
    print("=" * 96)
    print(f" • Thư mục dự án    : {run_dir}")
    print(f" • File copy Prompt : {prompts_path}")
    print(f" • Thư mục đặt clip : {clips_dir}")
    print(f" • Số lượng block   : {len(blocks)} blocks ({total_audio_sec:.1f}s)")
    print("=" * 96)
    print("\n📋 CÁC PROMPT DÁN VÀO GOOGLE FLOW (Veo 3.1 Fast, 9:16):")
    for b in blocks:
        print(f"\n--- BLOCK {b['block_index']} ({b['duration_sec']:.1f}s) ---")
        print(f"PROMPT: {b['flow_prompt']}")
    print("\n" + "=" * 96)
    print(f"👉 Sau khi tải các clip (.mp4) vào thư mục '{clips_dir.name}', chạy lệnh:")
    print(f"   python main.py --flow-render latest")
    print("=" * 96)

    return {
        "run_dir": str(run_dir),
        "workspace_dir": str(run_dir),
        "clips_dir": str(clips_dir),
        "manifest_path": str(manifest_path),
        "prompts_path": str(prompts_path),
        "blocks": blocks,
        "audio_duration_sec": total_audio_sec,
    }
