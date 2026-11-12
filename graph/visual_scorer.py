"""
Local Visual Feature Scorer (0-token API) cho Tầng 2 (`graph/visual_scorer.py`).

Đánh giá chất lượng thật trên CẢ video stock (.mp4) lẫn ảnh (.jpg/.png):
  1. Trích 2-3 keyframe đại diện từ file video bằng `ffmpeg` (không cần `cv2`).
  2. Đo các chỉ số pixel xác định 100% offline:
     - Độ nét Laplacian (`sharpness_score`)
     - Kiểm tra frame tối đen (`is_dark`)
     - Kiểm tra clip đứng hình / tĩnh (`is_static`, với video >= 2 frames)
     - Vector màu trung bình & histogram RGB (`mean_rgb`, `hist_rgb`) phục vụ tính `continuity_score`.
  3. (Tùy chọn, bật mặc định) Chấm CLIP local 0-token bằng `transformers.CLIPModel`:
     - `clip_prompt_score` ($S_{clip}$): mức độ khớp ngữ nghĩa với `image_prompt_en`
     - `human_detected`: phát hiện khung hình dính người/chân dung khi ở chế độ `NO_HUMAN_BROLL`.
     Nếu model chưa tải sẵn hoặc máy offline, trả về `None` (không bịa số).
"""

from __future__ import annotations

import os
import socket
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

from config.settings import ENABLE_LOCAL_CLIP, LOCAL_CLIP_MODEL

_CLIP_BUNDLE: Optional[Tuple[Any, Any, str]] = None
_CLIP_FAILED_REASON: Optional[str] = None

_HUMAN_PROMPTS = [
    "a close-up photograph of a person, human face, portrait, man or woman",
    "people talking, human silhouette, crowd of people, human body",
]
_NON_HUMAN_PROMPTS = [
    "an empty landscape, architecture, nature, mist, or dramatic scenery with no people",
    "historical artifact, ancient temple, battlefield terrain, desert, or objects without humans",
]


def _ffmpeg_exe() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def _hf_online() -> bool:
    try:
        socket.gethostbyname("huggingface.co")
        return True
    except Exception:
        return False


def _get_clip_bundle() -> Optional[Tuple[Any, Any, str]]:
    """Tải singleton `CLIPModel` + `CLIPProcessor` trên CPU (ưu tiên cache local, 0-token API)."""
    global _CLIP_BUNDLE, _CLIP_FAILED_REASON
    if not ENABLE_LOCAL_CLIP or _CLIP_FAILED_REASON is not None:
        return None
    if _CLIP_BUNDLE is not None:
        return _CLIP_BUNDLE

    try:
        import torch
        from transformers import CLIPModel, CLIPProcessor

        try:
            processor = CLIPProcessor.from_pretrained(LOCAL_CLIP_MODEL, local_files_only=True)
            model = CLIPModel.from_pretrained(LOCAL_CLIP_MODEL, local_files_only=True)
        except Exception:
            if not _hf_online():
                _CLIP_FAILED_REASON = "offline_and_not_cached"
                print(f"   [VisualScorer] CLIP '{LOCAL_CLIP_MODEL}' chưa có trong cache local (offline) -> bỏ qua chấm CLIP.")
                return None
            print(f"   [VisualScorer] Đang tải local CLIP '{LOCAL_CLIP_MODEL}' lần đầu (chạy 0-token từ các lần sau)...")
            processor = CLIPProcessor.from_pretrained(LOCAL_CLIP_MODEL)
            model = CLIPModel.from_pretrained(LOCAL_CLIP_MODEL)

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device)
        model.eval()
        _CLIP_BUNDLE = (model, processor, device)
        return _CLIP_BUNDLE
    except Exception as exc:
        _CLIP_FAILED_REASON = f"{type(exc).__name__}: {exc}"
        print(f"   [VisualScorer] Không khởi tạo được local CLIP ({_CLIP_FAILED_REASON}) -> chỉ chấm chỉ số hình học/màu.")
        return None


def extract_video_keyframes(video_path: Path, max_frames: int = 3) -> List[Image.Image]:
    """Trích tối đa `max_frames` khung hình đại diện từ file `.mp4` bằng `ffmpeg`."""
    if not video_path.exists() or video_path.stat().st_size < 512:
        return []

    ff = _ffmpeg_exe()
    frames: List[Image.Image] = []
    with tempfile.TemporaryDirectory(prefix="wav2vid_kf_") as tmp_dir:
        out_pattern = str(Path(tmp_dir) / "kf_%02d.jpg")
        cmd = [
            ff,
            "-y",
            "-v",
            "error",
            "-i",
            str(video_path),
            "-vf",
            "fps=1.5,scale=360:-2",
            "-frames:v",
            str(max_frames),
            out_pattern,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        if res.returncode != 0:
            return []
        for p in sorted(Path(tmp_dir).glob("kf_*.jpg")):
            try:
                with Image.open(p) as im:
                    frames.append(im.convert("RGB"))
            except Exception:
                continue
    return frames


def load_media_keyframes(media_path: Path, media_type: str, max_frames: int = 3) -> List[Image.Image]:
    """Nạp danh sách khung hình đại diện cho cả `video` lẫn `image`."""
    if media_type == "video":
        return extract_video_keyframes(media_path, max_frames=max_frames)
    try:
        with Image.open(media_path) as im:
            return [im.convert("RGB")]
    except Exception:
        return []


def _laplacian_var(gray: np.ndarray) -> float:
    if gray.shape[0] < 3 or gray.shape[1] < 3:
        return 0.0
    lap = (
        -4.0 * gray[1:-1, 1:-1]
        + gray[:-2, 1:-1]
        + gray[2:, 1:-1]
        + gray[1:-1, :-2]
        + gray[1:-1, 2:]
    )
    return float(lap.var())


def compute_rgb_histogram(img_arr: np.ndarray, bins: int = 32) -> np.ndarray:
    """Histogram 3 kênh RGB đã chuẩn hóa để đo `continuity_score` giữa 2 cảnh liên tiếp."""
    hists = []
    for c in range(3):
        h, _ = np.histogram(img_arr[:, :, c], bins=bins, range=(0.0, 255.0), density=True)
        hists.append(h.astype(np.float32))
    return np.concatenate(hists)


def histogram_correlation(hist_a: np.ndarray, hist_b: np.ndarray) -> float:
    ha = hist_a - float(np.mean(hist_a))
    hb = hist_b - float(np.mean(hist_b))
    denom = float(np.linalg.norm(ha) * np.linalg.norm(hb))
    if denom <= 1e-8:
        return 1.0
    return float(np.clip(np.dot(ha, hb) / denom, 0.0, 1.0))


def _extract_tensor(out: Any):
    """Hỗ trợ cả `transformers` 4.x (trả Tensor) lẫn 5.x (trả `BaseModelOutputWithPooling`)."""
    if hasattr(out, "pooler_output") and out.pooler_output is not None:
        return out.pooler_output
    if hasattr(out, "image_embeds") and out.image_embeds is not None:
        return out.image_embeds
    if hasattr(out, "text_embeds") and out.text_embeds is not None:
        return out.text_embeds
    return out[0] if isinstance(out, (tuple, list)) else out


def _clip_encode_frames(frames: List[Image.Image], model: Any, processor: Any, device: str):
    import torch

    inputs = processor(images=frames, return_tensors="pt").to(device)
    with torch.no_grad():
        feats = _extract_tensor(model.get_image_features(**inputs))
        feats = feats / feats.norm(dim=-1, keepdim=True).clamp(min=1e-8)
        mean_feat = feats.mean(dim=0, keepdim=True)
        mean_feat = mean_feat / mean_feat.norm(dim=-1, keepdim=True).clamp(min=1e-8)
    return mean_feat


def _clip_encode_texts(texts: List[str], model: Any, processor: Any, device: str):
    import torch

    inputs = processor(text=texts, return_tensors="pt", padding=True, truncation=True, max_length=77).to(device)
    with torch.no_grad():
        feats = _extract_tensor(model.get_text_features(**inputs))
        feats = feats / feats.norm(dim=-1, keepdim=True).clamp(min=1e-8)
    return feats


def _apply_color_harm_array(arr: np.ndarray, params: Optional[Dict[str, Any]]) -> np.ndarray:
    if not params:
        return arr
    gains = np.asarray(params.get("gains", [1.0, 1.0, 1.0]), dtype=np.float32)
    offsets = np.asarray(params.get("offsets_255", [0.0, 0.0, 0.0]), dtype=np.float32)
    return np.clip(arr * gains + offsets, 0.0, 255.0)


def compute_pair_continuity(ev_prev: Dict[str, Any], ev_curr: Dict[str, Any]) -> float:
    """Đo độ liên tục tông màu & histogram giữa 2 cảnh liên tiếp."""
    if ev_prev.get("mean_rgb") is None or ev_curr.get("mean_rgb") is None:
        return 1.0
    mean_sim = float(np.clip(1.0 - np.abs(ev_curr["mean_rgb"] - ev_prev["mean_rgb"]).mean() * 2.0, 0.0, 1.0))
    hist_corr = histogram_correlation(ev_prev["hist_rgb"], ev_curr["hist_rgb"])
    return float(0.6 * hist_corr + 0.4 * mean_sim)


def _compute_reinhard_linear_params(
    ref_mean: np.ndarray,
    ref_std: np.ndarray,
    src_mean: np.ndarray,
    src_std: np.ndarray,
    blend: float = 0.65,
) -> Dict[str, List[float]]:
    gains: List[float] = []
    offsets_255: List[float] = []
    for c in range(3):
        r_m, r_s = float(ref_mean[c]), max(float(ref_std[c]), 0.02)
        s_m, s_s = float(src_mean[c]), max(float(src_std[c]), 0.02)
        raw_gain = float(np.clip(r_s / s_s, 0.60, 1.65))
        gain = (1.0 - blend) + blend * raw_gain
        offset_01 = blend * (r_m - gain * s_m)
        gains.append(round(gain, 4))
        offsets_255.append(round(float(np.clip(offset_01 * 255.0, -75.0, 75.0)), 2))
    return {"gains": gains, "offsets_255": offsets_255}


def harmonize_scene_continuity(
    scenes: List[Dict[str, Any]],
    run_dir: Path,
    scorer: "VisualFeatureScorer",
    intent_mode: str = "NO_HUMAN_BROLL",
    min_continuity: float = 0.75,
    blend: float = 0.65,
) -> Tuple[int, List[Dict[str, Any]]]:
    """
    ContinuityHarmonizer: đồng bộ tông màu giữa các cảnh liên tiếp có độ lệch > ngưỡng (`S_cont < min_continuity`).
      - Với cảnh `image`: xuất bản đã cân bằng Reinhard ra `scene_{i}_harm.jpg`.
      - Với cảnh `video`: gắn filter `lutrgb` để `video_renderer` áp dụng trực tiếp lúc render.
    """
    evals = [
        scorer.inspect_media(
            Path(sc["media_path"]),
            media_type=sc.get("media_type", "image"),
            prompt_en=sc.get("image_prompt_en", ""),
            intent_mode=intent_mode,
            color_harm_params=sc.get("color_harm_params"),
        )
        for sc in scenes
    ]
    harm_count = 0
    for idx in range(1, len(scenes)):
        prev_ev, curr_ev = evals[idx - 1], evals[idx]
        if prev_ev["is_corrupt"] or curr_ev["is_corrupt"]:
            continue
        if compute_pair_continuity(prev_ev, curr_ev) >= min_continuity:
            continue

        params = _compute_reinhard_linear_params(
            prev_ev["mean_rgb"], prev_ev["std_rgb"], curr_ev["mean_rgb"], curr_ev["std_rgb"], blend=blend
        )
        sc = scenes[idx]
        if sc.get("media_type") == "image":
            try:
                with Image.open(sc["media_path"]) as im:
                    arr = np.asarray(im.convert("RGB"), dtype=np.float32)
                harmonized = _apply_color_harm_array(arr, params).astype(np.uint8)
                harm_path = run_dir / f"scene_{idx + 1}_harm.jpg"
                Image.fromarray(harmonized).save(str(harm_path), quality=95)
                sc["media_path"] = str(harm_path)
                sc["continuity_harmonized"] = True
                harm_count += 1
                evals[idx] = scorer.inspect_media(
                    harm_path,
                    media_type="image",
                    prompt_en=sc.get("image_prompt_en", ""),
                    intent_mode=intent_mode,
                )
            except Exception:
                continue
        else:
            g = params["gains"]
            o = params["offsets_255"]
            sc["color_harm_params"] = params
            sc["color_harm_vf"] = (
                f"lutrgb=r='clip(val*{g[0]}+{o[0]},0,255)':"
                f"g='clip(val*{g[1]}+{o[1]},0,255)':"
                f"b='clip(val*{g[2]}+{o[2]},0,255)'"
            )
            sc["continuity_harmonized"] = True
            harm_count += 1
            evals[idx] = scorer.inspect_media(
                Path(sc["media_path"]),
                media_type="video",
                prompt_en=sc.get("image_prompt_en", ""),
                intent_mode=intent_mode,
                color_harm_params=params,
            )
    return harm_count, evals


class VisualFeatureScorer:
    """Bộ chấm điểm hình ảnh/video local (0-token API) cho Bước 1 & Bước 2 Tầng 2."""

    def __init__(self, use_clip: bool = ENABLE_LOCAL_CLIP):
        self.use_clip = use_clip
        self._non_human_text_feats = None
        self._human_text_feats = None

    def _clip_scores(
        self,
        frames: List[Image.Image],
        prompt_en: str,
        check_human: bool,
    ) -> Tuple[Optional[float], Optional[bool], Optional[float]]:
        if not self.use_clip or not frames:
            return None, None, None
        bundle = _get_clip_bundle()
        if bundle is None:
            return None, None, None

        import torch

        model, processor, device = bundle
        img_feat = _clip_encode_frames(frames, model, processor, device)

        clip_score: Optional[float] = None
        clean_prompt = (prompt_en or "").strip()
        if clean_prompt:
            txt_feat = _clip_encode_texts([clean_prompt], model, processor, device)
            clip_score = round(float((img_feat @ txt_feat.T).item()), 4)

        human_detected: Optional[bool] = None
        human_prob: Optional[float] = None
        if check_human:
            if self._human_text_feats is None:
                self._human_text_feats = _clip_encode_texts(_HUMAN_PROMPTS, model, processor, device)
                self._non_human_text_feats = _clip_encode_texts(_NON_HUMAN_PROMPTS, model, processor, device)
            sim_h = float((img_feat @ self._human_text_feats.T).max().item())
            sim_nh = float((img_feat @ self._non_human_text_feats.T).max().item())
            logits = torch.tensor([sim_h, sim_nh]) * 25.0
            probs = torch.softmax(logits, dim=0)
            human_prob = round(float(probs[0].item()), 3)
            human_detected = bool(human_prob >= 0.62 and (sim_h - sim_nh) >= 0.015)

        return clip_score, human_detected, human_prob

    def inspect_media(
        self,
        media_path: Path,
        media_type: str,
        prompt_en: str = "",
        intent_mode: str = "NO_HUMAN_BROLL",
        max_frames: int = 3,
        color_harm_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Kiểm định 1 file media (`.mp4` hoặc `.jpg`/`.png`).
        Trả về dict chứa các chỉ số thực đo để làm gate chọn ứng viên & báo cáo `visual_scores`.
        """
        frames = load_media_keyframes(media_path, media_type=media_type, max_frames=max_frames)
        if not frames:
            return {
                "is_corrupt": True,
                "frame_count": 0,
                "sharpness_score": 0.0,
                "brightness_mean": 0.0,
                "is_dark": True,
                "is_static": media_type == "video",
                "motion_diff": 0.0,
                "clip_prompt_score": None,
                "human_detected": None,
                "human_prob": None,
                "mean_rgb": None,
                "std_rgb": None,
                "hist_rgb": None,
                "reject_reasons": ["file_hong_hoac_khong_doc_duoc_frame"],
            }

        arrays = [_apply_color_harm_array(np.asarray(fr.resize((270, 480)), dtype=np.float32), color_harm_params) for fr in frames]
        sharp_vals = [_laplacian_var(a.mean(axis=2)) for a in arrays]
        sharpness = float(np.clip(np.mean(sharp_vals) / 120.0, 0.0, 1.0))

        luma_means = [float(a.mean()) for a in arrays]
        brightness = float(np.mean(luma_means))
        dark_ratios = [float((a.mean(axis=2) < 18.0).mean()) for a in arrays]
        is_dark = brightness < 22.0 or float(np.mean(dark_ratios)) > 0.85

        motion_diff = 0.0
        is_static = False
        if media_type == "video" and len(arrays) >= 2:
            diffs = [float(np.abs(arrays[idx] - arrays[idx - 1]).mean()) for idx in range(1, len(arrays))]
            motion_diff = round(float(np.mean(diffs)), 2)
            is_static = motion_diff < 1.2

        mid_arr = arrays[len(arrays) // 2]
        mean_rgb = (mid_arr.reshape(-1, 3).mean(axis=0) / 255.0).astype(np.float32)
        std_rgb = (mid_arr.reshape(-1, 3).std(axis=0) / 255.0).astype(np.float32)
        hist_rgb = compute_rgb_histogram(mid_arr)

        check_human = intent_mode == "NO_HUMAN_BROLL"
        clip_score, human_detected, human_prob = self._clip_scores(
            frames=frames,
            prompt_en=prompt_en,
            check_human=check_human,
        )

        reject_reasons: List[str] = []
        if is_dark:
            reject_reasons.append("frame_qua_toi")
        if is_static:
            reject_reasons.append("video_dung_hinh")
        if sharpness < 0.20:
            reject_reasons.append("anh_qua_mo")
        if check_human and human_detected:
            reject_reasons.append(f"dinh_nguoi_o_NO_HUMAN_BROLL(p={human_prob})")

        return {
            "is_corrupt": False,
            "frame_count": len(frames),
            "sharpness_score": round(sharpness, 3),
            "brightness_mean": round(brightness, 1),
            "is_dark": is_dark,
            "is_static": is_static,
            "motion_diff": motion_diff,
            "clip_prompt_score": clip_score,
            "human_detected": human_detected,
            "human_prob": human_prob,
            "mean_rgb": mean_rgb,
            "std_rgb": std_rgb,
            "hist_rgb": hist_rgb,
            "reject_reasons": reject_reasons,
        }
