"""
Đọc toàn bộ biến môi trường từ file `.env` cho hệ thống Wav2Vid Đa Chủ Đề (Topic-to-Video Agentic Pipeline).
"""

import os
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_FILE, override=True)


def _resolve_path(env_val: str, default_rel: str) -> Path:
    raw = os.getenv(env_val, default_rel).strip()
    p = Path(raw)
    return p if p.is_absolute() else (BASE_DIR / p).resolve()


# =====================================================================
# 1. ĐƯỜNG DẪN FILE & WORKSPACE (ĐỌC TỪ `.env`)
# =====================================================================
CHECKPOINT_DB_PATH: Path = _resolve_path("CHECKPOINT_DB_PATH", "./workspace/wav2vid_checkpoints.sqlite")
ASSETS_DIR: Path = _resolve_path("ASSETS_DIR", "./assets")
CONTINUITY_STATE_DIR: Path = _resolve_path("CONTINUITY_STATE_DIR", "./assets/continuity_state")
WORKSPACE_DIR: Path = _resolve_path("WORKSPACE_DIR", "./workspace")
OUTPUT_AUDIO_DIR: Path = WORKSPACE_DIR
AUDIO_SAMPLE_RATE: int = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
VIDEO_FPS: int = int(os.getenv("VIDEO_FPS", "30"))
TTS_VOICE: str = os.getenv("TTS_VOICE", "vi-VN-NamMinhNeural").strip()
TTS_RATE: str = os.getenv("TTS_RATE", "-4%").strip()
TTS_PITCH: str = os.getenv("TTS_PITCH", "-2Hz").strip()

# =====================================================================
# 2. CẤU HÌNH LLM THINKING API (ĐỌC TỪ `.env`)
# =====================================================================
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip()
GEMINI_TEMPERATURE: float = float(os.getenv("GEMINI_TEMPERATURE", "0.2"))
GEMINI_THINKING_BUDGET: int = int(os.getenv("GEMINI_THINKING_BUDGET", "1024"))
FREE_LLM_ENDPOINT: str = os.getenv("FREE_LLM_ENDPOINT", "https://text.pollinations.ai/openai").strip()
FREE_LLM_MODEL: str = os.getenv("FREE_LLM_MODEL", "openai-fast").strip()
FREE_LLM_TIMEOUT: int = int(os.getenv("FREE_LLM_TIMEOUT", "150"))

# =====================================================================
# 3. CẤU HÌNH API TẠO ẢNH 9:16 (ĐỌC TỪ `.env`)
# =====================================================================
IMAGE_PROVIDER: str = os.getenv("IMAGE_PROVIDER", "pollinations").strip().lower()
POLLINATIONS_MODEL: str = os.getenv("POLLINATIONS_MODEL", "turbo").strip()
IMAGE_WIDTH: int = int(os.getenv("IMAGE_WIDTH", "720"))
IMAGE_HEIGHT: int = int(os.getenv("IMAGE_HEIGHT", "1280"))
# Video stock thật (tuỳ chọn, miễn phí tại https://www.pexels.com/api/): có key thì ưu tiên footage thật cho từng cảnh
PEXELS_API_KEY: str = os.getenv("PEXELS_API_KEY", "").strip()
# Thay thế khi Pexels tạm ngừng cấp key: https://pixabay.com/api/docs/ (key hiện ngay sau khi đăng ký)
PIXABAY_API_KEY: str = os.getenv("PIXABAY_API_KEY", "").strip()
DOWNLOAD_GENERATED_IMAGE: bool = os.getenv("DOWNLOAD_GENERATED_IMAGE", "true").strip().lower() == "true"

# =====================================================================
# 4. NGƯỠNG KIỂM ĐỊNH CHẤT LƯỢNG & WAV2VID SCORING GATES (ĐỌC TỪ `.env`)
# =====================================================================
MAX_SCENE_PROMPT_WORDS: int = int(os.getenv("MAX_SCENE_PROMPT_WORDS", "60"))
MAX_VISUAL_TRAITS_WORDS: int = int(os.getenv("MAX_VISUAL_TRAITS_WORDS", "30"))
MIN_AVERAGE_SCORE: float = float(os.getenv("MIN_AVERAGE_SCORE", "8.0"))
MIN_FAITHFULNESS_SCORE: float = float(os.getenv("MIN_FAITHFULNESS_SCORE", "8.0"))
MIN_FACE_SIMILARITY_SCORE: float = float(os.getenv("MIN_FACE_SIMILARITY_SCORE", "8.5"))
MAX_PROMPT_RETRIES: int = int(os.getenv("MAX_PROMPT_RETRIES", "3"))

# Chốt chặn 1: Visual Feature Gate (`VisualFeatureScorer`)
ENABLE_LOCAL_CLIP: bool = os.getenv("ENABLE_LOCAL_CLIP", "true").strip().lower() == "true"
LOCAL_CLIP_MODEL: str = os.getenv("LOCAL_CLIP_MODEL", "openai/clip-vit-base-patch32").strip()
MIN_CLIP_PROMPT_SCORE: float = float(os.getenv("MIN_CLIP_PROMPT_SCORE", "0.28"))
MIN_CONTINUITY_SCORE: float = float(os.getenv("MIN_CONTINUITY_SCORE", "0.75"))
MIN_ID_POSE_SCORE: float = float(os.getenv("MIN_ID_POSE_SCORE", "0.70"))
MIN_VISUAL_TOTAL_SCORE: float = float(os.getenv("MIN_VISUAL_TOTAL_SCORE", "0.78"))

# Chốt chặn 2: Output Lip-Sync Gate (`OutputScoreEvaluator`)
MIN_SYNCNET_LSE_C: float = float(os.getenv("MIN_SYNCNET_LSE_C", "5.0"))
MAX_SYNCNET_LSE_D: float = float(os.getenv("MAX_SYNCNET_LSE_D", "7.5"))
MIN_MOUTH_SHARPNESS: float = float(os.getenv("MIN_MOUTH_SHARPNESS", "0.70"))
MAX_BBOX_JITTER_PX: float = float(os.getenv("MAX_BBOX_JITTER_PX", "1.8"))
MIN_OUTPUT_TOTAL_SCORE: float = float(os.getenv("MIN_OUTPUT_TOTAL_SCORE", "0.80"))

# Cấu hình Wav2Lip & TikTok Content Posting API v2
WAV2LIP_PADS: List[int] = [int(x) for x in os.getenv("WAV2LIP_PADS", "0,15,0,0").split(",")]
WAV2LIP_BATCH_SIZE: int = int(os.getenv("WAV2LIP_BATCH_SIZE", "32"))
TIKTOK_ACCESS_TOKEN: str = os.getenv("TIKTOK_ACCESS_TOKEN", "").strip()
TIKTOK_RETRY_QUEUE_DB: Path = _resolve_path("TIKTOK_RETRY_QUEUE_DB", "./workspace/tiktok_retry_queue.sqlite")

FORBIDDEN_MODERN_TERMS: List[str] = []
CHARACTER_ALIASES: Dict[str, List[str]] = {}
CANONICAL_VISUAL_TRAITS: Dict[str, str] = {}

for _dir in [
    ASSETS_DIR / "avatars",
    ASSETS_DIR / "b_rolls",
    ASSETS_DIR / "fonts",
    CONTINUITY_STATE_DIR,
    WORKSPACE_DIR,
]:
    _dir.mkdir(parents=True, exist_ok=True)
