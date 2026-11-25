"""
Ứng dụng Desktop đơn giản cho người dùng phổ thông (Không cần biết code).
Chỉ cần mở app -> dán Gemini API Key -> nhập chủ đề (Prompt) -> bấm TẠO VIDEO NGAY.
Hỗ trợ giao diện cửa sổ (Tkinter) trên Windows/macOS/Linux và chế độ cấu hình nhanh trên Terminal nếu thiếu Tk.
"""

import json
import os
import platform
import queue
import re
import subprocess
import sys
import threading
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
ENV_EXAMPLE_PATH = BASE_DIR / ".env.example"
CONFIG_PATH = BASE_DIR / "app_config.json"
WORKSPACE_DIR = BASE_DIR / "workspace"

VOICE_OPTIONS = [
    ("vanthanhthu", "vanthanhthu — Nam trầm khoa học (Nhanh, khuyên dùng)"),
    ("review_phim", "review_phim — Nữ Review Phim (Dồn dập, kịch tính)"),
    ("gen_z", "gen_z — Nữ Gen Z (Tươi sáng, bắt trend)"),
    ("giat_gan", "giat_gan — Nam Giật Gân (Bí ẩn, tài liệu)"),
    ("nam_review", "nam_review — Nam Hiện Đại (Công nghệ, tài chính)"),
    ("clone", "clone — Giọng Clone Offline (từ workspace/voice-preview.mp3)"),
]

ASPECT_OPTIONS = [
    ("9:16", "9:16 — Dọc (TikTok / YouTube Shorts / Reels)"),
    ("16:9", "16:9 — Ngang (YouTube)"),
]

SUB_OPTIONS = [
    ("none", "none — Không phụ đề (Khung hình sạch 100%)"),
    ("tiktok_yellow", "tiktok_yellow — Phụ đề TikTok chữ vàng viền đen"),
]


def load_env_dict() -> Dict[str, str]:
    """Đọc các biến từ file .env (hoặc .env.example nếu chưa có .env)."""
    target = ENV_PATH if ENV_PATH.exists() else ENV_EXAMPLE_PATH
    data: Dict[str, str] = {}
    if not target.exists():
        return data
    for line in target.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        data[k] = v
    return data


def save_env_keys(updates: Dict[str, str]) -> None:
    """Cập nhật khóa API vào file .env mà vẫn giữ nguyên các cấu hình khác."""
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()
    elif ENV_EXAMPLE_PATH.exists():
        lines = ENV_EXAMPLE_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()
    else:
        lines = []

    remaining = dict(updates)
    new_lines: List[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in remaining:
                val = remaining.pop(key)
                new_lines.append(f'{key}="{val}"')
                continue
        new_lines.append(line)

    for key, val in remaining.items():
        new_lines.append(f'{key}="{val}"')

    ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def load_app_config() -> Dict[str, object]:
    """Đọc cấu hình lần chạy gần nhất từ app_config.json."""
    defaults: Dict[str, object] = {
        "topic": "Bí mật lăng mộ Tần Thủy Hoàng",
        "duration_mins": 3.0,
        "voice": "vanthanhthu",
        "aspect": "9:16",
        "sub_style": "none",
        "footage": "",
        "script_file": "",
    }
    if CONFIG_PATH.exists():
        try:
            loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                defaults.update(loaded)
        except Exception:
            pass
    return defaults


def save_app_config(cfg: Dict[str, object]) -> None:
    """Lưu cấu hình đơn giản vào app_config.json."""
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_cli_command(cfg: Dict[str, object]) -> List[str]:
    """Tạo lệnh chạy main.py từ cấu hình người dùng."""
    topic = str(cfg.get("topic") or "").strip() or "Bí mật lăng mộ Tần Thủy Hoàng"
    duration = str(cfg.get("duration_mins") or "3.0").strip()
    voice = str(cfg.get("voice") or "vanthanhthu").strip()
    aspect = str(cfg.get("aspect") or "9:16").strip()
    sub_style = str(cfg.get("sub_style") or "none").strip()
    footage = str(cfg.get("footage") or "").strip()
    script_file = str(cfg.get("script_file") or "").strip()

    cmd = [
        sys.executable,
        str(BASE_DIR / "main.py"),
        "--broll",
        topic,
        "--duration",
        duration,
        "--voice",
        voice,
        "--aspect",
        aspect,
        "--sub-style",
        sub_style,
    ]
    if footage:
        cmd.extend(["--footage", footage])
    if script_file:
        cmd.extend(["--script-file", script_file])
    return cmd


def open_folder(path: Path) -> None:
    """Mở file hoặc thư mục kết quả bằng trình quản lý tệp / trình phát mặc định."""
    if not path.suffix and not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    sys_name = platform.system()
    if sys_name == "Windows":
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys_name == "Darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def run_gui_app() -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext, ttk

    root = tk.Tk()
    root.title("wav2video — Tạo Video Tự Động (Không Cần Code)")
    root.geometry("820x720")
    root.minsize(720, 620)

    env_data = load_env_dict()
    cfg_data = load_app_config()

    gemini_key = env_data.get("GEMINI_API_KEY", "")
    if gemini_key == "YOUR_GEMINI_API_KEY_HERE":
        gemini_key = ""

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass

    main_frame = ttk.Frame(root, padding=14)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Header
    ttk.Label(
        main_frame,
        text="🎬 wav2video — Tạo Video Tài Liệu & B-Roll Tự Động",
        font=("Segoe UI", 14, "bold"),
    ).pack(anchor="w")
    ttk.Label(
        main_frame,
        text="Chỉ cần dán API Key + nhập Chủ đề (Prompt) rồi bấm Tạo Video Ngay.",
        foreground="#555555",
    ).pack(anchor="w", pady=(2, 10))

    # 1. API Key Frame
    api_frame = ttk.LabelFrame(main_frame, text="1. Cấu hình API Key (Tự động lưu vào .env)", padding=10)
    api_frame.pack(fill=tk.X, pady=(0, 8))

    ttk.Label(api_frame, text="Gemini API Key (*):").grid(row=0, column=0, sticky="w", padx=(0, 8))
    gemini_var = tk.StringVar(value=gemini_key)
    gemini_entry = ttk.Entry(api_frame, textvariable=gemini_var, show="*", width=55)
    gemini_entry.grid(row=0, column=1, sticky="ew", padx=(0, 6))

    show_key = tk.BooleanVar(value=False)

    def toggle_key() -> None:
        gemini_entry.config(show="" if show_key.get() else "*")

    ttk.Checkbutton(api_frame, text="Hiện", variable=show_key, command=toggle_key).grid(row=0, column=2, padx=(0, 6))

    ttk.Label(api_frame, text="Pexels Key (Tùy chọn):").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(6, 0))
    pexels_var = tk.StringVar(value=env_data.get("PEXELS_API_KEY", ""))
    ttk.Entry(api_frame, textvariable=pexels_var, width=55).grid(row=1, column=1, sticky="ew", padx=(0, 6), pady=(6, 0))
    api_frame.columnconfigure(1, weight=1)

    # 2. Prompt & Content Frame
    prompt_frame = ttk.LabelFrame(main_frame, text="2. Nội dung / Prompt Video", padding=10)
    prompt_frame.pack(fill=tk.X, pady=(0, 8))

    ttk.Label(prompt_frame, text="Chủ đề / Prompt:").grid(row=0, column=0, sticky="nw", padx=(0, 8))
    topic_text = tk.Text(prompt_frame, height=3, wrap=tk.WORD, font=("Segoe UI", 10))
    topic_text.insert("1.0", str(cfg_data.get("topic", "")))
    topic_text.grid(row=0, column=1, columnspan=2, sticky="ew")

    ttk.Label(prompt_frame, text="File kịch bản JSON (Tùy chọn):").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(8, 0))
    script_var = tk.StringVar(value=str(cfg_data.get("script_file", "")))
    ttk.Entry(prompt_frame, textvariable=script_var).grid(row=1, column=1, sticky="ew", pady=(8, 0), padx=(0, 6))

    def browse_script() -> None:
        p = filedialog.askopenfilename(
            title="Chọn file kịch bản JSON",
            initialdir=str(BASE_DIR),
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if p:
            script_var.set(p)

    ttk.Button(prompt_frame, text="Chọn file...", command=browse_script).grid(row=1, column=2, pady=(8, 0))
    prompt_frame.columnconfigure(1, weight=1)

    # 3. Video Settings Frame
    opt_frame = ttk.LabelFrame(main_frame, text="3. Tùy chỉnh Video", padding=10)
    opt_frame.pack(fill=tk.X, pady=(0, 8))

    ttk.Label(opt_frame, text="Thời lượng (phút):").grid(row=0, column=0, sticky="w", padx=(0, 8))
    dur_var = tk.StringVar(value=str(cfg_data.get("duration_mins", 3.0)))
    ttk.Combobox(opt_frame, textvariable=dur_var, values=["1.0", "2.0", "3.0", "4.0", "5.0"], width=10).grid(
        row=0, column=1, sticky="w", padx=(0, 16)
    )

    ttk.Label(opt_frame, text="Khổ video:").grid(row=0, column=2, sticky="w", padx=(0, 8))
    aspect_labels = [lbl for _, lbl in ASPECT_OPTIONS]
    cur_aspect = str(cfg_data.get("aspect", "9:16"))
    aspect_default = next((lbl for k, lbl in ASPECT_OPTIONS if k == cur_aspect), aspect_labels[0])
    aspect_var = tk.StringVar(value=aspect_default)
    ttk.Combobox(opt_frame, textvariable=aspect_var, values=aspect_labels, state="readonly", width=34).grid(
        row=0, column=3, sticky="ew"
    )

    ttk.Label(opt_frame, text="Giọng đọc:").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(8, 0))
    voice_labels = [lbl for _, lbl in VOICE_OPTIONS]
    cur_voice = str(cfg_data.get("voice", "vanthanhthu"))
    voice_default = next((lbl for k, lbl in VOICE_OPTIONS if k == cur_voice), voice_labels[0])
    voice_var = tk.StringVar(value=voice_default)
    ttk.Combobox(opt_frame, textvariable=voice_var, values=voice_labels, state="readonly").grid(
        row=1, column=1, columnspan=3, sticky="ew", pady=(8, 0)
    )

    ttk.Label(opt_frame, text="Phụ đề:").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=(8, 0))
    sub_labels = [lbl for _, lbl in SUB_OPTIONS]
    cur_sub = str(cfg_data.get("sub_style", "none"))
    sub_default = next((lbl for k, lbl in SUB_OPTIONS if k == cur_sub), sub_labels[0])
    sub_var = tk.StringVar(value=sub_default)
    ttk.Combobox(opt_frame, textvariable=sub_var, values=sub_labels, state="readonly").grid(
        row=2, column=1, columnspan=3, sticky="ew", pady=(8, 0)
    )

    ttk.Label(opt_frame, text="Video nền (B-Roll):").grid(row=3, column=0, sticky="w", padx=(0, 8), pady=(8, 0))
    footage_var = tk.StringVar(value=str(cfg_data.get("footage", "")))
    ttk.Entry(opt_frame, textvariable=footage_var).grid(row=3, column=1, columnspan=2, sticky="ew", pady=(8, 0), padx=(0, 6))

    def browse_footage() -> None:
        p = filedialog.askdirectory(title="Chọn thư mục chứa video nền (hoặc bỏ trống để tự tải)", initialdir=str(BASE_DIR))
        if p:
            footage_var.set(p)

    ttk.Button(opt_frame, text="Chọn thư mục...", command=browse_footage).grid(row=3, column=3, sticky="w", pady=(8, 0))
    opt_frame.columnconfigure(3, weight=1)

    # 4. Action Buttons
    btn_frame = ttk.Frame(main_frame)
    btn_frame.pack(fill=tk.X, pady=(4, 8))

    proc_ref: Dict[str, Optional[subprocess.Popen]] = {"proc": None}
    last_video_ref: Dict[str, Optional[Path]] = {"path": None}
    log_queue: "queue.Queue[str]" = queue.Queue()

    def collect_config() -> Dict[str, object]:
        v_code = next((k for k, lbl in VOICE_OPTIONS if lbl == voice_var.get()), "vanthanhthu")
        a_code = next((k for k, lbl in ASPECT_OPTIONS if lbl == aspect_var.get()), "9:16")
        s_code = next((k for k, lbl in SUB_OPTIONS if lbl == sub_var.get()), "none")
        try:
            dur_val = max(0.5, min(30.0, float(dur_var.get().strip())))
        except ValueError:
            dur_val = 3.0
        return {
            "topic": topic_text.get("1.0", tk.END).strip(),
            "duration_mins": dur_val,
            "voice": v_code,
            "aspect": a_code,
            "sub_style": s_code,
            "footage": footage_var.get().strip(),
            "script_file": script_var.get().strip(),
        }

    def save_all() -> Dict[str, object]:
        save_env_keys({
            "GEMINI_API_KEY": gemini_var.get().strip(),
            "PEXELS_API_KEY": pexels_var.get().strip(),
        })
        cfg = collect_config()
        save_app_config(cfg)
        return cfg

    def append_log(msg: str) -> None:
        log_box.configure(state=tk.NORMAL)
        log_box.insert(tk.END, msg)
        log_box.see(tk.END)
        log_box.configure(state=tk.DISABLED)

    def poll_logs() -> None:
        while not log_queue.empty():
            append_log(log_queue.get_nowait())
        root.after(120, poll_logs)

    def start_render() -> None:
        if proc_ref["proc"] is not None:
            return
        if not gemini_var.get().strip():
            messagebox.showwarning("Thiếu API Key", "Vui lòng nhập Gemini API Key trước khi tạo video!")
            return
        cfg = save_all()
        if not cfg["topic"] and not cfg["script_file"]:
            messagebox.showwarning("Thiếu nội dung", "Vui lòng nhập Chủ đề / Prompt hoặc chọn file kịch bản JSON!")
            return

        cmd = build_cli_command(cfg)
        log_box.configure(state=tk.NORMAL)
        log_box.delete("1.0", tk.END)
        log_box.configure(state=tk.DISABLED)
        append_log("🚀 Đang khởi chạy quy trình tạo video...\n")
        append_log(f"📌 Chủ đề: {cfg['topic']}\n\n")

        run_btn.configure(state=tk.DISABLED)
        stop_btn.configure(state=tk.NORMAL)
        play_btn.configure(state=tk.DISABLED)
        last_video_ref["path"] = None

        def worker() -> None:
            env = os.environ.copy()
            env["PYTHONPATH"] = f"{BASE_DIR}{os.pathsep}{env.get('PYTHONPATH', '')}"
            env["PYTHONIOENCODING"] = "utf-8"
            env["GEMINI_API_KEY"] = gemini_var.get().strip()
            if pexels_var.get().strip():
                env["PEXELS_API_KEY"] = pexels_var.get().strip()
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(BASE_DIR),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                )
                proc_ref["proc"] = proc
                assert proc.stdout is not None
                for line in proc.stdout:
                    log_queue.put(line)
                    m_vid = re.search(r"(?:Video thành phẩm\s*:|MASTER VIDEO ĐÃ HOÀN TẤT\s*:)\s*(.+?\.mp4)", line)
                    if m_vid:
                        cand = Path(m_vid.group(1).strip())
                        if cand.exists():
                            last_video_ref["path"] = cand
                code = proc.wait()
                if code == 0:
                    log_queue.put("\n✅ HOÀN TẤT! Bạn có thể bấm '▶ Mở Video Vừa Tạo' hoặc '📂 Mở thư mục Video'.\n")
                else:
                    log_queue.put(f"\n⚠️ Tiến trình dừng với mã lỗi: {code}\n")
            except Exception as exc:
                log_queue.put(f"\n❌ Lỗi khởi chạy: {exc}\n")
            finally:
                proc_ref["proc"] = None
                has_vid = last_video_ref["path"] is not None and last_video_ref["path"].exists()
                root.after(
                    0,
                    lambda: (
                        run_btn.configure(state=tk.NORMAL),
                        stop_btn.configure(state=tk.DISABLED),
                        play_btn.configure(state=tk.NORMAL if has_vid else tk.DISABLED),
                    ),
                )

        threading.Thread(target=worker, daemon=True).start()

    def stop_render() -> None:
        proc = proc_ref.get("proc")
        if proc is not None:
            proc.terminate()
            append_log("\n⏹ Đã gửi lệnh dừng tiến trình.\n")

    run_btn = ttk.Button(btn_frame, text="🎬 TẠO VIDEO NGAY", command=start_render)
    run_btn.pack(side=tk.LEFT, padx=(0, 8))

    stop_btn = ttk.Button(btn_frame, text="⏹ Dừng", command=stop_render, state=tk.DISABLED)
    stop_btn.pack(side=tk.LEFT, padx=(0, 8))

    ttk.Button(btn_frame, text="💾 Lưu cấu hình", command=lambda: (save_all(), append_log("💾 Đã lưu API Key & cấu hình.\n"))).pack(
        side=tk.LEFT, padx=(0, 8)
    )
    def open_latest_video() -> None:
        vid = last_video_ref.get("path")
        if vid and vid.exists():
            open_folder(vid)

    play_btn = ttk.Button(btn_frame, text="▶ Mở Video Vừa Tạo", command=open_latest_video, state=tk.DISABLED)
    play_btn.pack(side=tk.RIGHT, padx=(8, 0))
    ttk.Button(btn_frame, text="📂 Mở thư mục Video", command=lambda: open_folder(WORKSPACE_DIR)).pack(side=tk.RIGHT)

    # 5. Log Output Frame
    log_frame = ttk.LabelFrame(main_frame, text="4. Nhật ký tiến trình trực tiếp", padding=8)
    log_frame.pack(fill=tk.BOTH, expand=True)

    log_box = scrolledtext.ScrolledText(log_frame, height=12, state=tk.DISABLED, font=("Consolas", 9))
    log_box.pack(fill=tk.BOTH, expand=True)

    root.after(120, poll_logs)
    root.mainloop()


def run_terminal_wizard() -> None:
    """Chế độ dự phòng trên Terminal khi hệ thống không có Tkinter (ví dụ Linux tối giản)."""
    print("=" * 72)
    print("🎬 wav2video — TRÌNH CẤU HÌNH NHANH (KHÔNG CẦN CODE)")
    print("=" * 72)

    env_data = load_env_dict()
    cfg = load_app_config()

    cur_key = env_data.get("GEMINI_API_KEY", "")
    if cur_key == "YOUR_GEMINI_API_KEY_HERE":
        cur_key = ""
    masked = f"{cur_key[:6]}...{cur_key[-4:]}" if len(cur_key) > 10 else "(chưa có)"
    new_key = input(f"1. Nhập Gemini API Key [{masked}] (Enter để giữ nguyên): ").strip()
    if new_key:
        save_env_keys({"GEMINI_API_KEY": new_key})
    elif not cur_key:
        print("⚠️ Chưa có GEMINI_API_KEY. Vui lòng nhập API Key hợp lệ trước khi chạy.")
        return

    new_topic = input(f"2. Nhập chủ đề / Prompt [{cfg['topic']}]: ").strip()
    if new_topic:
        cfg["topic"] = new_topic

    new_dur = input(f"3. Thời lượng phút [{cfg['duration_mins']}]: ").strip()
    if new_dur:
        try:
            cfg["duration_mins"] = float(new_dur)
        except ValueError:
            pass

    print("4. Chọn giọng đọc: vanthanhthu | review_phim | gen_z | giat_gan | nam_review | clone")
    new_voice = input(f"   Giọng đọc [{cfg['voice']}]: ").strip()
    if new_voice:
        cfg["voice"] = new_voice

    save_app_config(cfg)
    cmd = build_cli_command(cfg)
    print("\n🚀 Đang chạy lệnh tạo video...\n")
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{BASE_DIR}{os.pathsep}{env.get('PYTHONPATH', '')}"
    subprocess.run(cmd, cwd=str(BASE_DIR), env=env)


if __name__ == "__main__":
    try:
        import tkinter  # noqa: F401
        run_gui_app()
    except Exception:
        run_terminal_wizard()

