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
from typing import Dict, Any, List, Optional
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


def _generate_cinematic_ambient_bgm(num_samples: int, sample_rate: int, voice_env: np.ndarray) -> np.ndarray:
    """
    Tạo nhạc nền Ambient Điện ảnh (Hans Zimmer / Makoto Shinkai Ethereal Warm Pad)
    tự động hạ nhỏ (Auto-Ducking) khi giọng đọc vang lên và ngân nhẹ ở các nhịp nghỉ câu.
    """
    t = np.arange(num_samples, dtype=np.float32) / float(sample_rate)
    # Vòng hòa âm Am9 - Fmaj7 - Cmaj7 - G6 ấm áp, sâu lắng
    chords = [
        (110.0, 164.81, 220.0, 261.63, 329.63),   # Am9
        (87.31, 130.81, 174.61, 220.0, 261.63),   # Fmaj7
        (130.81, 196.00, 246.94, 293.66, 392.00), # Cmaj9
        (98.00, 146.83, 196.00, 246.94, 329.63),  # G6
    ]
    pad = np.zeros(num_samples, dtype=np.float32)
    chord_dur = 6.0
    for idx, freqs in enumerate(chords):
        # Trọng số chuyển mượt giữa các hợp âm theo chu kỳ 24s
        phase = (t % (chord_dur * len(chords))) / chord_dur
        weight = np.clip(1.0 - np.abs(phase - (idx + 0.5)), 0.0, 1.0)
        # Làm mượt đường bao chuyển hợp âm
        weight = 0.5 - 0.5 * np.cos(np.pi * weight)
        layer = np.zeros(num_samples, dtype=np.float32)
        for h_idx, f in enumerate(freqs):
            detune = 1.0 + 0.0015 * np.sin(2 * np.pi * (0.18 + 0.05 * h_idx) * t)
            amp = 0.35 / (1.0 + 0.45 * h_idx)
            layer += amp * np.sin(2 * np.pi * f * detune * t)
        pad += weight * layer

    # Lọc thông thấp (Low-pass filter ở 950Hz) để nhạc nền ấm, sâu, không bao giờ lấn tần số giọng nói (1kHz-4kHz)
    sos_lp = signal.butter(3, 950.0 / (sample_rate * 0.5), btype="low", output="sos")
    pad = signal.sosfilt(sos_lp, pad).astype(np.float32)
    pad = pad / (np.max(np.abs(pad)) + 1e-6)

    # Auto-Ducking: Khi có tiếng đọc (voice_env cao), nhạc nền hạ xuống 7%; khi nghỉ lấy hơi, nhạc nền dâng nhẹ lên 14%
    ducking_gain = 0.14 - 0.075 * np.clip(voice_env * 2.2, 0.0, 1.0)
    # Fade-in 1.0s đầu và Fade-out 1.5s cuối
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


def synthesize_voiceover_waveform(
    full_voiceover_text: str,
    output_filename: str,
    sample_rate: int = AUDIO_SAMPLE_RATE,
) -> Path:
    """
    Sinh giọng đọc Neural VITS Tiếng Việt (`facebook/mms-tts-vie`) chạy trực tiếp trên PyTorch
    kết hợp Studio Broadcast Mastering & Nhạc nền Ambient Auto-Ducking.
    """
    OUTPUT_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    wav_path = OUTPUT_AUDIO_DIR / output_filename
    wav_path.parent.mkdir(parents=True, exist_ok=True)

    # Làm sạch ký tự đặc biệt nhưng giữ nguyên dấu câu để tách nhịp ngắt nghỉ tự nhiên
    clean_text = re.sub(r'["“”()\[\]*#]', "", full_voiceover_text)
    clean_text = re.sub(r"\s+", " ", clean_text).strip()

    try:
        import torch
        model, tokenizer = _get_local_vits_vietnamese_model()
        vits_sr = int(model.config.sampling_rate)

        # Tách văn bản theo từng mệnh đề dấu phẩy, chấm, hỏi, chấm than để tạo nhịp thở tự nhiên
        parts = [p.strip() for p in re.split(r"([,.;:?!]+)", clean_text) if p.strip()]
        chunks: List[np.ndarray] = [np.zeros(int(0.20 * vits_sr), dtype=np.float32)]

        with torch.no_grad():
            for part in parts:
                if re.match(r"^[,.;:?!]+$", part):
                    if any(ch in part for ch in ".?!"):
                        pause_sec = 0.46  # Nghỉ hết câu truyền cảm
                    else:
                        pause_sec = 0.20  # Nghỉ lấy hơi nhẹ ở dấu phẩy
                    chunks.append(np.zeros(int(pause_sec * vits_sr), dtype=np.float32))
                    continue

                # Chuẩn hóa chữ thường cho VITS tokenizer tiếng Việt
                clause_clean = part.lower().strip()
                if not clause_clean:
                    continue
                inputs = tokenizer(clause_clean, return_tensors="pt")
                if inputs["input_ids"].shape[1] == 0:
                    continue
                out_wav = model(**inputs).waveform[0].cpu().numpy().astype(np.float32)

                # Khử khoảng lặng thừa ở hai đầu mỗi mệnh đề và áp fade 8ms chống click
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

        chunks.append(np.zeros(int(0.45 * vits_sr), dtype=np.float32))
        raw_voice = np.concatenate(chunks)

        if vits_sr != sample_rate:
            target_len = int(len(raw_voice) * sample_rate / float(vits_sr))
            raw_voice = signal.resample(raw_voice, target_len).astype(np.float32)

        # Áp dụng Studio Broadcast Mastering (Warmth EQ + Presence + Studio Room)
        mastered_voice = _apply_studio_broadcast_dsp(raw_voice, sample_rate)

        # Tính đường bao âm lượng giọng nói để điều khiển Auto-Ducking cho nhạc nền Ambient
        win_len = max(1, int(0.08 * sample_rate))
        voice_env = np.convolve(np.abs(mastered_voice), np.ones(win_len) / win_len, mode="same")

        # Hòa trộn nhạc nền Ambient Điện ảnh (Auto-Ducking)
        bgm = _generate_cinematic_ambient_bgm(len(mastered_voice), sample_rate, voice_env)
        final_mix = mastered_voice * 0.86 + bgm
        final_mix = final_mix / (np.max(np.abs(final_mix)) + 1e-6) * 0.90

        pcm16 = (final_mix * 32767.0).astype(np.int16)
        wavfile.write(str(wav_path), sample_rate, pcm16)
        print(
            f"[TTS Neural VITS Studio] Đã sinh giọng đọc Nam Neural VITS (`facebook/mms-tts-vie` + Studio EQ + Ambient BGM) -> {wav_path.name}"
        )
        return wav_path
    except Exception as e:
        print(f" [TTS Warning] Lỗi VITS Neural ({e}) -> Chuyển sang bộ tổng hợp dự phòng.")

    # Dự phòng an toàn
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
