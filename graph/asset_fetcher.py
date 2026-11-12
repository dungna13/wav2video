"""
Lấy tư liệu hình ảnh cho TỪNG CẢNH (`graph/asset_fetcher.py`).

Thứ tự ưu tiên cho mỗi cảnh (Tầng 2 — đa ứng viên, chống trùng ID, lọc người & chấm local 0-token):
  1. Video stock thật từ Pexels / Pixabay / Mixkit:
     - Lấy nhiều ứng viên (tối đa `max_candidates`), bỏ qua các ID đã dùng (`used_ids`) ở cảnh trước.
     - Khi ở mode `NO_HUMAN_BROLL`, lọc thô slug/tags dính người và đổi từ khóa đồng nghĩa sang bối cảnh phi nhân vật.
     - Kiểm tra từng ứng viên bằng `VisualFeatureScorer` (trích keyframe `ffmpeg`, phát hiện tối/đứng hình,
       chấm CLIP local 0-token với `image_prompt_en` và phát hiện người nếu bật CLIP).
  2. Ảnh điện ảnh sinh bằng Pollinations (`image_prompt_en` + `style_anchor_en`), có retry/backoff khi 402/429/timeout.
  3. Dự phòng: dùng lại ảnh/video ứng viên khả dĩ nhất hoặc cảnh gần nhất, cuối cùng mới tới `assets/default_scenes`.
"""

from __future__ import annotations

import io
import re
import socket
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import requests
from PIL import Image

from config.settings import (
    MIN_CLIP_PROMPT_SCORE,
    PEXELS_API_KEY,
    PIXABAY_API_KEY,
    POLLINATIONS_MODEL,
)
from graph.visual_scorer import VisualFeatureScorer

NEGATIVE_STYLE = (
    "photorealistic documentary photograph, natural imperfections, subtle film grain, "
    "no text, no watermark, no logo, no cartoon, no illustration, no 3d render"
)
MIN_IMAGE_BYTES = 12000
MIN_VIDEO_BYTES = 50000

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_HUMAN_HINT_RE = re.compile(
    r"\b(man|woman|men|women|person|people|girl|boy|face|portrait|couple|crowd|"
    r"businessman|businesswoman|selfie|family|friends|smiling|talking|child|kid|"
    r"human|actor|actress|model|speaker|presenter)\b",
    re.I,
)


def _online(host: str) -> bool:
    try:
        socket.gethostbyname(host)
        return True
    except Exception:
        return False


def _has_human_hint(text: str) -> bool:
    return bool(_HUMAN_HINT_RE.search((text or "").replace("-", " ").replace("_", " ")))


def _search_pexels_candidates(
    query: str,
    height: int,
    used_ids: Set[str],
    no_human: bool,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    if not PEXELS_API_KEY or not query:
        return []
    out: List[Dict[str, Any]] = []
    try:
        r = requests.get(
            "https://api.pexels.com/videos/search",
            params={"query": query, "orientation": "portrait", "size": "medium", "per_page": 10},
            headers={"Authorization": PEXELS_API_KEY},
            timeout=20,
        )
        if r.status_code != 200:
            return []
        for video in r.json().get("videos", []):
            vid_id = f"pexels:{video.get('id')}"
            if vid_id in used_ids or video.get("duration", 0) < 3:
                continue
            slug = str(video.get("url") or "")
            if no_human and _has_human_hint(slug):
                continue
            files = [
                f
                for f in video.get("video_files", [])
                if f.get("file_type") == "video/mp4" and f.get("height", 0) >= f.get("width", 0)
            ]
            files = [f for f in files if 720 <= f.get("height", 0) <= 1920] or files
            if not files:
                continue
            best = sorted(files, key=lambda f: abs(f.get("height", 0) - height))[0]
            out.append({"provider": "pexels_video", "asset_id": vid_id, "url": best["link"], "label": slug})
            if len(out) >= limit:
                break
    except Exception as e:
        print(f"   [Pexels] {query!r}: {e}")
    return out


def _search_pixabay_candidates(
    query: str,
    used_ids: Set[str],
    no_human: bool,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Pixabay không lọc được khổ dọc: lấy nhiều ứng viên hợp lệ rồi renderer crop giữa về 9:16."""
    if not PIXABAY_API_KEY or not query:
        return []
    out: List[Dict[str, Any]] = []
    try:
        r = requests.get(
            "https://pixabay.com/api/videos/",
            params={"key": PIXABAY_API_KEY, "q": query, "per_page": 10, "safesearch": "true"},
            timeout=20,
        )
        if r.status_code != 200:
            print(f"   [Pixabay] HTTP {r.status_code}")
            return []
        for hit in r.json().get("hits", []):
            vid_id = f"pixabay:{hit.get('id')}"
            if vid_id in used_ids or hit.get("duration", 0) < 3:
                continue
            tags = str(hit.get("tags") or "")
            if no_human and _has_human_hint(tags):
                continue
            for quality in ("medium", "large", "small"):
                info = hit.get("videos", {}).get(quality) or {}
                url = info.get("url")
                if url:
                    out.append({"provider": "pixabay_video", "asset_id": vid_id, "url": url, "label": tags})
                    break
            if len(out) >= limit:
                break
    except Exception as e:
        print(f"   [Pixabay] {query!r}: {e}")
    return out


def _mixkit_terms(query: str, no_human: bool) -> List[str]:
    words = [w.lower() for w in re.findall(r"\b\w+\b", query) if len(w) > 2]
    synonyms = {
        "battlefield": "fire",
        "battle": "fire",
        "war": "fire",
        "artillery": "cannon",
        "gun": "smoke",
        "mud": "rain",
        "storm": "rain",
        "trench": "dark",
        "victory": "flag",
        "soldiers": "flag" if no_human else "people",
        "soldier": "helmet" if no_human else "man",
        "military": "smoke" if no_human else "crowd",
        "climbing": "mountain",
        "attack": "explosion",
        "history": "book",
        "ancient": "temple",
        "science": "technology",
        "nature": "forest",
    }
    terms: List[str] = []
    for w in words:
        if w not in terms:
            terms.append(w)
        syn = synonyms.get(w)
        if syn and syn not in terms:
            terms.append(syn)
    return terms


def _search_mixkit_candidates(
    query: str,
    used_ids: Set[str],
    no_human: bool,
    limit: int = 6,
) -> List[Dict[str, Any]]:
    """Thu thập nhiều ứng viên video stock 720p từ Mixkit (miễn phí, không cần API key)."""
    if not query:
        return []
    headers = {"User-Agent": _USER_AGENT}
    out: List[Dict[str, Any]] = []
    seen_here: Set[str] = set()

    for term in _mixkit_terms(query, no_human=no_human):
        url = f"https://mixkit.co/free-stock-video/{term}/"
        try:
            r = requests.get(url, headers=headers, timeout=6)
            if r.status_code != 200:
                continue
            html = r.text
            mp4_ids = re.findall(r"https://assets\.mixkit\.co/videos/(\d+)/\1-(?:1080|720)\.mp4", html)
            for raw_id in mp4_ids:
                asset_id = f"mixkit:{raw_id}"
                if asset_id in used_ids or asset_id in seen_here:
                    continue
                seen_here.add(asset_id)
                slug_m = re.search(rf"(?:free-stock-video/|mixkit-)([a-z0-9-]+?)-{raw_id}\b", html, re.I)
                label = slug_m.group(1) if slug_m else term
                if no_human and _has_human_hint(label):
                    continue
                out.append(
                    {
                        "provider": "mixkit_video",
                        "asset_id": asset_id,
                        "url": f"https://assets.mixkit.co/videos/{raw_id}/{raw_id}-720.mp4",
                        "label": label,
                    }
                )
                if len(out) >= limit:
                    return out
        except Exception:
            continue
    return out


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


def _download_video(url: str, dest: Path) -> bool:
    try:
        resp = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=45)
        if resp.status_code == 200 and len(resp.content) > MIN_VIDEO_BYTES:
            dest.write_bytes(resp.content)
            return True
    except Exception:
        pass
    return False


def _collect_stock_candidates(
    query: str,
    width: int,
    height: int,
    used_ids: Set[str],
    no_human: bool,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    del width  # giữ chữ ký rõ ràng cho Pexels/Pixabay
    cands: List[Dict[str, Any]] = []
    if PEXELS_API_KEY:
        cands.extend(_search_pexels_candidates(query, height, used_ids, no_human, limit=limit))
    if PIXABAY_API_KEY and len(cands) < limit:
        cands.extend(_search_pixabay_candidates(query, used_ids, no_human, limit=limit - len(cands)))
    if len(cands) < limit:
        cands.extend(_search_mixkit_candidates(query, used_ids, no_human, limit=limit - len(cands)))
    return cands[:limit]


def _candidate_rank(ev: Dict[str, Any], no_human: bool) -> float:
    clip = ev.get("clip_prompt_score")
    base = float(clip) if clip is not None else 0.25
    sharp = float(ev.get("sharpness_score") or 0.0)
    penalty = 0.30 if (no_human and ev.get("human_detected")) else 0.0
    return base + 0.15 * sharp - penalty


def _select_best_stock_video(
    scene_idx: int,
    sc: Dict[str, Any],
    vid_path: Path,
    run_dir: Path,
    width: int,
    height: int,
    used_ids: Set[str],
    bad_ids: Set[str],
    scorer: VisualFeatureScorer,
    intent_mode: str,
    max_candidates: int,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], int]:
    """
    Thử tối đa `max_candidates` video stock chưa trùng ID, chấm keyframe local 0-token.
    Trả về `(accepted_cand, backup_usable_cand_info, tried_count)`.
    """
    no_human = intent_mode == "NO_HUMAN_BROLL"
    query = sc.get("stock_query_en", "")
    prompt_en = sc.get("image_prompt_en", "")
    cands = _collect_stock_candidates(query, width, height, used_ids | bad_ids, no_human=no_human, limit=max(max_candidates, 4))

    best_backup: Optional[Dict[str, Any]] = None
    best_backup_path: Optional[Path] = None
    tried = 0

    try:
        for k, cand in enumerate(cands[:max_candidates], 1):
            tmp_path = run_dir / f".cand_s{scene_idx + 1}_{k}.mp4"
            if not _download_video(cand["url"], tmp_path):
                tmp_path.unlink(missing_ok=True)
                continue
            tried += 1
            ev = scorer.inspect_media(tmp_path, media_type="video", prompt_en=prompt_en, intent_mode=intent_mode)

            if ev["is_corrupt"] or ev["is_dark"] or ev["is_static"]:
                bad_ids.add(cand["asset_id"])
                tmp_path.unlink(missing_ok=True)
                continue
            if no_human and ev.get("human_detected") is True:
                bad_ids.add(cand["asset_id"])
                tmp_path.unlink(missing_ok=True)
                continue

            clip_ok = ev["clip_prompt_score"] is None or float(ev["clip_prompt_score"]) >= MIN_CLIP_PROMPT_SCORE
            if not ev["reject_reasons"] and clip_ok:
                tmp_path.replace(vid_path)
                used_ids.add(cand["asset_id"])
                return {**cand, "eval": ev}, None, tried

            rank = _candidate_rank(ev, no_human=no_human)
            if best_backup is None or rank > best_backup["rank"]:
                if best_backup_path is not None:
                    best_backup_path.unlink(missing_ok=True)
                best_backup = {**cand, "eval": ev, "rank": rank}
                best_backup_path = tmp_path
            else:
                tmp_path.unlink(missing_ok=True)

        if best_backup is not None and best_backup_path is not None:
            backup_save = run_dir / f".backup_s{scene_idx + 1}.mp4"
            best_backup_path.replace(backup_save)
            best_backup["temp_path"] = backup_save
            return None, best_backup, tried
        return None, None, tried
    finally:
        for leftover in run_dir.glob(f".cand_s{scene_idx + 1}_*.mp4"):
            leftover.unlink(missing_ok=True)


def fetch_scene_assets(
    scenes: List[Dict[str, Any]],
    style_anchor_en: str,
    run_dir: Path,
    seed: int,
    width: int,
    height: int,
    intent_mode: str = "NO_HUMAN_BROLL",
    scorer: Optional[VisualFeatureScorer] = None,
    max_candidates: int = 3,
) -> Dict[str, Any]:
    """Gắn `media_path` + `media_type` ('video'|'image') + `media_source` vào từng scene (sửa tại chỗ)."""
    default_dir = Path(__file__).resolve().parent.parent / "assets" / "default_scenes"
    defaults = [p for p in sorted(default_dir.glob("default_scene_*.jpg")) if p.stat().st_size > 5000]
    online_img = _online("image.pollinations.ai")
    local_scorer = scorer or VisualFeatureScorer()

    used_ids: Set[str] = set()
    bad_ids: Set[str] = set()
    last_good: Optional[Path] = None
    sources: List[str] = []
    candidates_tried_total = 0

    for i, sc in enumerate(scenes):
        img_path = run_dir / f"scene_{i + 1}.jpg"
        vid_path = run_dir / f"scene_{i + 1}.mp4"
        source = ""

        if vid_path.exists() and vid_path.stat().st_size > MIN_VIDEO_BYTES:
            sc.update(media_path=str(vid_path), media_type="video")
            source = "stock_video(cache)"
        elif img_path.exists() and img_path.stat().st_size > MIN_IMAGE_BYTES:
            sc.update(media_path=str(img_path), media_type="image")
            last_good = img_path
            source = "ai_image(cache)"
        else:
            accepted, backup, tried = _select_best_stock_video(
                scene_idx=i,
                sc=sc,
                vid_path=vid_path,
                run_dir=run_dir,
                width=width,
                height=height,
                used_ids=used_ids,
                bad_ids=bad_ids,
                scorer=local_scorer,
                intent_mode=intent_mode,
                max_candidates=max_candidates,
            )
            candidates_tried_total += tried
            if accepted is not None:
                sc.update(
                    media_path=str(vid_path),
                    media_type="video",
                    asset_id=accepted["asset_id"],
                    candidates_tried=tried,
                )
                source = accepted["provider"]
            else:
                if online_img:
                    prompt = f"{sc['image_prompt_en']}. {style_anchor_en}. {NEGATIVE_STYLE}"
                    if _fetch_pollinations_image(prompt, img_path, seed + i * 17, width, height):
                        sc.update(media_path=str(img_path), media_type="image", candidates_tried=tried)
                        last_good = img_path
                        source = "ai_image"
                    time.sleep(1.2)
                if not source and backup is not None:
                    Path(backup["temp_path"]).replace(vid_path)
                    used_ids.add(backup["asset_id"])
                    sc.update(
                        media_path=str(vid_path),
                        media_type="video",
                        asset_id=backup["asset_id"],
                        candidates_tried=tried,
                    )
                    source = f"{backup['provider']}(best_cand)"
                elif backup is not None and Path(backup["temp_path"]).exists():
                    Path(backup["temp_path"]).unlink(missing_ok=True)

        if not source:
            fallback = last_good or (defaults[i % len(defaults)] if defaults else None)
            if fallback is None:
                raise RuntimeError(f"Không lấy được hình cho cảnh {i + 1} và không có ảnh dự phòng trong assets/default_scenes.")
            sc.update(media_path=str(fallback), media_type="image")
            source = "FALLBACK_reuse_previous" if last_good else "FALLBACK_default_scene"
        sc["media_source"] = source
        sources.append(source)
        print(f"   ├─ Cảnh {i + 1}/{len(scenes)}: {source} (id={sc.get('asset_id', '-')}, thử={sc.get('candidates_tried', 0)})")

    n_fallback = sum(1 for s in sources if s.startswith("FALLBACK"))
    return {
        "sources": sources,
        "fallback_scenes": n_fallback,
        "real_scenes": len(sources) - n_fallback,
        "unique_stock_assets": len(used_ids),
        "candidates_tried_total": candidates_tried_total,
        "stock_enabled": True,
    }
