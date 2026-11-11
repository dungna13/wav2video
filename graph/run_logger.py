"""
Auto File Logging & Diagnostics (`graph/run_logger.py`).

Tự động ghi toàn bộ stdout/stderr + traceback từng phiên chạy vào:
  - `workspace/logs/run_YYYYMMDD_HHMMSS.log`
  - `workspace/logs/latest.log` (luôn phản ánh phiên chạy gần nhất, flush ngay theo từng dòng)

Cung cấp hàm `--logs` để kiểm tra nhanh các lỗi và checkpoint gần nhất trong SQLite.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import Callable, Optional, TextIO, Tuple

from config.settings import CHECKPOINT_DB_PATH, WORKSPACE_DIR

LOG_DIR: Path = WORKSPACE_DIR / "logs"
LATEST_LOG_PATH: Path = LOG_DIR / "latest.log"


class _TeeStream:
    """Ghi đồng thời ra terminal và nhiều file log, flush tức thì để không mất log khi crash."""

    def __init__(self, orig: TextIO, *files: TextIO) -> None:
        self._orig = orig
        self._files = files

    def write(self, data: str) -> int:
        self._orig.write(data)
        self._orig.flush()
        for f in self._files:
            try:
                f.write(data)
                f.flush()
            except Exception:
                pass
        return len(data)

    def flush(self) -> None:
        self._orig.flush()
        for f in self._files:
            try:
                f.flush()
            except Exception:
                pass

    def isatty(self) -> bool:
        return hasattr(self._orig, "isatty") and self._orig.isatty()


def start_run_log(label: str = "run") -> Tuple[Path, Callable[[], None]]:
    """Bắt đầu ghi log phiên chạy hiện tại ra file `.log`; trả về `(log_path, stop_fn)`."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    safe_label = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in label)[:32].strip("_") or "run"
    log_path = LOG_DIR / f"run_{ts}_{safe_label}.log"

    run_file = open(log_path, "w", encoding="utf-8", buffering=1)
    latest_file = open(LATEST_LOG_PATH, "w", encoding="utf-8", buffering=1)

    orig_out, orig_err = sys.stdout, sys.stderr
    sys.stdout = _TeeStream(orig_out, run_file, latest_file)  # type: ignore[assignment]
    sys.stderr = _TeeStream(orig_err, run_file, latest_file)  # type: ignore[assignment]

    print(f"[Log] Đang ghi log phiên chạy tại: {log_path}")

    def stop() -> None:
        sys.stdout = orig_out
        sys.stderr = orig_err
        for f in (run_file, latest_file):
            try:
                f.flush()
                f.close()
            except Exception:
                pass

    return log_path, stop


def print_diagnostics(checkpoint_db: Path = CHECKPOINT_DB_PATH, limit: int = 5) -> None:
    """In nhanh các checkpoint, error_logs trong SQLite và phần đuôi `latest.log`."""
    print("=" * 96)
    print("KIỂM TRA CHECKPOINT & ERROR LOGS")
    print("=" * 96)

    if checkpoint_db.exists():
        conn = sqlite3.connect(str(checkpoint_db))
        conn.row_factory = sqlite3.Row
        try:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            if "checkpoints" in tables:
                rows = conn.execute(
                    "SELECT thread_id, state_json, updated_at FROM checkpoints ORDER BY updated_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
                print(f"• Checkpoints gần nhất ({len(rows)} phiên) trong {checkpoint_db.name}:")
                for r in rows:
                    try:
                        st = json.loads(r["state_json"] or "{}")
                    except Exception:
                        st = {}
                    status = st.get("run_status") or st.get("tiktok_publish_status") or "unknown"
                    last_node = st.get("last_completed_node") or "-"
                    topic = str(st.get("topic_title") or st.get("user_request") or "")[:48]
                    errs = len(st.get("error_logs") or [])
                    print(
                        f"  [{r['updated_at']}] {r['thread_id']} | status={status} | last_node={last_node} "
                        f"| errors={errs} | topic='{topic}'"
                    )

            if "error_logs" in tables:
                err_rows = conn.execute(
                    "SELECT id, thread_id, node_name, error_type, message, traceback, created_at "
                    "FROM error_logs ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
                print(f"\n• Error Logs SQLite ({len(err_rows)} lỗi gần nhất):")
                if not err_rows:
                    print("  (Không có lỗi nào được ghi nhận trong bảng error_logs.)")
                for er in err_rows:
                    print(
                        f"  #{er['id']} [{er['created_at']}] {er['thread_id']} @ {er['node_name']} -> "
                        f"{er['error_type']}: {er['message']}"
                    )
                    if er["traceback"]:
                        tail_tb = "\n    ".join(str(er["traceback"]).strip().splitlines()[-4:])
                        print(f"    {tail_tb}")
        finally:
            conn.close()
    else:
        print(f"• Chưa có file checkpoint SQLite tại {checkpoint_db}")

    print("\n• Log file gần nhất:")
    if LATEST_LOG_PATH.exists():
        lines = LATEST_LOG_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()
        print(f"  File: {LATEST_LOG_PATH} ({len(lines)} dòng) — 25 dòng cuối:")
        for ln in lines[-25:]:
            print(f"  | {ln}")
    else:
        print(f"  (Chưa có log trong {LOG_DIR})")
    print("=" * 96)

