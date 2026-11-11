"""
Lấy tư liệu hình ảnh cho TỪNG CẢNH (`graph/asset_fetcher.py`).

Thứ tự ưu tiên cho mỗi cảnh:
  1. (tuỳ chọn) Video stock thật từ Pexels (`PEXELS_API_KEY`) hoặc Pixabay (`PIXABAY_API_KEY`) — dùng `stock_query_en`, ưu tiên khổ dọc.
  2. Ảnh điện ảnh sinh bằng Pollinations (`image_prompt_en` + `style_anchor_en` chung cho cả phim), có retry/backoff khi 402/429/timeout.
  3. Dự phòng: dùng lại ảnh đã sinh thành công của cảnh gần nhất (cùng phong cách), cuối cùng mới tới ảnh mặc định trong `assets/default_scenes`.

Trả về `asset_report` ghi rõ nguồn từng cảnh để người dùng biết cảnh nào là ảnh thật sinh theo lời, cảnh nào là dự phòng.
"""

import io
import socket
import time
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List

import requests
from PIL import Image

from config.settings import POLLINATIONS_MODEL, PEXELS_API_KEY, PIXABAY_API_KEY

NEGATIVE_STYLE = (
    "photorealistic documentary photograph, natural imperfections, subtle film grain, "
    "no text, no watermark, no logo, no cartoon, no illustration, no 3d render"
)
MIN_IMAGE_BYTES = 12000


def _online(host: str) -> bool:
    try:
        socket.gethostbyname(host)
        return True
    except Exception:
        return False


def _fetch_pexels_video(query: str, dest: Path, width: int, height: int) -> bool:
    if not PEXELS_API_KEY or not query:
        return False
    try:
        r = requests.get(
            "https://api.pexels.com/videos/search",
            params={"query": query, "orientation": "portrait", "size": "medium", "per_page": 5},
            headers={"Authorization": PEXELS_API_KEY},
            timeout=20,
        )
        if r.status_code != 200:
            return False
        for video in r.json().get("videos", []):
            if video.get("duration", 0) < 3:
                continue
            files = [f for f in video.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("height", 0) >= f.get("width", 0)]
            files = [f for f in files if 720 <= f.get("height", 0) <= 1920] or files
            if not files:
                continue
            best = sorted(files, key=lambda f: abs(f.get("height", 0) - height))[0]
            data = requests.get(best["link"], timeout=60)
            if data.status_code == 200 and len(data.content) > 50000:
                dest.write_bytes(data.content)
                return True
    except Exception as e:
        print(f"   [Pexels] {query!r}: {e}")
    return False


def _fetch_mixkit_video(query: str, dest: Path) -> bool:
    """Tự động tìm và tải clip video stock HD (720p) từ Mixkit (100% miễn phí, không cần API key)."""
    if not query:
        return False
    import re
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    words = [w.lower() for w in re.findall(r"\b\w+\b", query) if len(w) > 2]
    synonyms = {
        "battlefield": "fire", "battle": "fire", "war": "fire", "artillery": "cannon", "gun": "smoke",
        "mud": "rain", "storm": "rain", "trench": "dark", "victory": "flag", "soldiers": "people",
        "soldier": "man", "military": "crowd", "climbing": "mountain", "attack": "explosion",
        "history": "book", "ancient": "temple", "science": "technology", "nature": "forest"
    }
    search_terms = []
    for w in words:
        search_terms.append(w)
        if w in synonyms:
            search_terms.append(synonyms[w])

    for term in search_terms:
        url = f"https://mixkit.co/free-stock-video/{term}/"
        try:
            r = requests.get(url, headers=headers, timeout=6)
            if r.status_code == 200:
                mp4s = re.findall(r"https://assets\.mixkit\.co/videos/(\d+)/\1-1080\.mp4", r.text)
                if mp4s:
                    vid_id = mp4s[0]
                    vid_url = f"https://assets.mixkit.co/videos/{vid_id}/{vid_id}-720.mp4"
                    down = requests.get(vid_url, headers=headers, timeout=40)
                    if down.status_code == 200 and len(down.content) > 50000:
                        dest.write_bytes(down.content)
                        return True
        except Exception as e:
            continue
    return False


def _fetch_pixabay_video(query: str, dest: Path, width: int, height: int) -> bool:
    """Pixabay không lọc được khổ dọc: tải clip ngang rồi renderer crop giữa về 9:16."""
    if not PIXABAY_API_KEY or not query:
        return False
    try:
        r = requests.get(
            "https://pixabay.com/api/videos/",
            params={"key": PIXABAY_API_KEY, "q": query, "per_page": 5, "safesearch": "true"},
            timeout=20,
        )
        if r.status_code != 200:
            print(f"   [Pixabay] HTTP {r.status_code}")
            return False
        for hit in r.json().get("hits", []):
            if hit.get("duration", 0) < 3:
                continue
            for quality in ("medium", "large", "small"):
                info = hit.get("videos", {}).get(quality) or {}
                url = info.get("url")
                if not url:
                    continue
                data = requests.get(url, timeout=90)
                if data.status_code == 200 and len(data.content) > 50000:
                    dest.write_bytes(data.content)
                    return True
                break
    except Exception as e:
        print(f"   [Pixabay] {query!r}: {e}")
    return False


def _fetch_pollinations_image(prompt: str, dest: Path, seed: int, width: int, height: int, attempts: int = 3) -> bool:
    url = (
        f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}"
        f"?model={POLLINATIONS_MODEL}&width={width}&height={height}&seed={seed}&nologo=true"
    )
    for attempt in range(1, attempts + 1):
        try:
            resp = requests.get(url, timeout=60)
            ctype = resp.headers.get("content-type", "")
            if resp.status_code == 200 and "image" in ctype and len(resp.content) > MIN_IMAGE_BYTES:
                Image.open(io.BytesIO(resp.content)).convert("RGB").save(str(dest), quality=95)
                return True
            wait = 12 if resp.status_code in (402, 429) else 4
            print(f"   [Pollinations] HTTP {resp.status_code} (lần {attempt}/{attempts}) -> chờ {wait}s")
        except Exception as e:
            wait = 4
            print(f"   [Pollinations] {type(e).__name__} (lần {attempt}/{attempts}) -> chờ {wait}s")
        time.sleep(wait)
    return False


def fetch_scene_assets(
    scenes: List[Dict[str, Any]],
    style_anchor_en: str,
    run_dir: Path,
    seed: int,
    width: int,
    height: int,
) -> Dict[str, Any]:
    """Gắn `media_path` + `media_type` ('video'|'image') + `media_source` vào từng scene (sửa tại chỗ)."""
    default_dir = Path(__file__).resolve().parent.parent / "assets" / "default_scenes"
    defaults = [p for p in sorted(default_dir.glob("default_scene_*.jpg")) if p.stat().st_size > 5000]
    online_img = _online("image.pollinations.ai")
    last_good: Path | None = None
    sources: List[str] = []

    for i, sc in enumerate(scenes):
        img_path = run_dir / f"scene_{i + 1}.jpg"
        vid_path = run_dir / f"scene_{i + 1}.mp4"
        source = ""

        if vid_path.exists() and vid_path.stat().st_size > 50000:
            sc.update(media_path=str(vid_path), media_type="video")
            source = "stock_video(cache)"
        elif img_path.exists() and img_path.stat().st_size > MIN_IMAGE_BYTES:
            sc.update(media_path=str(img_path), media_type="image")
            last_good = img_path
            source = "ai_image(cache)"
        else:
            if _fetch_pexels_video(sc.get("stock_query_en", ""), vid_path, width, height):
                sc.update(media_path=str(vid_path), media_type="video")
                source = "pexels_video"
            elif _fetch_pixabay_video(sc.get("stock_query_en", ""), vid_path, width, height):
                sc.update(media_path=str(vid_path), media_type="video")
                source = "pixabay_video"
            elif _fetch_mixkit_video(sc.get("stock_query_en", ""), vid_path):
                sc.update(media_path=str(vid_path), media_type="video")
                source = "mixkit_video"
            elif online_img:
                prompt = f"{sc['image_prompt_en']}. {style_anchor_en}. {NEGATIVE_STYLE}"
                if _fetch_pollinations_image(prompt, img_path, seed + i * 17, width, height):
                    sc.update(media_path=str(img_path), media_type="image")
                    last_good = img_path
                    source = "ai_image"
                time.sleep(1.2)  # giãn cách để không dính giới hạn tần suất của bản miễn phí

        if not source:
            fallback = last_good or (defaults[i % len(defaults)] if defaults else None)
            if fallback is None:
                raise RuntimeError(f"Không lấy được hình cho cảnh {i + 1} và không có ảnh dự phòng trong assets/default_scenes.")
            sc.update(media_path=str(fallback), media_type="image")
            source = "FALLBACK_reuse_previous" if last_good else "FALLBACK_default_scene"
        sc["media_source"] = source
        sources.append(source)
        print(f"   ├─ Cảnh {i + 1}/{len(scenes)}: {source}")

    n_fallback = sum(1 for s in sources if s.startswith("FALLBACK"))
    return {
        "sources": sources,
        "fallback_scenes": n_fallback,
        "real_scenes": len(sources) - n_fallback,
        "stock_enabled": True,
    }

