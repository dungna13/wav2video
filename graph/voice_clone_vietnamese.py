"""
Module Voice Clone tiếng Việt cục bộ (Offline) sử dụng F5-TTS Vietnamese.
Tự động nhân bản chất giọng từ file âm thanh mẫu (ví dụ: workspace/voice-preview.mp3).
"""

import os
import sys
from pathlib import Path
from typing import Optional, Tuple
import soundfile as sf
import torch

# Tối ưu hóa số luồng CPU để F5-TTS suy luận nhanh nhất
try:
    torch.set_num_threads(min(16, max(4, os.cpu_count() or 8)))
except Exception:
    pass

_MODEL = None
_VOCODER = None
_REF_AUDIO = None
_REF_TEXT = None

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_REF_AUDIO = BASE_DIR / "workspace" / "voice-preview.mp3"
DEFAULT_REF_TEXT = (
    "Alo, mình đây. Bạn đang ở nhà phải không? Mình gọi vì chiều nay thợ sửa máy lạnh hẹn qua trong khoảng "
    "3 giờ đến 5 giờ, mà 5 giờ rưỡi mình mới tan làm."
)

MODEL_PATH = BASE_DIR / "models" / "f5tts_vi" / "model_latest.safetensors"
VOCAB_PATH = BASE_DIR / "models" / "f5tts_vi" / "vocab.txt"


def get_or_load_vietnamese_clone_model():
    """Tải và lưu trữ model trong bộ nhớ RAM để không phải nạp lại từ ổ cứng."""
    global _MODEL, _VOCODER
    if _MODEL is not None and _VOCODER is not None:
        return _MODEL, _VOCODER

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Không tìm thấy model F5-TTS tại {MODEL_PATH}. "
            "Vui lòng tải file model_latest.safetensors đặt vào thư mục models/f5tts_vi/."
        )

    # Đảm bảo PATH có thư mục chứa Python interpreter hiện tại (tương thích Windows & Linux)
    venv_bin = str(Path(sys.executable).resolve().parent)
    if venv_bin not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{venv_bin}{os.pathsep}{os.environ.get('PATH', '')}"

    from f5_tts.infer.utils_infer import load_model, load_vocoder
    from f5_tts.model import DiT

    print("🎙️ [Voice Clone Vi] Đang tải mô hình F5-TTS Vietnamese vào RAM...")
    _VOCODER = load_vocoder(vocoder_name="vocos")
    _MODEL = load_model(
        model_cls=DiT,
        model_cfg=dict(dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4),
        ckpt_path=str(MODEL_PATH),
        mel_spec_type="vocos",
        vocab_file=str(VOCAB_PATH),
    )
    print("✅ [Voice Clone Vi] Nạp mô hình tiếng Việt thành công!")
    return _MODEL, _VOCODER


def clone_vietnamese_speech(
    text: str,
    output_path: Path,
    ref_audio_path: Optional[Path] = None,
    ref_text: Optional[str] = None,
    speed: float = 1.0,
    nfe_step: int = 16,
) -> Path:
    """
    Tạo file audio tiếng Việt nhân bản giọng nói từ audio mẫu.
    """
    global _REF_AUDIO, _REF_TEXT

    ref_audio_file = Path(ref_audio_path or DEFAULT_REF_AUDIO)
    ref_text_content = ref_text or DEFAULT_REF_TEXT

    model, vocoder = get_or_load_vietnamese_clone_model()

    from f5_tts.infer.utils_infer import infer_process, preprocess_ref_audio_text

    if _REF_AUDIO is None or _REF_TEXT != ref_text_content:
        processed_audio, processed_text = preprocess_ref_audio_text(
            str(ref_audio_file),
            ref_text_content,
        )
        _REF_AUDIO = processed_audio
        _REF_TEXT = processed_text

    clean_text = text.strip()
    if not clean_text:
        clean_text = "..."

    import re
    import numpy as np
    from f5_tts.infer.utils_infer import infer_process

    # Tách kịch bản thành các câu đơn tự nhiên theo dấu chấm, hỏi, than
    sentences = [s.strip() for s in re.split(r"(?<=[.?!])\s+", clean_text) if s.strip()]
    if not sentences:
        sentences = [clean_text]

    segments = []
    final_sample_rate = 24000
    pause_samples = int(0.25 * final_sample_rate)
    pause = np.zeros(pause_samples, dtype=np.float32)

    for idx, sent in enumerate(sentences):
        audio_segment, sr_out, _ = infer_process(
            _REF_AUDIO,
            _REF_TEXT,
            sent,
            model,
            vocoder,
            mel_spec_type="vocos",
            nfe_step=nfe_step,
            speed=speed,
        )
        if audio_segment is not None and len(audio_segment) > 0:
            segments.append(audio_segment)
            if idx < len(sentences) - 1:
                segments.append(pause)
            final_sample_rate = sr_out

    if segments:
        final_wave = np.concatenate(segments)
    else:
        final_wave = np.zeros(int(final_sample_rate * 0.5), dtype=np.float32)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), final_wave, final_sample_rate)
    return output_path

