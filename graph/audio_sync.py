"""
Module Xử lý Giọng đọc Neural VITS Tiếng Việt (`facebook/mms-tts-vie` Local PyTorch + Studio Broadcast DSP + Ambient BGM):
1. Sử dụng trực tiếp mô hình **Meta VITS Neural Vietnamese TTS (`facebook/mms-tts-vie`)** chạy 100% miễn phí trên PyTorch Local
   (giọng Nam trầm ấm tự nhiên, KHÔNG dùng giọng chị Google `gTTS`, không phụ thuộc API trả phí).
2. Xử lý ngắt nghỉ hơi thở tự nhiên theo từng mệnh đề (Clause-level Prosody Pacing) + **Studio Broadcast Mastering**
   (Warm Chest EQ + Soft Knee Compression + Subtle Studio Reverb) + **Nhạc nền Điện ảnh Ambient tự động hạ âm lượng khi có tiếng nói (Auto-Ducking BGM)**.
3. Trích xuất Acoustic Features (`rms_envelope_per_frame`, `spectral_centroid_hz_per_frame`, `onset_peaks_sec`, `timeline_phases`) ở 30fps.
"""

import os
import re
import warnings
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import scipy.io.wavfile as wavfile
import scipy.signal as signal

from config.settings import OUTPUT_AUDIO_DIR, AUDIO_SAMPLE_RATE, VIDEO_FPS

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

_VITS_MODEL = None
_VITS_TOKENIZER = None


def _get_local_vits_vietnamese_model():
    """Khởi tạo và cache mô hình Neural VITS Tiếng Việt `facebook/mms-tts-vie` trên RAM."""
    global _VITS_MODEL, _VITS_TOKENIZER
    if _VITS_MODEL is not None and _VITS_TOKENIZER is not None:
        return _VITS_MODEL, _VITS_TOKENIZER

    import torch
    from transformers import VitsModel, AutoTokenizer

    _VITS_TOKENIZER = AutoTokenizer.from_pretrained("facebook/mms-tts-vie")
    _VITS_MODEL = VitsModel.from_pretrained("facebook/mms-tts-vie")
    _VITS_MODEL.eval()
    # Tinh chỉnh tốc độ đọc và độ mượt thanh quản (Speaking Rate & Noise Scale) chuẩn Kể chuyện Điện ảnh
    _VITS_MODEL.speaking_rate = 0.96
    _VITS_MODEL.noise_scale = 0.36
    _VITS_MODEL.noise_scale_duration = 0.45
    return _VITS_MODEL, _VITS_TOKENIZER


def _resolve_bgm_file(music_mood: str = "") -> Optional[Path]:
    bgm_dir = Path(__file__).resolve().parent.parent / "assets" / "bgm"
    if music_mood and bgm_dir.exists():
        slug = re.sub(r"[^a-z0-9]+", "_", music_mood.lower()).strip("_")
        for candidate in (f"{slug}.mp3", f"{slug}.wav"):
            p = bgm_dir / candidate
            if p.exists():
                return p
    default_bgm = bgm_dir / "cinematic_piano_ambient.mp3"
    return default_bgm if default_bgm.exists() else None


def _generate_cinematic_ambient_bgm(
    num_samples: int,
    sample_rate: int,
    voice_env: np.ndarray,
    music_mood: str = "",
) -> np.ndarray:
    """
    Sử dụng file nhạc nền trong `assets/bgm/` (theo `music_mood` nếu có, mặc định `cinematic_piano_ambient.mp3`)
    và áp dụng Auto-Ducking tự động hạ âm lượng khi có giọng đọc vang lên.
    """
    import subprocess
    import imageio_ffmpeg

    bgm_path = _resolve_bgm_file(music_mood)
    pad = None

    if bgm_path is not None and bgm_path.exists():
        try:
            ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
            cmd = [
                ffmpeg_bin, "-i", str(bgm_path),
                "-f", "s16le", "-ar", str(sample_rate), "-ac", "1", "-"
            ]
            res = subprocess.run(cmd, capture_output=True, check=True)
            bgm_arr = np.frombuffer(res.stdout, dtype=np.int16).astype(np.float32) / 32768.0
            if len(bgm_arr) > 1000:
                # Lặp vòng lặp bài nhạc cho đủ độ dài num_samples
                repeats = (num_samples // len(bgm_arr)) + 1
                tiled = np.tile(bgm_arr, repeats)[:num_samples]
                pad = tiled
        except Exception as e:
            print(f" [BGM Info] Không đọc được file nhạc ({e}) -> Dùng bộ hòa âm dự phòng.")

    t = np.arange(num_samples, dtype=np.float32) / float(sample_rate)

    if pad is None:
        # Bộ hòa âm ấm áp dự phòng
        chords = [
            (110.0, 164.81, 220.0, 261.63, 329.63),
            (87.31, 130.81, 174.61, 220.0, 261.63),
            (130.81, 196.00, 246.94, 293.66, 392.00),
            (98.00, 146.83, 196.00, 246.94, 329.63),
        ]
        pad = np.zeros(num_samples, dtype=np.float32)
        chord_dur = 6.0
        for idx, freqs in enumerate(chords):
            phase = (t % (chord_dur * len(chords))) / chord_dur
            weight = np.clip(1.0 - np.abs(phase - (idx + 0.5)), 0.0, 1.0)
            weight = 0.5 - 0.5 * np.cos(np.pi * weight)
            layer = np.zeros(num_samples, dtype=np.float32)
            for h_idx, f in enumerate(freqs):
                detune = 1.0 + 0.0015 * np.sin(2 * np.pi * (0.18 + 0.05 * h_idx) * t)
                amp = 0.35 / (1.0 + 0.45 * h_idx)
                layer += amp * np.sin(2 * np.pi * f * detune * t)
            pad += weight * layer

        sos_lp = signal.butter(3, 950.0 / (sample_rate * 0.5), btype="low", output="sos")
        pad = signal.sosfilt(sos_lp, pad).astype(np.float32)
        pad = pad / (np.max(np.abs(pad)) + 1e-6)

    # Auto-Ducking chuẩn Studio: khi có giọng đọc thì hạ xuống 9%; khi nghỉ câu thì ngân lên 18%
    ducking_gain = 0.18 - 0.09 * np.clip(voice_env * 2.5, 0.0, 1.0)
    fade_in = np.minimum(1.0, t / 1.0)
    fade_out = np.minimum(1.0, (t[-1] - t) / 1.5) if len(t) > 1 else 1.0
    return (pad * ducking_gain * fade_in * fade_out).astype(np.float32)


def _apply_studio_broadcast_dsp(voice_wav: np.ndarray, sample_rate: int) -> np.ndarray:
    """
    Chuỗi DSP xử lý giọng đọc chuẩn Studio Podcast / Phim Tài Liệu:
    1. High-pass 75Hz khử ù nền.
    2. Warm Chest Boost (+3.5dB quanh 155Hz) giúp giọng nam dày và trầm ấm.
    3. Clarity Presence (+2.0dB quanh 3100Hz) giúp phát âm tiếng Việt rõ nét.
    4. Soft-Knee Dynamic Tanh Compressor + Subtle Studio Early Reflection.
    """
    nyq = sample_rate * 0.5
    # 1. High-pass 75Hz
    sos_hp = signal.butter(2, 75.0 / nyq, btype="high", output="sos")
    y = signal.sosfilt(sos_hp, voice_wav).astype(np.float32)

    # 2. Warm Chest Bandpass Boost (110Hz - 240Hz)
    sos_warm = signal.butter(2, [110.0 / nyq, 240.0 / nyq], btype="band", output="sos")
    warm_band = signal.sosfilt(sos_warm, y).astype(np.float32)
    y = y + 0.42 * warm_band

    # 3. Clarity Presence Band (2400Hz - 4200Hz)
    sos_pres = signal.butter(2, [2400.0 / nyq, min(0.92, 4200.0 / nyq)], btype="band", output="sos")
    pres_band = signal.sosfilt(sos_pres, y).astype(np.float32)
    y = y + 0.22 * pres_band

    # 4. Subtle Studio Room Early Reflection (28ms & 54ms delay nhẹ 6%)
    d1 = int(0.028 * sample_rate)
    d2 = int(0.054 * sample_rate)
    reverb = np.zeros_like(y)
    if len(y) > d2:
        reverb[d1:] += 0.055 * y[:-d1]
        reverb[d2:] += 0.030 * y[:-d2]
    y = y + reverb

    # 5. Soft-Knee Broadcast Tube Saturation & Normalization
    y = y / (np.max(np.abs(y)) + 1e-6)
    y = np.tanh(y * 1.35) / np.tanh(1.35)
    return y.astype(np.float32)


_DIGITS_VI = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]


def _vn_below_1000(n: int, full: bool) -> str:
    h, rest = divmod(n, 100)
    t, u = divmod(rest, 10)
    words: List[str] = []
    if h or full:
        words += [_DIGITS_VI[h], "trăm"]
    if t > 1:
        words += [_DIGITS_VI[t], "mươi"]
        if u == 1:
            words.append("mốt")
        elif u == 5:
            words.append("lăm")
        elif u:
            words.append(_DIGITS_VI[u])
    elif t == 1:
        words.append("mười")
        if u == 5:
            words.append("lăm")
        elif u:
            words.append(_DIGITS_VI[u])
    else:
        if u:
            if h or full:
                words.append("linh")
            words.append(_DIGITS_VI[u])
    return " ".join(words)


def vn_number_to_words(n: int) -> str:
    """Đọc số nguyên không âm bằng chữ tiếng Việt (VITS không đọc được chữ số)."""
    if n == 0:
        return "không"
    units = ["", "nghìn", "triệu", "tỷ"]
    groups: List[int] = []
    while n > 0:
        n, g = divmod(n, 1000)
        groups.append(g)
    parts: List[str] = []
    for idx in range(len(groups) - 1, -1, -1):
        g = groups[idx]
        if g == 0:
            continue
        full = idx != len(groups) - 1
        parts.append(f"{_vn_below_1000(g, full)} {units[idx] if idx < len(units) else ''}".strip())
    return " ".join(parts)


def normalize_vi_text_for_tts(text: str) -> str:
    """Chuẩn hoá văn bản cho VITS: số -> chữ, % -> phần trăm, bỏ ký hiệu lạ."""

    def _num(m: "re.Match[str]") -> str:
        raw = m.group(0).replace(".", "").replace(" ", "")
        try:
            return vn_number_to_words(int(raw))
        except ValueError:
            return m.group(0)

    t = re.sub(r"(\d+(?:[.,]\d+)?)\s*%", lambda m: m.group(1) + " phần trăm", text)
    t = re.sub(r"(?<=\d),(?=\d)", " phẩy ", t)
    t = re.sub(r"\d{1,3}(?:\.\d{3})+|\d+", _num, t)
    t = t.replace("&", " và ").replace("/", " trên ")
    t = re.sub(r"[\"“”()\[\]*#_~^<>|\\]", "", t)
    t = re.sub(r"[-–—]+", ", ", t)
    return re.sub(r"\s+", " ", t).strip()


def _vits_clause_audio(text: str, model, tokenizer, vits_sr: int, torch_mod) -> np.ndarray:
    """Sinh giọng cho 1 đoạn văn (nhiều mệnh đề), có ngắt nghỉ theo dấu câu. Không kèm đệm đầu/cuối."""
    parts = [p.strip() for p in re.split(r"([,.;:?!]+)", text) if p.strip()]
    chunks: List[np.ndarray] = []
    with torch_mod.no_grad():
        for part in parts:
            if re.match(r"^[,.;:?!]+$", part):
                pause_sec = 0.46 if any(ch in part for ch in ".?!") else 0.20
                chunks.append(np.zeros(int(pause_sec * vits_sr), dtype=np.float32))
                continue
            clause_clean = part.lower().strip()
            if not clause_clean:
                continue
            inputs = tokenizer(clause_clean, return_tensors="pt")
            if inputs["input_ids"].shape[1] == 0:
                continue
            out_wav = model(**inputs).waveform[0].cpu().numpy().astype(np.float32)

            non_silent = np.where(np.abs(out_wav) > 0.008)[0]
            if len(non_silent) > 10:
                s_idx = max(0, int(non_silent[0]) - int(0.015 * vits_sr))
                e_idx = min(len(out_wav), int(non_silent[-1]) + int(0.025 * vits_sr))
                out_wav = out_wav[s_idx:e_idx]

            fade_len = min(int(0.008 * vits_sr), len(out_wav) // 4)
            if fade_len > 2:
                out_wav[:fade_len] *= np.linspace(0.0, 1.0, fade_len, dtype=np.float32)
                out_wav[-fade_len:] *= np.linspace(1.0, 0.0, fade_len, dtype=np.float32)
            chunks.append(out_wav)
    return np.concatenate(chunks) if chunks else np.zeros(int(0.3 * vits_sr), dtype=np.float32)


def _synth_sfx(cue: str, sr: int) -> np.ndarray:
    """Sinh hiệu ứng âm thanh chuyển nhịp (`low_thud`, `subtle_whoosh`, `camera_click`, `wind_swell`, `deep_sub_drop`, `heartbeat_pulse`, `clock_tick_stop`)."""
    cue = (cue or "none").strip().lower()
    if cue == "low_thud":
        n = int(0.45 * sr)
        t = np.linspace(0.0, 0.45, n, endpoint=False, dtype=np.float32)
        freq = 68.0 - 32.0 * (t / 0.45)
        env = np.exp(-t * 8.5).astype(np.float32)
        return (np.sin(2.0 * np.pi * np.cumsum(freq) / sr) * env * 0.42).astype(np.float32)
    if cue == "deep_sub_drop":
        n = int(0.65 * sr)
        t = np.linspace(0.0, 0.65, n, endpoint=False, dtype=np.float32)
        freq = 92.0 * np.exp(-t * 2.4) + 28.0
        env = np.exp(-t * 4.8).astype(np.float32)
        return (np.sin(2.0 * np.pi * np.cumsum(freq) / sr) * env * 0.46).astype(np.float32)
    if cue == "heartbeat_pulse":
        n = int(0.55 * sr)
        t = np.linspace(0.0, 0.55, n, endpoint=False, dtype=np.float32)
        lub = np.exp(-((t - 0.06) / 0.032) ** 2) * np.sin(2.0 * np.pi * 55.0 * t)
        dub = np.exp(-((t - 0.24) / 0.028) ** 2) * np.sin(2.0 * np.pi * 48.0 * t) * 0.78
        return ((lub + dub) * 0.44).astype(np.float32)
    if cue == "clock_tick_stop":
        n = int(0.32 * sr)
        t = np.linspace(0.0, 0.32, n, endpoint=False, dtype=np.float32)
        tick1 = np.exp(-t * 55.0) * np.sin(2.0 * np.pi * 1650.0 * t)
        t2 = np.maximum(0.0, t - 0.14)
        tick2 = np.where(t >= 0.14, np.exp(-t2 * 60.0) * np.sin(2.0 * np.pi * 1250.0 * t2) * 0.75, 0.0)
        return ((tick1 + tick2) * 0.26).astype(np.float32)
    if cue == "subtle_whoosh":
        n = int(0.36 * sr)
        rng = np.random.default_rng(7)
        noise = rng.normal(0.0, 1.0, n).astype(np.float32)
        b, a = signal.butter(2, [300.0 / (sr / 2), min(0.95, 2200.0 / (sr / 2))], btype="band")
        filtered = signal.lfilter(b, a, noise).astype(np.float32)
        env = np.hanning(n).astype(np.float32)
        return (filtered * env * 0.18).astype(np.float32)
    if cue == "camera_click":
        n = int(0.09 * sr)
        t = np.linspace(0.0, 0.09, n, endpoint=False, dtype=np.float32)
        rng = np.random.default_rng(13)
        click = rng.normal(0.0, 1.0, n).astype(np.float32) * np.exp(-t * 65.0)
        return (click * 0.25).astype(np.float32)
    if cue == "wind_swell":
        n = int(0.68 * sr)
        rng = np.random.default_rng(21)
        noise = rng.normal(0.0, 1.0, n).astype(np.float32)
        b, a = signal.butter(2, min(0.95, 750.0 / (sr / 2)), btype="low")
        filtered = signal.lfilter(b, a, noise).astype(np.float32)
        env = np.hanning(n).astype(np.float32)
        return (filtered * env * 0.22).astype(np.float32)
    return np.zeros(0, dtype=np.float32)


def _normalize_loudness_lufs(wav_path: Path, sample_rate: int, target_lufs: float = -14.0) -> bool:
    """Chuẩn hóa âm lượng đầu ra về chuẩn TikTok/Shorts (`-14 LUFS`, `-1 dBTP`) bằng FFmpeg `loudnorm`."""
    import subprocess
    import imageio_ffmpeg

    tmp_path = wav_path.with_suffix(".lufs_tmp.wav")
    try:
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [
            ff,
            "-y",
            "-v",
            "error",
            "-i",
            str(wav_path),
            "-af",
            f"loudnorm=I={target_lufs}:TP=-1.0:LRA=11",
            "-ar",
            str(sample_rate),
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(tmp_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if res.returncode == 0 and tmp_path.exists() and tmp_path.stat().st_size > 1000:
            tmp_path.replace(wav_path)
            return True
    except Exception:
        pass
    finally:
        tmp_path.unlink(missing_ok=True)
    return False


def _master_and_mix(
    raw_voice: np.ndarray,
    vits_sr: int,
    sample_rate: int,
    wav_path: Path,
    sfx_events: Optional[List[Tuple[float, str]]] = None,
    music_mood: str = "",
) -> Path:
    if vits_sr != sample_rate:
        target_len = int(len(raw_voice) * sample_rate / float(vits_sr))
        raw_voice = signal.resample(raw_voice, target_len).astype(np.float32)

    mastered_voice = _apply_studio_broadcast_dsp(raw_voice, sample_rate)
    win_len = max(1, int(0.08 * sample_rate))
    voice_env = np.convolve(np.abs(mastered_voice), np.ones(win_len) / win_len, mode="same")
    bgm = _generate_cinematic_ambient_bgm(len(mastered_voice), sample_rate, voice_env, music_mood=music_mood)
    final_mix = mastered_voice * 0.86 + bgm
    if sfx_events:
        for t_sec, cue in sfx_events:
            sfx = _synth_sfx(cue, sample_rate)
            if len(sfx) > 0:
                idx = max(0, int(t_sec * sample_rate))
                end = min(len(final_mix), idx + len(sfx))
                if end > idx:
                    final_mix[idx:end] += sfx[: end - idx]
    final_mix = final_mix / (np.max(np.abs(final_mix)) + 1e-6) * 0.90
    wavfile.write(str(wav_path), sample_rate, (final_mix * 32767.0).astype(np.int16))
    lufs_ok = _normalize_loudness_lufs(wav_path, sample_rate, target_lufs=-14.0)
    lufs_tag = " + -14 LUFS" if lufs_ok else ""
    print(f"[TTS Neural VITS Studio] Đã sinh giọng đọc (`facebook/mms-tts-vie` + Studio EQ + BGM{lufs_tag}) -> {wav_path.name}")
    return wav_path


def _resolve_wav_path(output_filename: Any) -> Path:
    target = Path(output_filename)
    wav_path = target if (target.is_absolute() or len(target.parts) > 1) else OUTPUT_AUDIO_DIR / target.name
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    return wav_path


def synthesize_scene_voiceover(
    scene_texts: List[str],
    output_filename: Any = "voiceover_studio.wav",
    sample_rate: int = AUDIO_SAMPLE_RATE,
    scene_gap_sec: float = 0.18,
    sfx_cues: Optional[List[str]] = None,
    music_mood: str = "",
) -> Tuple[Path, List[Tuple[float, float]]]:
    """
    Sinh giọng đọc THEO TỪNG CẢNH và trả về mốc thời gian thật (start_sec, end_sec) của lời mỗi cảnh trong file wav.
    Nhờ đó ảnh, chuyển cảnh và phụ đề từng từ khớp đúng thời điểm đọc (không ước lượng theo số ký tự).
    Không có dự phòng "bíp sine": nếu VITS lỗi sẽ raise để người dùng biết.
    """
    wav_path = _resolve_wav_path(output_filename)
    import torch

    model, tokenizer = _get_local_vits_vietnamese_model()
    vits_sr = int(model.config.sampling_rate)

    lead = 0.20
    chunks: List[np.ndarray] = [np.zeros(int(lead * vits_sr), dtype=np.float32)]
    cursor = lead
    timings: List[Tuple[float, float]] = []
    sfx_events: List[Tuple[float, str]] = []
    for i, text in enumerate(scene_texts):
        audio = _vits_clause_audio(normalize_vi_text_for_tts(text), model, tokenizer, vits_sr, torch)
        dur = len(audio) / float(vits_sr)
        timings.append((round(cursor, 3), round(cursor + dur, 3)))
        if sfx_cues and i < len(sfx_cues):
            cue = str(sfx_cues[i] or "none").strip().lower()
            if cue != "none":
                sfx_events.append((max(0.0, cursor - 0.08), cue))
        chunks.append(audio)
        chunks.append(np.zeros(int(scene_gap_sec * vits_sr), dtype=np.float32))
        cursor += dur + scene_gap_sec
    chunks.append(np.zeros(int(0.45 * vits_sr), dtype=np.float32))
    _master_and_mix(
        np.concatenate(chunks), vits_sr, sample_rate, wav_path, sfx_events=sfx_events, music_mood=music_mood
    )
    return wav_path, timings


def synthesize_voiceover_waveform(
    full_voiceover_text: str,
    output_filename: Any = "voiceover_studio.wav",
    sample_rate: int = AUDIO_SAMPLE_RATE,
) -> Path:
    """Sinh giọng đọc Neural VITS Tiếng Việt cho 1 đoạn văn liền (giữ cho tương thích ngược)."""
    wav_path = _resolve_wav_path(output_filename)
    try:
        import torch

        model, tokenizer = _get_local_vits_vietnamese_model()
        vits_sr = int(model.config.sampling_rate)
        text = normalize_vi_text_for_tts(full_voiceover_text)
        raw = np.concatenate(
            [
                np.zeros(int(0.20 * vits_sr), dtype=np.float32),
                _vits_clause_audio(text, model, tokenizer, vits_sr, torch),
                np.zeros(int(0.45 * vits_sr), dtype=np.float32),
            ]
        )
        return _master_and_mix(raw, vits_sr, sample_rate, wav_path)
    except Exception as e:
        print(f" [TTS Warning] Lỗi VITS Neural ({e}) -> Chuyển sang bộ tổng hợp dự phòng.")

    dur = 10.0
    t = np.linspace(0, dur, int(dur * sample_rate), endpoint=False, dtype=np.float32)
    wave = 0.5 * np.sin(2 * np.pi * 130.0 * t)
    wavfile.write(str(wav_path), sample_rate, (wave * 32767).astype(np.int16))
    return wav_path


def extract_waveform_sync_features(
    wav_path: Path,
    scene_narration: str,
    outro_reflection: str,
    closing_prayer: str,
    fps: int = VIDEO_FPS,
) -> Dict[str, Any]:
    """
    Đọc file dạng sóng `.wav` và dùng `scipy.signal` trích xuất bộ Feature đồng bộ chính xác với từng khung hình Video.
    """
    sr, data = wavfile.read(str(wav_path))
    if data.ndim > 1:
        data = data[:, 0]
    waveform = data.astype(np.float32) / 32768.0
    total_samples = len(waveform)
    duration_sec = round(total_samples / float(sr), 2)
    total_frames = max(1, int(np.ceil(duration_sec * fps)))
    samples_per_frame = max(1, int(sr / fps))

    rms_per_frame: List[float] = []
    centroid_per_frame: List[float] = []
    window = np.hanning(samples_per_frame)
    freqs = np.fft.rfftfreq(samples_per_frame, d=1.0 / sr)

    for f_idx in range(total_frames):
        start = f_idx * samples_per_frame
        end = min(total_samples, start + samples_per_frame)
        frame_slice = waveform[start:end]
        if len(frame_slice) < samples_per_frame:
            frame_slice = np.pad(frame_slice, (0, samples_per_frame - len(frame_slice)))

        rms = float(np.sqrt(np.mean(frame_slice ** 2)))
        rms_per_frame.append(rms)

        mag = np.abs(np.fft.rfft(frame_slice * window))
        mag_sum = float(np.sum(mag))
        centroid = float(np.sum(freqs * mag) / mag_sum) if mag_sum > 1e-6 else 0.0
        centroid_per_frame.append(round(centroid, 1))

    max_rms = max(rms_per_frame) if rms_per_frame and max(rms_per_frame) > 0 else 1.0
    norm_rms = [round(r / max_rms, 3) for r in rms_per_frame]

    peaks, _ = signal.find_peaks(norm_rms, height=0.22, distance=max(1, int(fps * 0.14)))
    onset_timestamps_sec = [round(int(p) / float(fps), 2) for p in peaks]

    len_s1 = max(1, len(scene_narration.split()))
    len_s2 = max(1, len(outro_reflection.split()))
    len_s3 = max(1, len(closing_prayer.split()))
    total_w = float(len_s1 + len_s2 + len_s3)

    t1_end = round(duration_sec * (len_s1 / total_w), 2)
    t2_end = round(duration_sec * ((len_s1 + len_s2) / total_w), 2)

    timeline_phases = {
        "phase_1_main_scene_narration": {
            "start_sec": 0.0,
            "end_sec": t1_end,
            "start_frame": 0,
            "end_frame": int(t1_end * fps),
            "text": scene_narration,
        },
        "phase_2_outro_moral_lesson": {
            "start_sec": t1_end,
            "end_sec": t2_end,
            "start_frame": int(t1_end * fps),
            "end_frame": int(t2_end * fps),
            "text": outro_reflection,
        },
        "phase_3_closing_prayer": {
            "start_sec": t2_end,
            "end_sec": duration_sec,
            "start_frame": int(t2_end * fps),
            "end_frame": total_frames,
            "text": closing_prayer,
        },
    }

    sample_indices = np.linspace(0, total_frames - 1, min(10, total_frames), dtype=int)
    frame_sync_preview = [
        {
            "frame_idx": int(i),
            "time_sec": round(int(i) / float(fps), 2),
            "rms_energy": norm_rms[int(i)],
            "spectral_centroid_hz": centroid_per_frame[int(i)],
            "mouth_open_ratio": round(min(1.0, norm_rms[int(i)] * 1.15), 2),
        }
        for i in sample_indices
    ]

    return {
        "sample_rate_hz": sr,
        "video_fps": fps,
        "duration_sec": duration_sec,
        "total_video_frames": total_frames,
        "rms_envelope_per_frame": norm_rms,
        "syllable_onset_count": len(onset_timestamps_sec),
        "onset_peaks_sec": onset_timestamps_sec[:15],
        "timeline_phases": timeline_phases,
        "frame_sync_preview": frame_sync_preview,
    }
