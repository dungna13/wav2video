"""
Web Server UI/UX cho Wav2Video & Google Flow (`graph/web_app.py`).

Cung cấp giao diện Web trực quan:
  1. Nhập chủ đề ➜ Tự sinh kịch bản & 4 Prompts khối cho Google Flow.
  2. Bấm 1 nút Copy Prompt cho từng Block.
  3. Upload trực tiếp các clip đã tải từ Google Flow vào từng Block.
  4. Bấm "Ghép Video" ➜ Xem trước ngay lập tức trên trình duyệt với phụ đề chuẩn & nút Tải về.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from config.settings import WORKSPACE_DIR
from graph.audio_sync import synthesize_scene_voiceover
from graph.flow_bundler import prepare_flow_workspace, render_from_flow_clips
from graph.tiktok_uploader import auto_upload_video, get_login_status, launch_interactive_login
from graph.video_renderer import render_documentary_video
from graph.workflow import create_christian_short_video_app

app = FastAPI(title="Wav2Video Web Studio", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMPLATES_DIR = Path(__file__).parent / "ui_templates"


class FlowPrepRequest(BaseModel):
    topic: str
    model: str = "auto"
    max_blocks: int = 4
    block_sec: float = 14.0
    tts_engine: str = "edge-tts"
    tts_voice: str = "vi-VN-NamMinhNeural"
    tts_rate: str = "+12%"


class FlowRenderRequest(BaseModel):
    run_dir: str
    sub_mode: str = "narration_full"
    speed_factor: float = 1.0


class AutoUploadTikTokRequest(BaseModel):
    video_path: str
    caption: str


@app.get("/favicon.ico", include_in_schema=False)
async def get_favicon():
    return Response(status_code=204)


@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_file = TEMPLATES_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy index.html")
    return index_file.read_text(encoding="utf-8")


@app.get("/api/latest-flow")
async def api_latest_flow():
    """Tự động trả về thông tin dự án và danh sách Prompts gần nhất để giao diện nạp ngay lập tức."""
    flows = sorted(WORKSPACE_DIR.glob("flow_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for f in flows:
        mf = f / "flow_manifest.json"
        if mf.exists():
            try:
                manifest = json.loads(mf.read_text(encoding="utf-8"))
                clips_dir = f / "flow_clips"
                uploaded_files = [p.name for p in clips_dir.iterdir() if p.is_file()] if clips_dir.exists() else []
                master_video = f / "final_master.mp4"
                has_master = master_video.exists()
                return {
                    "status": "success",
                    "run_dir": str(f),
                    "topic_title": manifest.get("topic_title", ""),
                    "manifest": manifest,
                    "blocks": manifest.get("blocks", []),
                    "uploaded_files": uploaded_files,
                    "final_master": str(master_video) if has_master else None,
                    "video_url": f"/api/video-stream?path={str(master_video)}" if has_master else None,
                }
            except Exception:
                continue
    return {"status": "none"}


@app.post("/api/flow-prep")
async def api_flow_prep(req: FlowPrepRequest):
    topic = req.topic.strip()
    if not topic:
        return {"status": "error", "message": "Chủ đề không được để trống"}

    try:
        short_video_app = create_christian_short_video_app(stop_after_tier1=True)
        config = {"configurable": {"thread_id": f"web_prep_{int(time.time())}"}}

        state = short_video_app.invoke(
            {
                "user_request": topic,
                "intent_mode": "NO_HUMAN_BROLL",
                "preferred_narrative_model": req.model,
                "tts_engine": req.tts_engine,
                "tts_voice": req.tts_voice,
                "tts_rate": req.tts_rate,
            },
            config=config,
        )

        flow_info = prepare_flow_workspace(
            state,
            target_block_sec=req.block_sec,
            max_blocks=req.max_blocks,
        )

        manifest = json.loads(Path(flow_info["manifest_path"]).read_text(encoding="utf-8"))
        run_dir_val = flow_info.get("run_dir") or flow_info.get("workspace_dir") or ""
        return {
            "status": "success",
            "run_dir": run_dir_val,
            "workspace_dir": run_dir_val,
            "manifest": manifest,
            "blocks": flow_info["blocks"],
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/upload-clip")
async def api_upload_clip(
    run_dir: str = Form(...),
    block_index: int = Form(...),
    clip_file: UploadFile = File(...),
):
    target_dir = Path(run_dir) / "flow_clips"
    target_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(clip_file.filename).suffix.lower() or ".mp4"
    dest_path = target_dir / f"{block_index}{suffix}"

    with open(dest_path, "wb") as f:
        shutil.copyfileobj(clip_file.file, f)

    return {
        "status": "success",
        "saved_path": str(dest_path),
        "filename": dest_path.name,
        "size_bytes": dest_path.stat().st_size,
    }


@app.post("/api/flow-render")
async def api_flow_render(req: FlowRenderRequest):
    run_dir = Path(req.run_dir)
    if not run_dir.exists():
        return {"status": "error", "message": f"Thư mục không tồn tại: {run_dir}"}

    try:
        res = render_from_flow_clips(run_dir=run_dir, sub_mode=req.sub_mode)
        master_video_path_str = res.get("final_master_video_path") or res.get("rendered", {}).get("final_master_video_path")
        master_video_path = Path(master_video_path_str)

        # Nếu người dùng muốn tăng tốc video & giọng đọc (speed_factor khác 1.0):
        if req.speed_factor and abs(req.speed_factor - 1.0) > 0.02:
            import imageio_ffmpeg
            import subprocess

            fast_video_path = run_dir / f"final_master_fast_{req.speed_factor:.2f}x.mp4"
            ff = imageio_ffmpeg.get_ffmpeg_exe()
            cmd = [
                ff, "-y", "-i", str(master_video_path),
                "-filter_complex", f"[0:v]setpts=PTS/{req.speed_factor}[v];[0:a]atempo={req.speed_factor}[a]",
                "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                "-c:a", "aac", "-b:a", "192k",
                str(fast_video_path),
            ]
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode == 0 and fast_video_path.exists():
                master_video_path = fast_video_path

        return {
            "status": "success",
            "final_master_video_path": str(master_video_path),
            "video_url": f"/api/video-stream?path={str(master_video_path)}",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/render-custom-images")
async def api_render_custom_images(
    title: str = Form("Video từ ảnh tùy chọn"),
    tts_voice: str = Form("vi-VN-NamMinhNeural"),
    tts_rate: str = Form("+20%"),
    music_mood: str = Form("cinematic_piano_ambient"),
    sub_mode: str = Form("narration_full"),
    narrations_json: str = Form("[]"),
    files: List[UploadFile] = File(...),
):
    try:
        if not files:
            return {"status": "error", "message": "Vui lòng tải lên ít nhất 1 ảnh"}

        run_id = f"custom_img_{int(time.time())}"
        run_dir = WORKSPACE_DIR / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        try:
            narrations = json.loads(narrations_json)
        except Exception:
            narrations = []

        if not narrations or len(narrations) < len(files):
            narrations = [
                narrations[i] if i < len(narrations) and narrations[i].strip() else f"Hình ảnh số {i+1} trong câu chuyện."
                for i in range(len(files))
            ]

        saved_img_paths: List[Path] = []
        for i, file in enumerate(files):
            ext = Path(file.filename).suffix.lower() or ".jpg"
            dest = run_dir / f"scene_{i+1}{ext}"
            with open(dest, "wb") as f_out:
                shutil.copyfileobj(file.file, f_out)
            saved_img_paths.append(dest)

        wav_path, timings = synthesize_scene_voiceover(
            scene_texts=narrations,
            output_filename=run_dir / "audio_16k_mono.wav",
            voice=tts_voice,
            rate=tts_rate,
            music_mood=music_mood,
        )

        total_audio_sec = float(timings[-1][1]) + 0.35 if timings else 5.0
        camera_moves = ["zoom_in", "zoom_out", "pan_left", "pan_right"]

        scenes: List[Dict[str, Any]] = []
        for i, img_path in enumerate(saved_img_paths):
            cam = camera_moves[i % len(camera_moves)]
            scenes.append({
                "media_path": str(img_path),
                "media_type": "image",
                "camera": cam,
                "narration_vn": narrations[i],
                "subtitle_vn": narrations[i],
            })

        res = render_documentary_video(
            run_dir=run_dir,
            wav_path=wav_path,
            scenes=scenes,
            timings=timings,
            total_audio_sec=total_audio_sec,
            topic_title=title,
            sub_mode=sub_mode,
        )

        master_video_path = Path(res["final_master_video_path"])
        return {
            "status": "success",
            "run_dir": str(run_dir),
            "final_master_video_path": str(master_video_path),
            "video_url": f"/api/video-stream?path={str(master_video_path)}",
            "caption": title,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/tiktok/status")
async def api_tiktok_status():
    return get_login_status()


@app.post("/api/tiktok/login")
async def api_tiktok_login():
    import threading
    t = threading.Thread(target=launch_interactive_login, daemon=True)
    t.start()
    return {"status": "started", "message": "Đang mở trình duyệt để đăng nhập TikTok..."}


@app.post("/api/tiktok/auto-upload")
async def api_tiktok_auto_upload(req: AutoUploadTikTokRequest):
    v_path = Path(req.video_path)
    res = auto_upload_video(video_path=v_path, caption=req.caption, headless=False)
    return res


@app.get("/api/video-stream")
async def api_video_stream(path: str):
    video_path = Path(path)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy file video")
    return FileResponse(video_path, media_type="video/mp4", filename=video_path.name)


def start_server(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    print(f"\n🚀 Đang khởi động Wav2Video Web Studio tại: http://localhost:{port}")
    print(f"👉 Mở trình duyệt và truy cập: http://localhost:{port}\n")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_server()

