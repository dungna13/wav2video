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

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from config.settings import WORKSPACE_DIR
from graph.flow_bundler import prepare_flow_workspace, render_from_flow_clips
from graph.tiktok_uploader import auto_upload_video, get_login_status, launch_interactive_login
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


class FlowRenderRequest(BaseModel):
    run_dir: str
    sub_mode: str = "narration_full"


class AutoUploadTikTokRequest(BaseModel):
    video_path: str
    caption: str


@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_file = TEMPLATES_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy index.html")
    return index_file.read_text(encoding="utf-8")


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
            },
            config=config,
        )

        flow_info = prepare_flow_workspace(
            state,
            target_block_sec=req.block_sec,
            max_blocks=req.max_blocks,
        )

        manifest = json.loads(Path(flow_info["manifest_path"]).read_text(encoding="utf-8"))
        return {
            "status": "success",
            "run_dir": flow_info["workspace_dir"],
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
        master_video_path = Path(res["final_master_video_path"])
        return {
            "status": "success",
            "final_master_video_path": str(master_video_path),
            "video_url": f"/api/video-stream?path={str(master_video_path)}",
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

