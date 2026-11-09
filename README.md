# wav2video

Hệ thống **Topic-to-Video Agentic Pipeline (LangGraph + 3D AI Storyboard Animation + Local VITS Neural Vietnamese TTS)** tự động lên kịch bản từ A–Z, tự thiết kế Nhân vật & 4 Phân cảnh Hoạt hình 3D, sinh giọng đọc Nam Neural VITS Tiếng Việt (`facebook/mms-tts-vie`) kèm nhạc nền Ambient Auto-Ducking và tự động chấm điểm kiểm định 3 tầng (`Script QA Score`, `Visual Feature Gate 1`, `Output SyncNet Gate 2`).

## Cài đặt

```bash
pip install -r requirements.txt
cp .env.example .env
```

## Cách chạy trên Terminal

```bash
python -X utf8 -u main.py "Hiệu ứng cánh bướm và lý thuyết hỗn loạn trong cuộc sống"
```
