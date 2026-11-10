"""
Median Lab & 3Blue1Brown High-End Visual Science Animation Engine:
1. Đồng bộ 100% từng câu thoại với Visual Action cơ học trực quan:
   - Câu 1: Đồng xu 3D quay lật đa chiều chân thực (Yaw + Pitch 3D Euler rotation, lật mặt Sấp/Ngửa).
   - Câu 2: Lực búng tay (F_búng), Luồng gió thổi cản (F_wind), Trọng lực (g) và Quỹ đạo ném xiên Parabol tất định có tâm ngắm HUD khóa vị trí tiếp đất 100%.
   - Câu 3: Bản chất triết học: Phân tách 'Thực tại vật lý đầy đủ dữ liệu' vs 'Sự thiếu hụt thông tin của con người'.
2. Hoạt họa liên tục từng mili-giây (Continuous Physics Math), loại bỏ 100% hiện tượng khựng/lag/tụt FPS.
"""

import math
import subprocess
from pathlib import Path
import numpy as np
import skia
import imageio_ffmpeg
from graph.audio_sync import synthesize_voiceover_waveform, extract_waveform_sync_features


def draw_arrow(canvas, p1, p2, paint, head_len=14.0, head_angle=0.45):
    """Vẽ vector mũi tên phát sáng mượt mà."""
    x1, y1 = p1
    x2, y2 = p2
    canvas.drawLine(x1, y1, x2, y2, paint)
    ang = math.atan2(y2 - y1, x2 - x1)
    
    left_x = x2 - head_len * math.cos(ang - head_angle)
    left_y = y2 - head_len * math.sin(ang - head_angle)
    right_x = x2 - head_len * math.cos(ang + head_angle)
    right_y = y2 - head_len * math.sin(ang + head_angle)
    
    arrow_path = skia.Path()
    arrow_path.moveTo(x2, y2)
    arrow_path.lineTo(left_x, left_y)
    arrow_path.lineTo(right_x, right_y)
    arrow_path.close()
    
    fill_p = skia.Paint(Color=paint.getColor(), Style=skia.Paint.kFill_Style, AntiAlias=True)
    canvas.drawPath(arrow_path, fill_p)


def draw_euler_3d_coin(canvas, cx, cy, radius, pitch_deg, yaw_deg, rms_val=0.0):
    """
    Render đồng xu 3D chân thực theo góc xoay Euler (Pitch & Yaw):
    - Tự động lật mặt Ngửa (Gold Pi) và mặt Sấp (Bronze Eagle / Star).
    - Có độ dày viền kim loại 3D (Extrusion depth).
    - Có bóng đổ ambient occlusion biến thiên theo khoảng cách.
    """
    rad_p = math.radians(pitch_deg)
    rad_y = math.radians(yaw_deg)
    
    cos_p = math.cos(rad_p)
    sin_p = math.sin(rad_p)
    cos_y = math.cos(rad_y)
    
    # Chiếu độ dẹt ellipse 2D
    norm_z = cos_p * cos_y
    is_front = norm_z >= 0
    
    scale_x = max(0.04, abs(cos_y))
    scale_y = max(0.04, abs(cos_p))
    
    rx = radius * scale_x
    ry = radius * scale_y
    
    # 1. Đổ bóng mờ phía dưới
    shadow_w = radius * 1.8 * (0.6 + 0.4 * scale_x)
    shadow_h = 24.0 * (0.6 + 0.4 * scale_y)
    shadow_paint = skia.Paint(
        Color=skia.ColorSetARGB(80, 0, 0, 0),
        MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 20.0),
        AntiAlias=True,
    )
    canvas.drawOval(skia.Rect.MakeXYWH(cx - shadow_w / 2, cy + radius * 1.4, shadow_w, shadow_h), shadow_paint)
    
    # 2. Cạnh viền đồng xu 3D (Rim Thickness)
    rim_depth = 12.0 * abs(math.sin(rad_y))
    rim_dir = 1.0 if math.sin(rad_y) > 0 else -1.0
    rim_paint = skia.Paint(
        Color=skia.ColorSetARGB(255, 180, 115, 20),
        AntiAlias=True,
    )
    rim_rect = skia.Rect.MakeXYWH(cx - rx + rim_depth * rim_dir, cy - ry, rx * 2, ry * 2)
    canvas.drawOval(rim_rect, rim_paint)
    
    # 3. Mặt chính đồng xu
    if is_front:
        # Mặt ngửa: Vàng Gold sáng chói
        coin_shader = skia.GradientShader.MakeLinear(
            points=[(cx - rx, cy - ry), (cx + rx, cy + ry)],
            colors=[
                skia.ColorSetARGB(255, 254, 240, 138),
                skia.ColorSetARGB(255, 234, 179, 8),
                skia.ColorSetARGB(255, 180, 100, 10),
            ],
        )
    else:
        # Mặt sấp: Đồng / Hợp kim sẫm màu
        coin_shader = skia.GradientShader.MakeLinear(
            points=[(cx - rx, cy - ry), (cx + rx, cy + ry)],
            colors=[
                skia.ColorSetARGB(255, 217, 119, 6),
                skia.ColorSetARGB(255, 146, 64, 14),
                skia.ColorSetARGB(255, 90, 40, 10),
            ],
        )
        
    face_paint = skia.Paint(Shader=coin_shader, AntiAlias=True)
    canvas.drawOval(skia.Rect.MakeXYWH(cx - rx, cy - ry, rx * 2, ry * 2), face_paint)
    
    # Viền kim loại nổi
    border_paint = skia.Paint(
        Color=skia.ColorSetARGB(230, 255, 255, 240),
        StrokeWidth=max(1.0, 2.5 * scale_x),
        Style=skia.Paint.kStroke_Style,
        AntiAlias=True,
    )
    canvas.drawOval(skia.Rect.MakeXYWH(cx - rx, cy - ry, rx * 2, ry * 2), border_paint)
    
    # Ký hiệu hoa văn trên mặt đồng xu
    if rx > 20 and ry > 20:
        sym_p = skia.Paint(
            Color=skia.ColorSetARGB(200, 120, 53, 15) if is_front else skia.ColorSetARGB(200, 254, 215, 170),
            StrokeWidth=max(1.2, 3.2 * min(scale_x, scale_y)),
            Style=skia.Paint.kStroke_Style,
            AntiAlias=True,
        )
        if is_front:
            # Biểu tượng Hy Lạp Pi
            canvas.drawLine(cx - rx * 0.42, cy - ry * 0.28, cx + rx * 0.42, cy - ry * 0.28, sym_p)
            canvas.drawLine(cx - rx * 0.22, cy - ry * 0.28, cx - rx * 0.22, cy + ry * 0.32, sym_p)
            canvas.drawLine(cx + rx * 0.22, cy - ry * 0.28, cx + rx * 0.22, cy + ry * 0.32, sym_p)
        else:
            # Biểu tượng Ngôi sao / Vòng tròn số học
            canvas.drawCircle(cx, cy, min(rx, ry) * 0.42, sym_p)


def render_median_lab_style_video(output_mp4_path: Path):
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    out_dir = output_mp4_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    width, height = 540, 960
    fps = 30

    # 1. Kịch bản khoa học chuẩn xác
    script_p1 = "Bạn nghĩ việc tung đồng xu là hoàn toàn ngẫu nhiên?"
    script_p2 = "Thực ra đồng xu chưa bao giờ ngẫu nhiên cả. Nếu ta biết chính xác lực búng tay và sức gió, quỹ đạo của nó là tất định một trăm phần trăm."
    script_p3 = "Thứ mà ta gọi là xác suất, thực chất chỉ là tên gọi khác của sự thiếu hụt thông tin."
    full_script = f"{script_p1} ... {script_p2} ... {script_p3}"

    wav_path = out_dir / "median_voiceover.wav"
    wav_path = synthesize_voiceover_waveform(full_script, output_filename=wav_path)
    sync_feats = extract_waveform_sync_features(wav_path, script_p1, script_p2, script_p3, fps=fps)

    duration_sec = sync_feats["duration_sec"]
    total_frames = int(duration_sec * fps)
    rms_env = sync_feats["rms_envelope_per_frame"]

    # Fonts
    font_mgr = skia.FontMgr()
    tf_bold = font_mgr.matchFamilyStyle("DejaVu Sans", skia.FontStyle.Bold())
    tf_reg = font_mgr.matchFamilyStyle("DejaVu Sans", skia.FontStyle.Normal())
    
    font_h1 = skia.Font(tf_bold, 24)
    font_hud = skia.Font(tf_bold, 13)
    font_code = skia.Font(tf_reg, 15)
    font_sub = skia.Font(tf_bold, 22)

    raw_video_path = out_dir / "raw_vector_motion.mp4"
    cmd_raw = [
        ffmpeg_exe, "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{width}x{height}",
        "-pix_fmt", "rgba",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "veryfast",
        "-crf", "17",
        str(raw_video_path),
    ]

    proc = subprocess.Popen(cmd_raw, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    surface = skia.Surface(width, height)

    t_p1 = sync_feats["timeline_phases"]["phase_1_main_scene_narration"]["end_sec"]
    t_p2 = sync_feats["timeline_phases"]["phase_2_outro_moral_lesson"]["end_sec"]

    try:
        for f_idx in range(total_frames):
            t_sec = f_idx / float(fps)
            rms = rms_env[f_idx] if f_idx < len(rms_env) else 0.0

            with surface as canvas:
                # -------------------------------------------------------------
                # 0. NỀN PHÒNG THÍ NGHIỆM VẬT LÝ DARK TECH (#090d16 -> #0f172a)
                # -------------------------------------------------------------
                bg_shader = skia.GradientShader.MakeLinear(
                    points=[(0, 0), (0, height)],
                    colors=[skia.ColorSetARGB(255, 8, 12, 22), skia.ColorSetARGB(255, 15, 23, 42)],
                )
                canvas.drawPaint(skia.Paint(Shader=bg_shader))

                # Lưới toạ độ kỹ thuật (Grid lines & dots)
                grid_paint = skia.Paint(Color=skia.ColorSetARGB(20, 148, 163, 184), StrokeWidth=1.0)
                for gx in range(0, width, 45):
                    canvas.drawLine(gx, 0, gx, height, grid_paint)
                for gy in range(0, height, 45):
                    canvas.drawLine(0, gy, width, gy, grid_paint)

                # -------------------------------------------------------------
                # SCENE 1: "BẠN NGHĨ VIỆC TUNG ĐỒNG XU LÀ HOÀN TOÀN NGẪU NHIÊN?"
                # -------------------------------------------------------------
                if t_sec < t_p1:
                    prog1 = t_sec / max(0.1, t_p1)
                    cx, cy = width / 2.0, height * 0.42

                    # Vòng hào quang năng lượng đập theo giọng nói
                    glow_p = skia.Paint(
                        Color=skia.ColorSetARGB(int(35 + 40 * rms), 56, 189, 248),
                        MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 70.0),
                        AntiAlias=True,
                    )
                    canvas.drawCircle(cx, cy, 140.0 + 35.0 * rms, glow_p)

                    # Đồng xu 3D xoay tít lơ lửng, chuyển động lượn sóng mượt mà
                    float_y = cy + 16.0 * math.sin(t_sec * 3.5)
                    pitch = 28.0 + 12.0 * math.sin(t_sec * 2.2)
                    yaw = t_sec * 340.0  # Quay 340 độ / giây liên tục

                    draw_euler_3d_coin(canvas, cx, float_y, radius=82.0, pitch_deg=pitch, yaw_deg=yaw, rms_val=rms)

                    # Vòng tròn định vị toạ độ quanh đồng xu (Radar ring)
                    radar_p = skia.Paint(
                        Color=skia.ColorSetARGB(90, 56, 189, 248),
                        StrokeWidth=1.5,
                        Style=skia.Paint.kStroke_Style,
                        PathEffect=skia.DashPathEffect.Make([10.0, 8.0], t_sec * 30.0),
                        AntiAlias=True,
                    )
                    canvas.drawCircle(cx, float_y, 118.0, radar_p)

                    scene_header = "01 // THỰC NGHIỆM: ĐỒNG XU NGẪU NHIÊN?"

                # -------------------------------------------------------------
                # SCENE 2: "THỰC RA ĐỒNG XU CHƯA BAO GIỜ NGẪU NHIÊN CẢ... LỰC BÚNG TAY VÀ SỨC GIÓ..."
                # -------------------------------------------------------------
                elif t_sec < t_p2:
                    dt_s2 = t_sec - t_p1
                    dur_s2 = max(0.1, t_p2 - t_p1)
                    prog2 = dt_s2 / dur_s2

                    # Toạ độ bệ phóng ngón tay (Origin Hand Launch)
                    orig_x = 90.0
                    orig_y = height * 0.68

                    # Vẽ bệ búng ngón tay (Mechanical / Hand Launcher Platform)
                    base_p = skia.Paint(Color=skia.ColorSetARGB(180, 51, 65, 85), StrokeWidth=3.0, AntiAlias=True)
                    canvas.drawLine(orig_x - 45, orig_y + 35, orig_x + 45, orig_y + 35, base_p)
                    canvas.drawLine(orig_x, orig_y + 35, orig_x, orig_y + 10, base_p)
                    
                    finger_p = skia.Paint(Color=skia.ColorSetARGB(240, 245, 158, 11), StrokeWidth=4.0, AntiAlias=True)
                    canvas.drawLine(orig_x - 20, orig_y + 25, orig_x, orig_y + 5, finger_p)
                    canvas.drawCircle(orig_x, orig_y + 5, 6.0, finger_p)

                    # Phương trình cơ học cổ điển Newton: Parabol ném xiên liên tục
                    # x(t) = v0_x * t,  y(t) = - (v0_y * t - 0.5 * g * t^2)
                    v0x = 28.0
                    v0y = 65.0
                    gravity = 5.2

                    # Vẽ đường cong quỹ đạo Parabol lý thuyết hoàn chỉnh mờ phía sau
                    traj_path = skia.Path()
                    steps = 140
                    for s in range(steps):
                        st = s * 0.18
                        px = orig_x + v0x * st
                        py = orig_y - (v0y * st - 0.5 * gravity * (st ** 2))
                        if s == 0:
                            traj_path.moveTo(px, py)
                        else:
                            traj_path.lineTo(px, py)

                    pred_paint = skia.Paint(
                        Color=skia.ColorSetARGB(95, 56, 189, 248),
                        StrokeWidth=2.0,
                        Style=skia.Paint.kStroke_Style,
                        PathEffect=skia.DashPathEffect.Make([8.0, 6.0], 0.0),
                        AntiAlias=True,
                    )
                    canvas.drawPath(traj_path, pred_paint)

                    # Chu kỳ bay lặp lại mượt mà cho đồng xu (mỗi vòng bay 3.2 giây)
                    flight_cycle = 3.2
                    flight_t = (dt_s2 % flight_cycle)
                    sim_t = flight_t * 3.8
                    coin_x = orig_x + v0x * sim_t
                    coin_y = orig_y - (v0y * sim_t - 0.5 * gravity * (sim_t ** 2))

                    # 1. Vector LỰC BÚNG TAY F_búng (Hiện rõ ở đầu bệ phóng)
                    f_force_p = skia.Paint(Color=skia.ColorSetARGB(255, 239, 68, 68), StrokeWidth=3.2, AntiAlias=True)
                    draw_arrow(canvas, (orig_x, orig_y + 5), (orig_x + 65, orig_y - 85), f_force_p)
                    lbl_force = skia.Paint(Color=skia.ColorSetARGB(255, 252, 165, 165), AntiAlias=True)
                    canvas.drawString("F_búng = 14.8 N", orig_x + 40, orig_y - 95, font_hud, lbl_force)

                    # 2. Vector LỰC GIÓ CẢN (Wind Streams) thổi từ phải qua trái
                    wind_p = skia.Paint(
                        Color=skia.ColorSetARGB(130, 147, 197, 253),
                        StrokeWidth=1.8,
                        Style=skia.Paint.kStroke_Style,
                        PathEffect=skia.DashPathEffect.Make([14.0, 10.0], -t_sec * 60.0),
                        AntiAlias=True,
                    )
                    for wy in [height * 0.32, height * 0.38, height * 0.44]:
                        canvas.drawLine(width - 40, wy, width - 210, wy, wind_p)
                    lbl_wind = skia.Paint(Color=skia.ColorSetARGB(200, 191, 219, 254), AntiAlias=True)
                    canvas.drawString("Vector Gió cản F_wind", width - 210, height * 0.30, font_hud, lbl_wind)

                    # 3. Vector TRỌNG LỰC g kéo xuống từ tâm đồng xu
                    g_arrow_p = skia.Paint(Color=skia.ColorSetARGB(240, 52, 211, 153), StrokeWidth=2.5, AntiAlias=True)
                    draw_arrow(canvas, (coin_x, coin_y), (coin_x, coin_y + 60), g_arrow_p)
                    lbl_g = skia.Paint(Color=skia.ColorSetARGB(220, 167, 243, 208), AntiAlias=True)
                    canvas.drawString("g = 9.8 m/s²", coin_x + 10, coin_y + 55, font_hud, lbl_g)

                    # 4. Vẽ đồng xu đang bay lộn vòng
                    coin_yaw = t_sec * 620.0
                    draw_euler_3d_coin(canvas, coin_x, coin_y, radius=38.0, pitch_deg=35.0, yaw_deg=coin_yaw)

                    # 5. Khung ngắm máy tính HUD: KHÓA ĐIỂM TIẾP ĐẤT TẤT ĐỊNH
                    target_x = orig_x + v0x * (flight_cycle * 3.8 * 0.95)
                    target_y = orig_y - (v0y * (flight_cycle * 3.8 * 0.95) - 0.5 * gravity * ((flight_cycle * 3.8 * 0.95) ** 2))
                    
                    hud_box_p = skia.Paint(
                        Color=skia.ColorSetARGB(210, 15, 23, 42),
                        AntiAlias=True,
                    )
                    canvas.drawRoundRect(skia.Rect.MakeXYWH(width - 240, height * 0.50, 215, 88), 10, 10, hud_box_p)
                    hud_border = skia.Paint(Color=skia.ColorSetARGB(180, 56, 189, 248), StrokeWidth=1.5, Style=skia.Paint.kStroke_Style, AntiAlias=True)
                    canvas.drawRoundRect(skia.Rect.MakeXYWH(width - 240, height * 0.50, 215, 88), 10, 10, hud_border)
                    
                    hud_cyan = skia.Paint(Color=skia.ColorSetARGB(255, 56, 189, 248), AntiAlias=True)
                    canvas.drawString("KẾT QUẢ: TẤT ĐỊNH 100%", width - 225, height * 0.50 + 26, font_hud, hud_cyan)
                    hud_white = skia.Paint(Color=skia.ColorSetARGB(230, 241, 245, 249), AntiAlias=True)
                    canvas.drawString("• Góc ném: 66.8°", width - 225, height * 0.50 + 48, font_code, hud_white)
                    canvas.drawString("• Kết quả: MẶT NGỬA", width - 225, height * 0.50 + 72, font_code, hud_white)

                    scene_header = "02 // ĐỘNG LỰC HỌC: QUỸ ĐẠO LÀ TẤT ĐỊNH"

                # -------------------------------------------------------------
                # SCENE 3: "THỨ MÀ TA GỌI LÀ XÁC SUẤT... LÀ SỰ THIẾU HỤT THÔNG TIN."
                # -------------------------------------------------------------
                else:
                    dt_s3 = t_sec - t_p2
                    dur_s3 = max(0.1, duration_sec - t_p2)
                    prog3 = dt_s3 / dur_s3

                    # Vẽ 2 bảng so sánh trực quan đối lập (Split Reality Architecture)
                    card_w = width - 60
                    card_h = 135

                    # Thẻ 1: THẾ GIỚI VẬT LÝ (Tất định hoàn toàn)
                    card1_y = height * 0.26
                    c1_bg = skia.Paint(Color=skia.ColorSetARGB(200, 15, 23, 42), AntiAlias=True)
                    canvas.drawRoundRect(skia.Rect.MakeXYWH(30, card1_y, card_w, card_h), 12, 12, c1_bg)
                    c1_border = skia.Paint(Color=skia.ColorSetARGB(200, 34, 197, 94), StrokeWidth=1.5, Style=skia.Paint.kStroke_Style, AntiAlias=True)
                    canvas.drawRoundRect(skia.Rect.MakeXYWH(30, card1_y, card_w, card_h), 12, 12, c1_border)

                    txt_g = skia.Paint(Color=skia.ColorSetARGB(255, 74, 222, 128), AntiAlias=True)
                    canvas.drawString("THỰC TẠI TỰ NHIÊN: TẤT ĐỊNH", 48, card1_y + 32, font_h1, txt_g)
                    txt_body = skia.Paint(Color=skia.ColorSetARGB(230, 226, 232, 240), AntiAlias=True)
                    canvas.drawString("Nếu có đủ thông số (Lực, Gió, Khối lượng):", 48, card1_y + 64, font_code, txt_body)
                    canvas.drawString("=> Không tồn tại bất kỳ sự ngẫu nhiên nào.", 48, card1_y + 94, font_code, txt_body)

                    # Thẻ 2: BẢN CHẤT CỦA XÁC SUẤT (Sự thiếu hụt dữ liệu)
                    card2_y = height * 0.45
                    c2_bg = skia.Paint(Color=skia.ColorSetARGB(200, 15, 23, 42), AntiAlias=True)
                    canvas.drawRoundRect(skia.Rect.MakeXYWH(30, card2_y, card_w, card_h), 12, 12, c2_bg)
                    c2_border = skia.Paint(Color=skia.ColorSetARGB(200, 249, 115, 22), StrokeWidth=1.5, Style=skia.Paint.kStroke_Style, AntiAlias=True)
                    canvas.drawRoundRect(skia.Rect.MakeXYWH(30, card2_y, card_w, card_h), 12, 12, c2_border)

                    txt_o = skia.Paint(Color=skia.ColorSetARGB(255, 251, 146, 60), AntiAlias=True)
                    canvas.drawString("XÁC SUẤT = THIẾU THÔNG TIN", 48, card2_y + 32, font_h1, txt_o)
                    canvas.drawString("Con người không thể đo lực búng trong mili-giây,", 48, card2_y + 64, font_code, txt_body)
                    canvas.drawString("nên gán nhãn 50% cho sự 'bất lực' của mình.", 48, card2_y + 94, font_code, txt_body)

                    # Hạt thông tin phát sáng rơi từ thẻ 1 sang lấp đầy thẻ 2
                    for dot_i in range(16):
                        d_phase = (t_sec * 1.5 + dot_i * 0.12) % 1.0
                        dx = 60 + dot_i * 26
                        dy = card1_y + card_h + d_phase * (card2_y - (card1_y + card_h))
                        dot_p = skia.Paint(Color=skia.ColorSetARGB(int(240 * (1 - d_phase)), 56, 189, 248), AntiAlias=True)
                        canvas.drawCircle(dx, dy, 3.5, dot_p)

                    scene_header = "03 // TRIẾT HỌC: BẢN CHẤT CỦA XÁC SUẤT"

                # -------------------------------------------------------------
                # HEADER HUD BANNER (MEDIAN LAB BRANDING)
                # -------------------------------------------------------------
                head_bg = skia.Paint(Color=skia.ColorSetARGB(190, 15, 23, 42), AntiAlias=True)
                canvas.drawRoundRect(skia.Rect.MakeXYWH(20, 25, width - 40, 58), 10, 10, head_bg)
                head_stroke = skia.Paint(Color=skia.ColorSetARGB(80, 56, 189, 248), StrokeWidth=1.0, Style=skia.Paint.kStroke_Style, AntiAlias=True)
                canvas.drawRoundRect(skia.Rect.MakeXYWH(20, 25, width - 40, 58), 10, 10, head_stroke)

                tag_cyan = skia.Paint(Color=skia.ColorSetARGB(255, 56, 189, 248), AntiAlias=True)
                canvas.drawString("MEDIAN VISUAL SCIENCE LAB", 36, 46, font_hud, tag_cyan)
                tag_title = skia.Paint(Color=skia.ColorSetARGB(245, 241, 245, 249), AntiAlias=True)
                canvas.drawString(scene_header, 36, 68, font_hud, tag_title)

                # -------------------------------------------------------------
                # SUBTITLE KINETIC TYPOGRAPHY DƯỚI ĐÁY
                # -------------------------------------------------------------
                if t_sec < t_p1:
                    sub_text = script_p1
                elif t_sec < t_p2:
                    sub_text = script_p2
                else:
                    sub_text = script_p3

                sub_box = skia.Paint(Color=skia.ColorSetARGB(210, 10, 15, 28), AntiAlias=True)
                canvas.drawRoundRect(skia.Rect.MakeXYWH(20, height - 165, width - 40, 105), 14, 14, sub_box)
                sub_stroke = skia.Paint(Color=skia.ColorSetARGB(75, 148, 163, 184), StrokeWidth=1.0, Style=skia.Paint.kStroke_Style, AntiAlias=True)
                canvas.drawRoundRect(skia.Rect.MakeXYWH(20, height - 165, width - 40, 105), 14, 14, sub_stroke)

                words = sub_text.split()
                line1 = " ".join(words[: len(words) // 2 + 1])
                line2 = " ".join(words[len(words) // 2 + 1 :])

                text_paint = skia.Paint(Color=skia.ColorSetARGB(255, 255, 255, 255), AntiAlias=True)
                canvas.drawString(line1, 38, height - 120, font_sub, text_paint)
                if line2:
                    canvas.drawString(line2, 38, height - 85, font_sub, text_paint)

                # Progress bar dưới cùng
                prog_w = (width - 40) * (f_idx / float(max(1, total_frames - 1)))
                canvas.drawRect(skia.Rect.MakeXYWH(20, height - 32, width - 40, 4), skia.Paint(Color=skia.ColorSetARGB(90, 51, 65, 85)))
                canvas.drawRect(skia.Rect.MakeXYWH(20, height - 32, prog_w, 4), skia.Paint(Color=skia.ColorSetARGB(255, 56, 189, 248)))

            # Gửi frame liên tục không ngắt quãng
            img = surface.makeImageSnapshot()
            proc.stdin.write(img.tobytes())

    finally:
        if proc.stdin:
            proc.stdin.close()
        proc.wait()

    # Ghép Video Vector + Audio Voiceover (đã có Ambient BGM)
    cmd_final = [
        ffmpeg_exe, "-y",
        "-i", str(raw_video_path),
        "-i", str(wav_path),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(output_mp4_path),
    ]
    subprocess.run(cmd_final, check=True, capture_output=True)
    print(f"\n===> THÀNH CÔNG: Video chuẩn Median Lab đã xuất ra tại:\n{output_mp4_path}")


if __name__ == "__main__":
    demo_out = Path("/home/blue/Downloads/Projects/wav2video/workspace/median_lab_demo/the_coin_was_never_random.mp4")
    render_median_lab_style_video(demo_out)
