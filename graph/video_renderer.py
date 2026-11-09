"""
Module Dựng Video Hoạt Hình Điện Ảnh 3D Sống Động (`video_renderer.py`):
Khắc phục triệt để hiện tượng "ghép 2 ảnh tĩnh trượt qua lại" bằng kiến trúc 3 tầng chuyển động 30fps:
1. **4 Phân Cảnh Độc Lập Hoàn Toàn (2x2 4-Panel Storyboard Grid)**:
   Tải bảng phân cảnh 2x2 (`1080x1920`) có Nhân vật chính & Bối cảnh 3D do LLM thiết kế, tách thành 4 góc máy độc lập
   (`scene_1.jpg` -> `scene_4.jpg`: Cận cảnh Mở đầu -> Trung cảnh Biến cố -> Đại cảnh Cao trào -> Bình minh Kết luận).
2. **2.5D Living Environment Warping & Volumetric God-Rays (`_apply_living_25d_scene_motion`)**:
   Biến ảnh tĩnh thành cảnh "Sống" ở 30fps: tách lớp chiều sâu 2.5D Parallax (tiền cảnh trôi nhanh hơn hậu cảnh),
   biến dạng lưới sóng gió (Wind & Ripple Mesh Displacement làm cây lá/áo choàng/mặt nước đung đưa thật) + Tia nắng God-Rays quét chéo.
3. **Thực Thể Hoạt Hình 3D Chuyển Động Thật Ở Tiền Cảnh (`_draw_3d_animated_actor`)**:
   Vẽ thực thể 3D cử động liên tục 30fps khớp nhịp giọng đọc (`rms_envelope_per_frame`):
   - `butterfly_chaos_wings`: Cánh bướm phát sáng 3D đập cánh theo góc chiếu phối cảnh 3D, bay lượn tạo vòng sóng hỗn loạn.
   - `cosmic_orbital_spheres`: Hệ hành tinh & vòng quỹ đạo 3D xoay quanh lõi năng lượng phát sáng.
   - `chrono_hourglass_gears`: Bánh răng thời gian 3D ăn khớp xoay tròn & dòng cát ánh sáng rơi.
   - `soul_lantern_ascension`: Đèn lồng 3D bập bùng lửa ấm bay lên bầu trời đêm.
"""

import io
import math
import subprocess
import urllib.parse
import socket
from pathlib import Path
from typing import Dict, Any, List, Tuple
import requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

from config.settings import IMAGE_WIDTH, IMAGE_HEIGHT, VIDEO_FPS


def _load_vn_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    candidates = (
        ["C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/tahomabd.ttf"]
        if bold
        else ["C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/tahoma.ttf"]
    )
    for fp in candidates:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, size=size)
            except Exception:
                pass
    return ImageFont.load_default()


def _get_font_bank() -> Dict[str, Any]:
    if not hasattr(_get_font_bank, "_cache"):
        _get_font_bank._cache = {
            "badge": _load_vn_font(19, bold=True),
            "scene_tag": _load_vn_font(21, bold=True),
            "sub": _load_vn_font(28, bold=True),
        }
    return _get_font_bank._cache


def _has_network() -> bool:
    try:
        socket.gethostbyname("image.pollinations.ai")
        return True
    except Exception:
        return False


def _create_fallback_4_scenes(width: int, height: int, seed: int) -> List[Image.Image]:
    """Bộ 4 cảnh 3D Fantasy Art khác biệt hoàn toàn khi chạy Offline."""
    scenes: List[Image.Image] = []
    palettes = [
        ((10, 22, 48), (20, 88, 142), (56, 189, 248), (253, 224, 71)),
        ((28, 12, 52), (135, 38, 62), (244, 114, 182), (251, 191, 36)),
        ((14, 18, 42), (88, 28, 135), (168, 85, 247), (56, 189, 248)),
        ((16, 32, 46), (22, 120, 96), (251, 191, 36), (254, 240, 138)),
    ]
    y = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None]
    x = np.linspace(-1.0, 1.0, width, dtype=np.float32)[None, :]

    for idx, (c_top, c_mid, c_glow, c_accent) in enumerate(palettes):
        cx = -0.2 + 0.14 * idx
        cy = 0.36 + 0.04 * (idx % 2)
        dist = np.sqrt((x - cx) ** 2 + ((y - cy) * 1.35) ** 2)
        orb = np.exp(-dist * (2.8 + 0.3 * idx))
        swirl = 0.5 + 0.5 * np.sin(dist * 10.0 - np.arctan2(y - cy, x - cx) * (2.0 + idx))

        r = c_top[0] * (1 - y) + c_mid[0] * y + c_glow[0] * orb * 0.85 + c_accent[0] * (orb ** 2) * swirl * 0.55
        g = c_top[1] * (1 - y) + c_mid[1] * y + c_glow[1] * orb * 0.85 + c_accent[1] * (orb ** 2) * swirl * 0.55
        b = c_top[2] * (1 - y) + c_mid[2] * y + c_glow[2] * orb * 0.85 + c_accent[2] * (orb ** 2) * swirl * 0.55

        horizon = 0.66 + 0.05 * np.sin(x * (3.0 + idx) + idx) - 0.03 * np.cos(x * 7.0)
        is_fg = y > horizon
        r = np.where(is_fg, r * 0.20, r)
        g = np.where(is_fg, g * 0.20, g)
        b = np.where(is_fg, b * 0.26, b)

        rgb = np.stack([np.clip(r, 0, 255), np.clip(g, 0, 255), np.clip(b, 0, 255)], axis=-1).astype(np.uint8)
        scenes.append(Image.fromarray(rgb, mode="RGB"))
    return scenes


def _fetch_ai_4panel_storyboard_scenes(
    run_dir: Path,
    topic_title: str,
    scene_action_prompt: str,
    seed: int,
    width: int = 540,
    height: int = 960,
) -> List[Image.Image]:
    """
    Tải Bảng Phân Cảnh 2x2 Grid (4 Khung Cảnh Độc Lập Hoàn Toàn: Top-Left, Top-Right, Bottom-Left, Bottom-Right)
    từ Pollinations AI (`1080x1920`) và cắt thành 4 file `scene_1.jpg` .. `scene_4.jpg` riêng biệt.
    """
    scene_paths = [run_dir / f"scene_{i}.jpg" for i in (1, 2, 3, 4)]
    if all(p.exists() and p.stat().st_size > 5000 for p in scene_paths):
        return [Image.open(p).convert("RGB") for p in scene_paths]

    if _has_network():
        prompt_clean = (
            f"A 2x2 4-panel comic storyboard grid of 4 distinct scenes in 3D Pixar and Makoto Shinkai anime style. "
            f"{scene_action_prompt}. Each of the 4 quadrants shows a completely different camera angle and action scene, "
            f"vivid lighting, volumetric god rays, 8k masterpiece, no text, no speech bubbles, no watermark"
        )
        encoded = urllib.parse.quote(prompt_clean)
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1920&seed={seed}&nologo=true"
        try:
            resp = requests.get(url, timeout=32)
            ctype = resp.headers.get("content-type", "")
            if resp.status_code == 200 and "image" in ctype and len(resp.content) > 12000:
                master_grid = Image.open(io.BytesIO(resp.content)).convert("RGB")
                mw, mh = master_grid.size
                usable_h = mh - 44  # Bỏ mép dưới cùng tránh watermark
                half_w = mw // 2
                half_h = usable_h // 2
                pad_x, pad_y = 14, 14  # Bỏ đường viền ngăn cách giữa 4 ô

                # Cắt 4 ô 2x2 độc lập hoàn toàn (Không bao giờ trùng lặp hình ảnh!)
                quadrants = [
                    (pad_x, pad_y, half_w - pad_x, half_h - pad_y),                   # Ô 1: Top-Left (Cảnh 1)
                    (half_w + pad_x, pad_y, mw - pad_x, half_h - pad_y),              # Ô 2: Top-Right (Cảnh 2)
                    (pad_x, half_h + pad_y, half_w - pad_x, usable_h - pad_y),        # Ô 3: Bottom-Left (Cảnh 3)
                    (half_w + pad_x, half_h + pad_y, mw - pad_x, usable_h - pad_y),   # Ô 4: Bottom-Right (Cảnh 4)
                ]
                scenes: List[Image.Image] = []
                for idx, box in enumerate(quadrants):
                    panel = master_grid.crop(box).resize((width, height), Image.Resampling.LANCZOS)
                    panel = ImageEnhance.Contrast(panel).enhance(1.08)
                    panel = ImageEnhance.Color(panel).enhance(1.12)
                    panel.save(str(scene_paths[idx]), quality=93)
                    scenes.append(panel)

                print(f"[3D AI 4-Panel Storyboard] Đã tải & tách 4 phân cảnh 2x2 độc lập (`scene_1.jpg`..`scene_4.jpg`) -> {run_dir.name}")
                return scenes
        except Exception as e:
            print(f" [3D AI Info] Không tải được ảnh mạng ({e}) -> Dùng 4 cảnh 3D Fantasy Art nội bộ.")

    fallback_scenes = _create_fallback_4_scenes(width, height, seed)
    for p, im in zip(scene_paths, fallback_scenes):
        im.save(str(p), quality=92)
    return fallback_scenes


def _apply_living_25d_scene_motion(
    scene_arr: np.ndarray,
    local_prog: float,
    t_sec: float,
    scene_idx: int,
    rms_val: float,
) -> np.ndarray:
    """
    Biến bức tranh từng cảnh thành Môi trường 2.5D Sống động ở 30fps:
    1. Chuyển động Camera 2.5D Parallax (Tiền cảnh dịch chuyển nhanh hơn Hậu cảnh tạo chiều sâu 3D thật).
    2. Biến dạng Sóng Gió Nội Cảnh (Wind & Fluid Ripple Mesh Displacement): làm mây trôi, mặt nước gợn sóng,
       lá cây và tà áo nhân vật đung đưa theo gió liên tục từng frame.
    3. Luồng Tia Nắng Điện Ảnh (Volumetric God-Rays) quét chéo và bừng sáng theo giọng đọc (`rms_val`).
    """
    h, w, _ = scene_arr.shape
    smooth_p = 0.5 - 0.5 * math.cos(math.pi * min(1.0, max(0.0, local_prog)))

    # Tạo lưới tọa độ chuẩn hóa [0..1]
    yy = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
    xx = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :]

    # 1. Zoom & Pan theo từng cảnh + 2.5D Depth Parallax theo trục dọc (tiền cảnh y lớn dịch chuyển mạnh hơn bầu trời y nhỏ)
    zoom = 1.12 + 0.10 * (smooth_p if scene_idx % 2 == 0 else (1.0 - smooth_p))
    parallax_depth = 0.45 + 0.85 * (yy ** 1.4)  # Tiền cảnh dưới dịch chuyển gấp ~2.8 lần bầu trời xa
    pan_dir = 1.0 if scene_idx in (0, 2) else -1.0
    pan_x = pan_dir * (smooth_p - 0.5) * 0.09 * parallax_depth
    pan_y = (0.5 - smooth_p) * 0.05

    # 2. Biến dạng Sóng Gió & Mây Trôi Nội Cảnh (Living Wind & Water Ripple Field)
    # Vùng bầu trời (y < 0.45): mây trôi ngang nhẹ nhàng
    sky_mask = np.clip((0.48 - yy) / 0.48, 0.0, 1.0)
    cloud_drift_x = sky_mask * 0.014 * np.sin(yy * 8.0 + t_sec * 1.35)

    # Vùng trung cảnh & tiền cảnh (y > 0.35): gió thổi cây lá / áo choàng & gợn sóng nước
    wind_mask = np.clip((yy - 0.30) / 0.70, 0.0, 1.0)
    wind_wave_x = wind_mask * 0.0085 * np.sin(yy * 24.0 - t_sec * 4.2 + xx * 6.0)
    wind_wave_y = wind_mask * 0.0045 * np.cos(xx * 18.0 + t_sec * 3.4)

    # Ánh xạ tọa độ lấy mẫu (Coordinate Remapping)
    u = 0.5 + (xx - 0.5 + pan_x + cloud_drift_x + wind_wave_x) / zoom
    v = 0.5 + (yy - 0.5 + pan_y + wind_wave_y) / zoom

    src_x = np.clip((u * (w - 1)).astype(np.int32), 0, w - 1)
    src_y = np.clip((v * (h - 1)).astype(np.int32), 0, h - 1)
    warped = scene_arr[src_y, src_x].astype(np.float32)

    # 3. Luồng Tia Nắng Volumetric God-Rays quét chéo qua không gian 3D
    ray_coord = xx * 0.78 - yy * 0.38 + 0.12 * math.sin(t_sec * 0.9)
    rays = (
        0.5
        + 0.30 * np.sin(ray_coord * 22.0 + t_sec * 1.8)
        + 0.20 * np.cos(ray_coord * 37.0 - t_sec * 2.4)
    )
    ray_envelope = np.clip(1.15 - yy * 1.1, 0.0, 1.0) * (0.14 + 0.16 * rms_val)
    ray_intensity = (rays * ray_envelope)[..., None]

    # Màu tia nắng vàng ấm pha cyan điện ảnh
    ray_color = np.array([255.0, 228.0, 165.0], dtype=np.float32) if scene_idx != 2 else np.array([145.0, 225.0, 255.0], dtype=np.float32)
    warped = np.clip(warped + ray_intensity * ray_color * 0.42, 0.0, 255.0)

    # Làm tối nhẹ vùng dưới cùng (y > 0.72) để phụ đề và thực thể 3D nổi bật
    vignette = np.where(yy > 0.72, 1.0 - 0.55 * ((yy - 0.72) / 0.28), 1.0)[..., None]
    warped = warped * vignette
    return warped.astype(np.uint8)


def _draw_3d_animated_actor(
    draw: ImageDraw.ImageDraw,
    archetype: str,
    t_sec: float,
    rms_val: float,
    width: int,
    height: int,
) -> None:
    """
    Vẽ Thực Thể Hoạt Hình 3D Chuyển Động Thật ở Tiền Cảnh (30fps Articulated 3D Animation)
    khớp trực tiếp với chủ đề và năng lượng giọng đọc `rms_val`.
    """
    # Tâm di chuyển lượn sóng 3D mềm mại trên khung hình
    cx = int(width * (0.50 + 0.18 * math.sin(t_sec * 1.15)))
    cy = int(height * (0.43 + 0.07 * math.cos(t_sec * 1.65)))

    if archetype == "butterfly_chaos_wings":
        # 1. Vòng sóng Năng lượng Hỗn loạn (Chaos Ripple Waves) lan tỏa từ thân bướm
        for r_idx in range(3):
            wave_phase = (t_sec * 0.85 + r_idx * 0.33) % 1.0
            rad_x = int(28 + wave_phase * (135 + 45 * rms_val))
            rad_y = int(rad_x * 0.52)
            alpha = int((1.0 - wave_phase) * (135 + 75 * rms_val))
            if alpha > 12:
                draw.ellipse(
                    (cx - rad_x, cy - rad_y, cx + rad_x, cy + rad_y),
                    outline=(56, 225, 255, alpha) if r_idx % 2 == 0 else (255, 215, 85, alpha),
                    width=2,
                )

        # 2. Chú Bướm Phát Sáng 3D Đập Cánh (3D Foreshortened Articulated Wings)
        flap = math.sin(t_sec * 11.5)  # Tần số vỗ cánh mượt ở 30fps
        wing_span = int((76 + 18 * rms_val) * (0.32 + 0.68 * abs(flap)))
        wing_lift = int(-22 * flap)
        tilt_y = int(12 * math.cos(t_sec * 1.15))

        for sign in (-1, 1):
            # Cánh trên (Forewing)
            p_top = [
                (cx, cy - 6),
                (cx + sign * int(wing_span * 0.85), cy - 58 + wing_lift + sign * tilt_y),
                (cx + sign * wing_span, cy - 12 + wing_lift // 2 + sign * tilt_y),
                (cx + sign * int(wing_span * 0.55), cy + 14),
            ]
            draw.polygon(p_top, fill=(38, 198, 248, 175), outline=(255, 242, 145, 240))
            # Cánh dưới (Hindwing)
            p_bot = [
                (cx, cy + 6),
                (cx + sign * int(wing_span * 0.68), cy + 16 + wing_lift // 2),
                (cx + sign * int(wing_span * 0.52), cy + 56 + wing_lift // 3),
                (cx + sign * 10, cy + 28),
            ]
            draw.polygon(p_bot, fill=(245, 168, 45, 165), outline=(255, 245, 190, 225))
            # Đốm sáng thần tiên trên cánh
            dot_x = cx + sign * int(wing_span * 0.58)
            dot_y = cy - 24 + wing_lift // 2
            draw.ellipse((dot_x - 6, dot_y - 6, dot_x + 6, dot_y + 6), fill=(255, 255, 220, 235))

        # Thân bướm phát sáng
        draw.ellipse((cx - 5, cy - 26, cx + 5, cy + 28), fill=(255, 248, 210, 255))

    elif archetype == "chrono_hourglass_gears":
        # Bánh răng Thời gian 3D ăn khớp xoay tròn + Đồng hồ cát ánh sáng
        for g_idx, (gx_off, gy_off, radius, speed, col) in enumerate([
            (-52, -28, 46, 1.4, (255, 208, 85, 190)),
            (48, 24, 36, -1.8, (64, 215, 255, 185)),
        ]):
            gx, gy = cx + gx_off, cy + gy_off
            draw.ellipse((gx - radius, gy - radius, gx + radius, gy + radius), outline=col, width=3)
            inner_r = int(radius * 0.55)
            draw.ellipse((gx - inner_r, gy - inner_r, gx + inner_r, gy + inner_r), outline=col, width=2)
            # Răng bánh răng & nan hoa xoay
            num_teeth = 10 if g_idx == 0 else 8
            for k in range(num_teeth):
                ang = t_sec * speed + k * (2 * math.pi / num_teeth)
                x1 = gx + int((radius - 4) * math.cos(ang))
                y1 = gy + int((radius - 4) * math.sin(ang))
                x2 = gx + int((radius + 9) * math.cos(ang))
                y2 = gy + int((radius + 9) * math.sin(ang))
                draw.line([(x1, y1), (x2, y2)], fill=col, width=4)
                if k % 2 == 0:
                    draw.line([(gx, gy), (x1, y1)], fill=col, width=2)

        # Dòng hạt cát thời gian rơi sáng rực ở trung tâm
        for s_i in range(14):
            fall_p = (t_sec * 1.8 + s_i * 0.07) % 1.0
            sy = cy - 45 + int(fall_p * 95)
            sx = cx + int(math.sin(s_i * 3.1 + t_sec * 5.0) * (3 + 12 * abs(fall_p - 0.5)))
            draw.ellipse((sx - 3, sy - 3, sx + 3, sy + 3), fill=(255, 242, 160, 235))

    elif archetype == "soul_lantern_ascension":
        # Đàn Đèn Lồng Linh Hồn 3D bay lên bầu trời đêm với ngọn lửa bập bùng bên trong
        for l_idx in range(7):
            rise_p = (t_sec * (0.12 + 0.02 * (l_idx % 3)) + l_idx * 0.17) % 1.0
            ly = int(height * (0.76 - rise_p * 0.62))
            lx = int(width * (0.16 + 0.11 * l_idx) + 24.0 * math.sin(t_sec * 1.4 + l_idx * 1.7))
            scale = 0.65 + 0.55 * (1.0 - rise_p)
            lw = int(22 * scale)
            lh = int(30 * scale)
            flicker = int(35 * math.sin(t_sec * 14.0 + l_idx))
            # Quầng sáng ấm quanh đèn lồng
            glow_r = int(lw * (1.8 + 0.4 * rms_val))
            draw.ellipse((lx - glow_r, ly - glow_r, lx + glow_r, ly + glow_r), fill=(255, 165, 45, 52))
            # Thân đèn lồng 3D
            draw.rounded_rectangle(
                (lx - lw, ly - lh, lx + lw, ly + lh),
                radius=6,
                fill=(245, min(255, 145 + flicker), 42, 210),
                outline=(255, 238, 175, 245),
                width=2,
            )
            # Tâm lửa sáng rực
            core_r = max(3, int(lw * 0.42))
            draw.ellipse((lx - core_r, ly - core_r + 4, lx + core_r, ly + core_r + 4), fill=(255, 252, 220, 250))

    else:
        # `cosmic_orbital_spheres`: Hệ Hành Tinh & Quỹ Đạo Năng Lượng 3D xoay quanh Tâm Sáng
        core_r = int(24 + 12 * rms_val)
        draw.ellipse((cx - core_r * 2, cy - core_r * 2, cx + core_r * 2, cy + core_r * 2), fill=(56, 189, 248, 68))
        draw.ellipse((cx - core_r, cy - core_r, cx + core_r, cy + core_r), fill=(255, 245, 195, 245), outline=(56, 225, 255, 255), width=2)

        for r_idx, (rx, ry, tilt_deg, spd, p_col) in enumerate([
            (110, 42, 26.0, 1.9, (56, 225, 255, 240)),
            (95, 36, -34.0, -2.3, (255, 205, 75, 240)),
            (132, 48, 8.0, 1.3, (244, 114, 182, 230)),
        ]):
            tilt = math.radians(tilt_deg)
            pts = []
            for step in range(37):
                a = step * (2 * math.pi / 36)
                ox, oy = rx * math.cos(a), ry * math.sin(a)
                px = cx + int(ox * math.cos(tilt) - oy * math.sin(tilt))
                py = cy + int(ox * math.sin(tilt) + oy * math.cos(tilt))
                pts.append((px, py))
            draw.line(pts, fill=(p_col[0], p_col[1], p_col[2], 115), width=2)

            # Hành tinh vệ tinh chuyển động 3D trên từng quỹ đạo
            p_ang = t_sec * spd + r_idx * 2.1
            ox, oy = rx * math.cos(p_ang), ry * math.sin(p_ang)
            px = cx + int(ox * math.cos(tilt) - oy * math.sin(tilt))
            py = cy + int(ox * math.sin(tilt) + oy * math.cos(tilt))
            pr = 7 + int(4 * math.sin(p_ang))  # To hơn khi bay ở nửa gần ống kính, nhỏ hơn khi ở xa
            draw.ellipse((px - pr - 4, py - pr - 4, px + pr + 4, py + pr + 4), fill=(p_col[0], p_col[1], p_col[2], 85))
            draw.ellipse((px - pr, py - pr, px + pr, py + pr), fill=(255, 255, 245, 255), outline=p_col, width=2)


def _split_text_into_subtitle_chunks(text: str, max_words: int = 11) -> List[str]:
    words = text.split()
    if not words:
        return [""]
    return [" ".join(words[i : i + max_words]) for i in range(0, len(words), max_words)]


def _wrap_text(text: str, max_chars: int = 32) -> List[str]:
    words = text.split()
    lines: List[str] = []
    cur: List[str] = []
    cur_len = 0
    for w in words:
        if cur_len + len(w) + (1 if cur else 0) <= max_chars:
            cur.append(w)
            cur_len += len(w) + (1 if len(cur) > 1 else 0)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
            cur_len = len(w)
    if cur:
        lines.append(" ".join(cur))
    return lines[:2]


def _render_foreground_ui_and_actor(
    base_rgb: np.ndarray,
    frame_idx: int,
    total_frames: int,
    fps: int,
    rms_val: float,
    archetype: str,
    topic_title: str,
    scene_label: str,
    active_sub_chunk: str,
    chunk_progress: float,
) -> np.ndarray:
    """
    Kết hợp Thực thể Hoạt hình 3D Tiền cảnh + Hạt Đom đóm Bokeh + Phụ đề Karaoke CapCut/TikTok.
    """
    h, w, _ = base_rgb.shape
    t = frame_idx / float(fps)
    f = _get_font_bank()

    pil_img = Image.fromarray(base_rgb, mode="RGB")
    draw = ImageDraw.Draw(pil_img, "RGBA")

    # 1. Vẽ Thực thể Hoạt hình 3D chuyển động thật ở Tiền cảnh
    _draw_3d_animated_actor(draw, archetype, t, rms_val, w, h)

    # 2. Hạt Đom Đóm / Bokeh Ánh Sáng 3D bay lượn quanh nhân vật
    for i in range(18):
        speed = 0.04 + (i % 5) * 0.015
        py = ((1.0 - ((t * speed + i * 0.13) % 1.0)) * (h * 0.78))
        px = ((0.10 + 0.80 * ((i * 0.37) % 1.0)) * w) + math.sin(t * 2.0 + i) * 20.0
        radius = 2 + (i % 3) + int(rms_val * 3.0)
        alpha = int(85 + 115 * (0.5 + 0.5 * math.sin(t * 3.8 + i)) * (0.5 + 0.5 * rms_val))
        color = (255, 232, 130, min(230, alpha)) if i % 2 == 0 else (95, 225, 255, min(220, alpha))
        draw.ellipse((px - radius * 2, py - radius * 2, px + radius * 2, py + radius * 2), fill=(color[0], color[1], color[2], alpha // 3))
        draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill=color)

    # 3. Nhãn Tiêu đề & Phân cảnh gọn ở góc trên
    draw.rounded_rectangle((16, 18, w - 16, 82), radius=12, fill=(10, 15, 28, 160), outline=(80, 200, 255, 130), width=1)
    title_short = topic_title if len(topic_title) <= 36 else topic_title[:33] + "..."
    draw.text((28, 24), title_short.upper(), fill=(255, 218, 95, 255), font=f["badge"])
    draw.text((28, 50), f"▸ {scene_label}", fill=(225, 242, 255, 245), font=f["scene_tag"])

    # 4. Phụ đề ngắn 2 dòng kiểu CapCut/TikTok ở vùng dưới
    sub_lines = _wrap_text(active_sub_chunk, max_chars=30)
    active_line_idx = min(max(0, len(sub_lines) - 1), int(chunk_progress * len(sub_lines)))
    y_sub = h - 148
    for idx, line in enumerate(sub_lines):
        is_curr = idx == active_line_idx
        color = (255, 238, 75, 255) if is_curr else (255, 255, 255, 235)
        bbox = draw.textbbox((0, 0), line, font=f["sub"])
        tw = bbox[2] - bbox[0]
        x_pos = max(18, (w - tw) // 2)
        draw.text(
            (x_pos, y_sub),
            line,
            fill=color,
            font=f["sub"],
            stroke_width=4,
            stroke_fill=(8, 10, 18, 255),
        )
        y_sub += 38

    # 5. Thanh Tiến Trình Video dưới đáy
    prog_w = int((w - 32) * (frame_idx / float(max(1, total_frames - 1))))
    draw.rectangle((16, h - 18, w - 16, h - 12), fill=(35, 45, 68, 180))
    draw.rectangle((16, h - 18, 16 + prog_w, h - 12), fill=(56, 220, 255, 255))

    return np.array(pil_img, dtype=np.uint8)


def render_complete_scenery_video_with_audio(
    run_dir: Path,
    wav_path: Path,
    audio_sync_features: Dict[str, Any],
    scripture_reference: str,
    retrieved_scripture: str = "",
    visual_archetype: str = "butterfly_chaos_wings",
    visual_labels: List[str] | None = None,
    scene_action_prompt: str = "",
    seed: int = 123456,
) -> Dict[str, Any]:
    """
    Kết xuất Video Hoạt Hình Điện Ảnh 3D Sống Động (4 Phân cảnh 2x2 Độc lập + 2.5D Living Scene Warping +
    Thực thể 3D Cử động Tiền cảnh + Giọng đọc Neural VITS Tiếng Việt).
    """
    import imageio_ffmpeg

    width, height = IMAGE_WIDTH, IMAGE_HEIGHT
    fps = int(audio_sync_features.get("video_fps", VIDEO_FPS))
    total_frames = int(audio_sync_features["total_video_frames"])
    rms_env = audio_sync_features["rms_envelope_per_frame"]
    phases = audio_sync_features["timeline_phases"]
    base_keyframe_path = run_dir / "prepped_keyframe.jpg"
    voiceover_wav_path = wav_path
    scripture_ref = scripture_reference

    labels = visual_labels or [
        "Cảnh 1: Khoảnh khắc Khởi nguồn",
        "Cảnh 2: Sóng Năng lượng Lan tỏa",
        "Cảnh 3: Cao trào Biến đổi Vũ trụ",
        "Cảnh 4: Bình minh Giác ngộ",
    ]
    while len(labels) < 4:
        labels.append(labels[-1])

    # 1. Tải 4 phân cảnh Hoạt hình 3D độc lập từ lưới 2x2 Grid Storyboard
    scenes_pil = _fetch_ai_4panel_storyboard_scenes(
        run_dir=run_dir,
        topic_title=scripture_ref,
        scene_action_prompt=scene_action_prompt or scripture_ref,
        seed=seed,
        width=width,
        height=height,
    )
    scenes_np = [np.array(im, dtype=np.uint8) for im in scenes_pil]

    # Lưu khung hình đại diện vào `base_keyframe_path` cho Chốt chặn Visual Gate 1
    preview_arr = _apply_living_25d_scene_motion(scenes_np[0], 0.35, 1.2, 0, 0.65)
    preview_arr = _render_foreground_ui_and_actor(
        base_rgb=preview_arr,
        frame_idx=int(total_frames * 0.2),
        total_frames=total_frames,
        fps=fps,
        rms_val=0.65,
        archetype=visual_archetype,
        topic_title=scripture_ref,
        scene_label=labels[0],
        active_sub_chunk=phases["phase_1_main_scene_narration"]["text"][:60],
        chunk_progress=0.3,
    )
    Image.fromarray(preview_arr).save(str(base_keyframe_path), quality=95)

    # 2. Chia thời lượng video thành 4 Phân cảnh Điện ảnh (Scene 0 -> Scene 3) với chuyển cảnh Cross-Dissolve 0.8s
    s_bounds = [0, int(total_frames * 0.25), int(total_frames * 0.52), int(total_frames * 0.78), total_frames]
    dissolve_frames = max(6, int(0.80 * fps))

    # 3. Chuẩn bị danh sách các cụm phụ đề ngắn theo 3 phần lời bình
    p1_end = phases["phase_1_main_scene_narration"]["end_frame"]
    p2_end = phases["phase_2_outro_moral_lesson"]["end_frame"]
    phase_Bounds = [
        (0, p1_end, phases["phase_1_main_scene_narration"]["text"]),
        (p1_end, p2_end, phases["phase_2_outro_moral_lesson"]["text"]),
        (p2_end, total_frames, phases["phase_3_closing_prayer"]["text"]),
    ]
    phase_chunks = [_split_text_into_subtitle_chunks(b[2], max_words=11) for b in phase_Bounds]

    # 4. Stream trực tiếp từng khung hình 30fps qua `imageio-ffmpeg` (`libx264` + `aac` `.mp4`)
    final_mp4_path = run_dir / "final_master.mp4"
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{width}x{height}",
        "-pix_fmt", "rgb24",
        "-r", str(fps),
        "-i", "-",
        "-i", str(voiceover_wav_path),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "ultrafast",
        "-crf", "21",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(final_mp4_path),
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for f_idx in range(total_frames):
            rms_val = rms_env[f_idx] if f_idx < len(rms_env) else 0.0
            t_sec = f_idx / float(fps)

            # Xác định Phân cảnh hiện tại (0..3)
            s_idx = 0
            for k in range(4):
                if s_bounds[k] <= f_idx <= s_bounds[k + 1]:
                    s_idx = k
                    break
            s_start, s_end = s_bounds[s_idx], s_bounds[s_idx + 1]
            local_prog = (f_idx - s_start) / float(max(1, s_end - s_start))

            # Render cảnh 2.5D Living Environment (Parallax + Sóng gió + God-rays)
            cur_rgb = _apply_living_25d_scene_motion(scenes_np[s_idx], local_prog, t_sec, s_idx, rms_val)

            # Cross-dissolve mượt sang cảnh tiếp theo ở cuối mỗi phân cảnh
            if s_idx < 3 and (s_end - f_idx) <= dissolve_frames:
                alpha = 1.0 - ((s_end - f_idx) / float(dissolve_frames))
                next_rgb = _apply_living_25d_scene_motion(scenes_np[s_idx + 1], 0.0, t_sec, s_idx + 1, rms_val)
                cur_rgb = (cur_rgb.astype(np.float32) * (1.0 - alpha) + next_rgb.astype(np.float32) * alpha).astype(np.uint8)

            # Xác định câu phụ đề ngắn đang đọc
            p_idx = 0 if f_idx < p1_end else (1 if f_idx < p2_end else 2)
            p_s, p_e, _ = phase_Bounds[p_idx]
            p_prog = (f_idx - p_s) / float(max(1, p_e - p_s))
            chunks = phase_chunks[p_idx]
            c_idx = min(len(chunks) - 1, int(p_prog * len(chunks)))
            c_prog = (p_prog * len(chunks)) - c_idx

            frame_rgb = _render_foreground_ui_and_actor(
                base_rgb=cur_rgb,
                frame_idx=f_idx,
                total_frames=total_frames,
                fps=fps,
                rms_val=rms_val,
                archetype=visual_archetype,
                topic_title=scripture_ref,
                scene_label=labels[s_idx],
                active_sub_chunk=chunks[c_idx],
                chunk_progress=c_prog,
            )
            proc.stdin.write(frame_rgb.tobytes())
    finally:
        if proc.stdin:
            proc.stdin.close()
        proc.wait()

    ass_path = run_dir / "subtitles.ass"
    ass_path.write_text(
        f"[Script Info]\nTitle: {scripture_ref}\nScriptType: v4.00+\nPlayResX: {width}\nPlayResY: {height}\n",
        encoding="utf-8",
    )

    return {
        "final_master_video_path": str(final_mp4_path),
        "subtitles_ass_path": str(ass_path),
        "ass_subtitle_path": str(ass_path),
        "prepped_visual_path": str(base_keyframe_path),
        "total_rendered_frames": total_frames,
        "video_fps": fps,
        "duration_sec": audio_sync_features["duration_sec"],
    }


generate_synchronized_christian_video = render_complete_scenery_video_with_audio

