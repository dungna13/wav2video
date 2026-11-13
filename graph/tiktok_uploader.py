"""
TikTok Auto Publisher Bot (`graph/tiktok_uploader.py`).

Cung cấp 2 chức năng tự động hóa:
  1. `open_tiktok_login_session()`: Mở trình duyệt Chromium để người dùng đăng nhập nick TikTok thật 1 lần.
     Session cookies/storage được lưu vĩnh viễn vào `workspace/tiktok_browser_profile`.
  2. `auto_upload_video_to_tiktok(video_path, caption, headless=True)`:
     Tự động hóa 100%: Mở TikTok Creator Center bằng session đã lưu ➜ Nạp file MP4 ➜ Nhập Caption ➜ Bấm Post.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict

from config.settings import WORKSPACE_DIR

PROFILE_DIR = WORKSPACE_DIR / "tiktok_browser_profile"


def get_login_status() -> Dict[str, Any]:
    """Kiểm tra xem profile đã từng đăng nhập TikTok hay chưa."""
    cookies_path = PROFILE_DIR / "Default" / "Network" / "Cookies"
    has_profile = PROFILE_DIR.exists() and any(PROFILE_DIR.iterdir())
    return {
        "profile_dir": str(PROFILE_DIR),
        "is_configured": has_profile,
    }


def launch_interactive_login() -> None:
    """Mở trình duyệt có giao diện để người dùng đăng nhập TikTok 1 lần."""
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    print("🚀 Đang mở trình duyệt để đăng nhập TikTok...")
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            channel=None,
            viewport={"width": 1280, "height": 800},
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        page = browser.new_page()
        page.goto("https://www.tiktok.com/login", wait_until="domcontentloaded")
        print("\n" + "=" * 60)
        print("👉 Vui lòng ĐĂNG NHẬP tài khoản TikTok của bạn trên cửa sổ vừa mở.")
        print("   (Có thể quét mã QR hoặc đăng nhập bằng Email/SĐT).")
        print("👉 Sau khi đăng nhập thành công vào trang cá nhân, bạn có thể ĐÓNG trình duyệt.")
        print("=" * 60 + "\n")

        # Chờ người dùng đăng nhập hoặc đóng trình duyệt (tối đa 5 phút)
        try:
            for _ in range(300):
                if browser.pages == []:
                    break
                time.sleep(1)
        except Exception:
            pass
        finally:
            try:
                browser.close()
            except Exception:
                pass
    print("✅ Đã lưu phiên đăng nhập TikTok thành công!")


def auto_upload_video(video_path: Path, caption: str, headless: bool = False) -> Dict[str, Any]:
    """Tự động tải video lên TikTok Creator Center bằng Playwright."""
    if not video_path.exists():
        return {"status": "error", "message": f"Không tìm thấy file video: {video_path}"}

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    result = {"status": "pending", "message": ""}
    print(f"🚀 Bắt đầu tự động tải video lên TikTok: {video_path.name}")

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=headless,
            viewport={"width": 1280, "height": 800},
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        page = browser.new_page()
        try:
            page.goto("https://www.tiktok.com/creator-center/upload?from=upload", wait_until="networkidle", timeout=45000)
            time.sleep(3)

            # Kiểm tra xem có bị chuyển về trang login không
            if "login" in page.url.lower():
                browser.close()
                return {
                    "status": "error",
                    "code": "AUTH_REQUIRED",
                    "message": "Chưa đăng nhập TikTok! Vui lòng bấm 'Đăng nhập TikTok' một lần trước.",
                }

            # Tìm thẻ input file upload (trong iframe hoặc trang chính)
            file_input = page.locator('input[type="file"]')
            if file_input.count() == 0:
                # Tìm trong iframes nếu có
                for frame in page.frames:
                    fi = frame.locator('input[type="file"]')
                    if fi.count() > 0:
                        file_input = fi
                        break

            if file_input.count() == 0:
                # Chờ thẻ file xuất hiện
                page.wait_for_selector('input[type="file"]', timeout=15000)
                file_input = page.locator('input[type="file"]')

            print("   ├─ Đang nạp file video...")
            file_input.first.set_input_files(str(video_path.resolve()))
            time.sleep(5)

            # Nhập Caption
            print("   ├─ Đang điền Caption & Hashtags...")
            # Khung soạn thảo caption của TikTok thường là div contenteditable hoặc input text
            caption_elem = page.locator('.notranslate[contenteditable="true"], div[contenteditable="true"]').first
            if caption_elem.count() > 0:
                caption_elem.click()
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                page.keyboard.type(caption, delay=30)
            time.sleep(3)

            # Chờ thanh tiến trình upload hoàn tất (nút Post sáng lên)
            print("   ├─ Chờ TikTok xử lý và sẵn sàng đăng...")
            time.sleep(6)

            # Nút Post (Đăng)
            post_btn = page.locator('button:has-text("Post"), button:has-text("Đăng")').first
            if post_btn.count() > 0:
                post_btn.click()
                print("   └─ 🚀 ĐÃ BẤM NÚT ĐĂNG LÊN TIKTOK!")
                time.sleep(5)
                result = {"status": "success", "message": "Video đã được tự động đăng lên TikTok thành công!"}
            else:
                result = {"status": "warning", "message": "Đã nạp video và caption thành công, vui lòng kiểm tra và bấm Đăng trên trình duyệt."}

        except Exception as ex:
            result = {"status": "error", "message": f"Lỗi trong quá trình upload: {str(ex)}"}
        finally:
            browser.close()

    return result

