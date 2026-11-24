<div align="center">

# 🎬 wav2video

### Hệ Thống Tự Động Sản Xuất Phim Tài Liệu & Video B-Roll Dọc 9:16 Chuẩn TikTok / Shorts

**Biến một chủ đề tự do, file cấu hình kịch bản (`.json`), hoặc cả cuốn sách (`.epub` / `.txt` / `.docx` / `.pdf`) thành video tài liệu ngắn dọc 9:16 hoàn chỉnh — tự động biên kịch điện ảnh, nhân bản giọng nói Offline tiếng Việt F5-TTS, cắt ghép B-Roll thông minh và xuất bản đa nền tảng.**

---

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Video Engine](https://img.shields.io/badge/Video%20Engine-FFmpeg%209%3A16%2030fps-007808?style=for-the-badge&logo=ffmpeg&logoColor=white)](https://ffmpeg.org/)
[![Voice Clone](https://img.shields.io/badge/Voice%20Clone-F5--TTS%20Vietnamese-FF6F00?style=for-the-badge)](https://github.com/SWivid/F5-TTS)
[![LLM Engine](https://img.shields.io/badge/LLM-Google%20Gemini%20Thinking-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![Local RAG](https://img.shields.io/badge/Local%20RAG-multilingual--e5--small%20%2B%20FTS5-0F766E?style=for-the-badge)](https://huggingface.co/intfloat/multilingual-e5-small)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

<sub>
<a href="#-video-demo--kết-quả-mẫu-showcase"><b>Live Demo</b></a> ·
<a href="#-quick-start-khởi-chạy-nhanh"><b>Quick Start</b></a> ·
<a href="#-cấu-hình-kịch-bản-declarative-config"><b>Config Guide</b></a> ·
<a href="#-hướng-dẫn-sử-dụng-chi-tiết-usage"><b>Usage</b></a> ·
<a href="#-star-history"><b>Star History</b></a>
</sub>

</div>

---

## 📖 Mục Lục (Table of Contents)

- [Giới Thiệu Dự Án](#-giới-thiệu-dự-án)
- [Video Demo & Kết Quả Mẫu (Showcase)](#-video-demo--kết-quả-mẫu-showcase)
- [Điểm Khác Biệt Cốt Lõi](#-điểm-khác-biệt-cốt-lõi)
- [3 Trụ Cột Sản Xuất Chính](#-3-trụ-cột-sản-xuất-chính)
- [Quick Start (Khởi Chạy Nhanh)](#-quick-start-khởi-chạy-nhanh)
- [Cấu Hình Kịch Bản (Declarative Config)](#-cấu-hình-kịch-bản-declarative-config)
- [Công Nghệ Sử Dụng (Tech Stack)](#-công-nghệ-sử-dụng-tech-stack)
- [Yêu Cầu Hệ Thống (Prerequisites)](#-yêu-cầu-hệ-thống-prerequisites)
- [Cài Đặt & Khởi Chạy (Installation)](#-cài-đặt--khởi-chạy-installation)
- [Cấu Hình Biến Môi Trường (.env)](#-cấu-hình-biến-môi-trường-env)
- [Hướng Dẫn Sử Dụng Chi Tiết (Usage)](#-hướng-dẫn-sử-dụng-chi-tiết-usage)
  - [1. Phim Tài Liệu B-Roll Dài 3–5 Phút Tự Động](#1-phim-tài-liệu-b-roll-dài-35-phút-tự-động-chuẩn-vanthanhthu09)
  - [2. Tự Động Nhân Bản Giọng Đọc Offline (F5-TTS Clone)](#2-tự-động-nhân-bản-giọng-đọc-offline-f5-tts-vietnamese)
  - [3. Biến Sách Thành Chuỗi Video Hằng Ngày (Book RAG)](#3-quy-trình-làm-video-hằng-ngày-từ-sách-book-rag)
  - [4. Bán Tự Động Với Google Flow (4 Block Liền Mạch)](#4-luồng-bán-tự-động-với-google-flow-4-block-liền-mạch)
  - [5. Bảng Tra Cứu Giọng Đọc TikTok Trendy](#5-bảng-tra-cứu-giọng-đọc-tiktok-trendy)
- [Cấu Trúc Thư Mục Dự Án (Project Structure)](#-cấu-trúc-thư-mục-dự-án-project-structure)
- [Xử Lý Sự Cố Thường Gặp (Troubleshooting & FAQ)](#-xử-lý-sự-cố-thường-gặp-troubleshooting--faq)
- [Lộ Trình Phát Triển (Roadmap)](#-lộ-trình-phát-triển-roadmap)
- [Star History](#-star-history)
- [Đóng Góp & Giấy Phép (Contributing & License)](#-đóng-góp--giấy-phép-contributing--license)

---

## 💡 Giới Thiệu Dự Án

**`wav2video`** ra đời nhằm giải quyết bài toán cốt lõi của các nhà sáng tạo nội dung dạng ngắn: **Làm thế nào để sản xuất video tài liệu, khoa học, khám phá bí ẩn chất lượng điện ảnh với chi phí 0 đồng, không dính bản quyền và hoàn toàn tự động?**

Thay vì tạo ra những video *"ghép slide ảnh vô hồn, giọng đọc Google Translate đơ cứng, hình ảnh một đằng – tiếng một nẻo"*, `wav2video` áp dụng tư duy của một **Đạo diễn Phim Tài liệu Ngắn**:
- Soạn kịch bản theo nhịp kể lôi cuốn, có cao trào, thắt nút (Hook 3s đầu).
- Cắt dựng video tư liệu (B-Roll) theo nhịp 3s–5s chuyển cảnh linh hoạt.
- Tự động kiểm duyệt khung hình sạch, chống dính chữ/phụ đề gốc từ video tư liệu.
- Giọng đọc trầm ấm tự nhiên với F5-TTS tiếng Việt chạy Offline 100% trên CPU hoặc Edge-TTS studio.

---

## 🎥 Video Demo & Kết Quả Mẫu (Showcase)

Sau mỗi lượt render, hệ thống xuất ra các tệp tin độc lập phục vụ nhu cầu đăng ngay hoặc hậu kỳ thêm:

| Tệp tin | Định dạng | Công dụng chính |
| :--- | :---: | :--- |
| 🎬 **`final_master.mp4`** | 1080×1920 (9:16) | Video hoàn thiện có sẵn giọng đọc + nhạc nền Auto-Ducking + cắt dựng B-Roll nhịp 3s-5s |
| 🎙️ **`audio_16k_mono.wav`** | PCM 16kHz Mono | Bản thu giọng đọc studio chuẩn `-14 LUFS` kèm nhạc nền bản quyền sạch |
| 📄 **`subtitles.ass`** | ASS / Karaoke | Phụ đề đồng bộ từng từ, căn Safe-Zone tránh UI TikTok |
| 📋 **`scene_timeline.json`** | JSON Timeline | Toàn bộ mốc thời gian, lời thoại từng phân đoạn và từ khóa footage |

> 📺 **Xem video demo sản phẩm thực tế:**  
> 👉 [**▶️ Xem Video Demo trên YouTube Shorts**](https://youtube.com/shorts/LUAgRhPBONg)  
> *(Ghé thăm kho video mẫu được tạo tự động bởi `wav2video` tại kênh tác giả)*

---

## ✨ Điểm Khác Biệt Cốt Lõi

* ⚡ **Zero Graph Overhead (Thuần Python Tối Ưu)**: Thực thi trực tiếp không phụ thuộc các framework đồ thị cồng kềnh, tối ưu tốc độ và độ ổn định khi xuất file.
* 🎛️ **Giao Diện Cấu Hình Độc Lập (Không Cần Bật Web UI)**: Bạn có thể chạy tự động 1 lệnh hoặc tự điều khiển 100% từng phân đoạn, từ khóa footage và lời đọc qua file cấu hình `script.json`.
* 🎙️ **Offline Vietnamese Voice Clone (F5-TTS)**: Nhân bản giọng nói bất kỳ từ file mẫu `.mp3`, giữ nguyên ngữ điệu tiếng Việt, tự động chuẩn hóa tốc độ `0.68x` (~175 từ/phút) chuẩn phim tài liệu, 0đ chi phí API.
* 🛡️ **Kiểm Duyệt Khung Hình Sạch 100%**: Thuật toán `_is_cut_usable` tự động phát hiện và loại bỏ các cảnh bị tối đen hoặc có chữ phụ đề/ticker dính từ video tư liệu YouTube.
* 🎚️ **Chuẩn Âm Thanh Studio `-14 LUFS` & Auto-Ducking**: Tự động hạ âm lượng nhạc nền xuống khi có giọng đọc và đẩy ngân vang khi ngắt nghỉ câu thoại, khóa mức trần `0.89` tránh rè vỡ tiếng.
* 📚 **Book RAG Local 0-Token**: Nạp toàn bộ sách vào SQLite, nhúng vector bằng `intfloat/multilingual-e5-small` kết hợp FTS5 BM25. Chấm điểm độ bám sát (Groundedness) bằng Vector Cosine trên CPU (0 token LLM).
* 🌊 **Quy Trình Google Flow 4-Block**: Tự động chia kịch bản thành 4 Block cân bằng thời lượng kèm câu nối liền mạch (*seamless continuation*) cho Google Flow / Veo.

---

## 🏛️ 3 Trụ Cột Sản Xuất Chính

```
                           ┌────────────────────────────────────────────────────────┐
                           │                      wav2video                         │
                           └──────────────────────────┬─────────────────────────────┘
                                                      │
         ┌────────────────────────────────────────────┼────────────────────────────────────────────┐
         │                                            │                                            │
         ▼                                            ▼                                            ▼
 1. B-Roll Phim Dài 3–5 Phút                  2. F5-TTS Voice Clone                     3. Book RAG Shorts
  (Chuẩn kênh @vanthanhthu09)                  (Nhân bản giọng Offline)                  (Sách -> Video ngày)
  • Kịch bản 10-22 đoạn tự động                • Mẫu từ voice-preview.mp3                • Nạp .epub / .pdf / .txt
  • Tự tải footage 4K qua yt-dlp               • Tách câu đơn tự nhiên                   • Hybrid Search BM25 + E5
  • Cắt ghép nhịp 3-5s đan xen                 • Tốc độ 0.68x trầm ấm                    • Khai thác 4-6 góc kể
  • Khung hình sạch 100% không chữ             • Chi phí 0đ API (chạy CPU)               • Tự động bốc hàng đợi
```

---

## 🚀 Quick Start (Khởi Chạy Nhanh)

Bạn có thể chạy `wav2video` theo 2 phong cách tùy vào mục đích:

<table>
<tr>
<td valign="top" width="50%">

### 🤖 Cách 1: Tự động hoàn toàn (AI-Driven)
*Chỉ cần cung cấp 1 chủ đề, AI tự viết kịch bản, tự tìm B-roll và render từ A-Z.*

```bash
# Trên Linux / macOS:
./run.sh --broll "Bí mật lăng mộ Tần Thủy Hoàng" --duration 3

# Trên Windows (PowerShell / CMD):
.\run.bat --broll "Bí mật lăng mộ Tần Thủy Hoàng" --duration 3
```

</td>
<td valign="top" width="50%">

### 📄 Cách 2: Tùy biến bằng File Cấu Hình (Config-Driven)
*Toàn quyền kiểm soát từng câu thuyết minh và từ khóa tìm kiếm B-roll, không cần mở Web.*

```bash
# Trên Linux / macOS:
./run.sh --broll "Lăng mộ" --script-file workspace/script_sample.json

# Trên Windows (PowerShell / CMD):
.\run.bat --broll "Lăng mộ" --script-file workspace/script_sample.json
```

</td>
</tr>
</table>

---

## ⚙️ Cấu Hình Kịch Bản (Declarative Config)

Không cần cài đặt hay duy trì một Web UI phức tạp, bạn có thể chỉnh sửa trực tiếp file cấu hình kịch bản JSON (`workspace/script_sample.json`). Pipeline sẽ đọc và render chính xác theo từng phân đoạn đã định sẵn.

<details open>
<summary><b>📄 Cấu trúc file <code>workspace/script_sample.json</code></b></summary>

<br/>

```json
{
  "title": "Bí mật bên dưới Lăng mộ Tần Thủy Hoàng",
  "topic": "Lăng mộ Tần Thủy Hoàng",
  "duration_mins": 3.0,
  "broll_search_queries": [
    "Qin Shi Huang mausoleum terracotta army 4k documentary",
    "ancient chinese underground palace cinematic b-roll",
    "terracotta warriors excavation cinematic 4k"
  ],
  "sections": [
    {
      "section_id": 1,
      "narration_vn": "Năm một nghìn chín trăm bảy mươi tư, khi nhóm nông dân tại Tây An đào giếng tìm nước, họ không hề biết mình vừa chạm vào cánh cổng của một trong những bí mật lớn nhất lịch sử nhân loại.",
      "visual_description": "Cảnh flycam sa mạc và khu khai quật lăng mộ cổ đại Tây An"
    },
    {
      "section_id": 2,
      "narration_vn": "Dưới lớp đất sâu hơn ba mươi mét là đội quân đất nung hơn tám nghìn chiến binh, mỗi gương mặt mang một biểu cảm độc nhất vô nhị, như thể một đạo quân sống bị hóa đá trong chớp mắt.",
      "visual_description": "Cận cảnh các tượng binh mã dũng đất nung trang nghiêm trong ánh sáng mờ ảo"
    },
    {
      "section_id": 3,
      "narration_vn": "Hàng trăm tấn thủy ngân lỏng được bố trí mô phỏng mạng lưới sông ngòi và biển cả, tạo nên một nồng độ độc chất chết người bao bọc vĩnh hằng giấc ngủ của vị hoàng đế đầu tiên.",
      "visual_description": "Dòng chảy thủy ngân phát sáng ma mị trong hầm mộ ngầm"
    }
  ]
}
```

#### Giải thích các trường:
* **`title` / `topic`**: Tiêu đề và chủ đề của video tài liệu.
* **`broll_search_queries`**: Danh sách 2–5 từ khóa tiếng Anh chất lượng cao để `yt-dlp` tự động kéo footage 4K/1080p về máy.
* **`sections`**: Danh sách các phân đoạn. Mỗi phân đoạn gồm:
  - `narration_vn`: Lời đọc tiếng Việt (đã chuẩn hóa số thành chữ để TTS đọc tròn vành rõ chữ).
  - `visual_description`: Gợi ý nội dung cảnh hình ảnh tương ứng.

</details>

---

## 🛠️ Công Nghệ Sử Dụng (Tech Stack)

| Hạng mục | Công nghệ / Thư viện | Vai trò |
|---|---|---|
| **Ngôn ngữ** | Python 3.10+ | Lõi xử lý logic toàn bộ pipeline |
| **Xử lý Video & Audio** | FFmpeg (qua `imageio_ffmpeg`) | Cắt, crop 9:16, rescale, cross-fade, mix audio, burn sub |
| **Trí tuệ nhân tạo (LLM)** | Google Gemini (Cascade / Thinking) | Soạn kịch bản, chấm điểm biên tập, gợi ý từ khóa B-roll |
| **Voice Clone Offline** | F5-TTS (DiT + Vocos 24kHz) | Nhân bản giọng đọc tiếng Việt mộc tự nhiên từ file mẫu |
| **Cloud TTS (Fallback)** | Edge-TTS / gTTS | 10+ phong cách giọng đọc TikTok trendy (Hoài My, Nam Minh...) |
| **Vector RAG & Search** | `multilingual-e5-small` + SQLite FTS5 | Nhúng vector & tìm kiếm lai tri thức sách nội bộ |
| **Tải tư liệu tự động** | `yt-dlp` | Tự động tìm và tải footage 4K/1080p từ YouTube theo từ khóa |
| **Đánh giá hình ảnh** | OpenAI CLIP ViT-B/32 | Chấm điểm khớp ngữ nghĩa ảnh tư liệu 0-token trên CPU |

---

## 📋 Yêu Cầu Hệ Thống (Prerequisites)

* **Hệ điều hành:** Linux (Ubuntu 20.04+, Debian), macOS hoặc Windows (CMD / PowerShell / WSL).
* **Python:** Phiên bản `3.10` trở lên.
* **FFmpeg:** Đã tích hợp sẵn binary qua package `imageio-ffmpeg` (không bắt buộc cài ngoài).
* **RAM:** Tối thiểu 8 GB (khuyến nghị 16 GB để chạy model F5-TTS mượt mà).
* **Dung lượng ổ cứng:** Trống tối thiểu 5 GB cho model F5-TTS và thư viện đệm.

---

## 🚀 Cài Đặt & Khởi Chạy (Installation)

### 1. Tải mã nguồn về máy:
```bash
git clone https://github.com/dungna13/wav2video.git
cd wav2video
```

### 2. Thiết lập môi trường ảo Python:
```bash
# Tạo môi trường ảo
python3 -m venv .venv

# Kích hoạt môi trường ảo:
# Trên Linux / macOS:
source .venv/bin/activate
# Trên Windows PowerShell:
.venv\Scripts\Activate.ps1
# Trên Windows CMD:
.venv\Scripts\activate.bat

# Cài đặt thư viện:
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Cấu hình quyền thực thi (Linux/macOS):
```bash
chmod +x run.sh
```

---

## 🔐 Cấu Hình Biến Môi Trường (.env)

Tạo file `.env` từ file mẫu:
```bash
cp .env.example .env
```

Mở `.env` và điền khóa API của bạn:
```env
# Google Gemini API Key (Bắt buộc để LLM viết kịch bản)
GEMINI_API_KEY="AIzaSy..."
GEMINI_MODEL="gemini-3.1-flash-lite-preview"

# API Footage Stock ngoài (Tùy chọn, hệ thống có sẵn YouTube/Mixkit tự động)
PEXELS_API_KEY=""
PIXABAY_API_KEY=""
```

> [!IMPORTANT]
> **Bảo mật**: File `.env` chứa API Key đã được khai báo trong `.gitignore`. Tuyệt đối không commit file này lên GitHub.

---

## 📖 Hướng Dẫn Sử Dụng Chi Tiết (Usage)

### 1. Phim Tài Liệu B-Roll Dài 3–5 Phút Tự Động (Chuẩn @vanthanhthu09)

Hệ thống tự động biên soạn kịch bản dài, tính toán đúng số từ (~135–155 từ/phút), tự tải footage 4K, cắt nhịp 3s–5s và lồng tiếng:

```bash
# 1. Tự động từ A-Z với kịch bản 5 phút:
./run.sh --broll "Bí ẩn bãi đá Stonehenge" --duration 5

# 2. Làm video 3.2 phút với giọng Clone tiếng Việt:
./run.sh --broll "Bí mật lăng mộ Tần Thủy Hoàng" --duration 3.2 --voice clone

# 3. Sử dụng video tư liệu có sẵn của bạn:
./run.sh --broll "Bí ẩn Stonehenge" --duration 5 --footage /duong/dan/thu_muc_video/

# 4. Sử dụng file cấu hình kịch bản JSON có sẵn:
./run.sh --broll "Lăng mộ Tần Thủy Hoàng" --duration 3 --script-file workspace/script_sample.json

# 5. Xuất video khổ ngang 16:9 cho YouTube:
./run.sh --broll "Hố đen vũ trụ" --duration 5 --aspect 16:9
```

*(Trên Windows, bạn có thể thay thế `./run.sh` bằng `.\run.bat` hoặc `python main.py`)*

---

### 2. Tự Động Nhân Bản Giọng Đọc Offline (F5-TTS Vietnamese)

Sử dụng trực tiếp giọng nói từ file mẫu [workspace/voice-preview.mp3](file:///workspace/voice-preview.mp3) mà không tốn bất kỳ chi phí API nào:

```bash
# Thêm cờ --voice clone vào lệnh chạy B-roll:
./run.sh --broll "Bí ẩn đáy biển Mariana" --duration 3 --voice clone
```

**Cơ chế tối ưu hóa giọng đọc độc quyền trong `wav2video`:**
* **Tách câu đơn tự nhiên**: Không dồn cả đoạn dài vào model làm một lượt; hệ thống tách theo dấu câu, gọi `infer_process` đơn lẻ giữ cao độ chuẩn `264–266 Hz`.
* **Khóa tốc độ `0.68x`**: Bù trừ độ dồn dập của giọng mẫu, tạo nhịp đọc từ tốn (~175 từ/phút), chuẩn truyền cảm của phim tài liệu.
* **Auto-Ducking**: Nhạc nền ngân vang khi ngắt câu và tự hạ xuống khi có tiếng người.

---

### 3. Quy Trình Làm Video Hằng Ngày Từ Sách (Book RAG)

Biến một cuốn sách dày thành chuỗi video TikTok đều đặn mỗi ngày:

```bash
# Bước 1: Nạp sách vào cơ sở dữ liệu (tự tách chương, nhúng vector 0-token):
./run.sh --ingest NhaGiaKim.epub

# Bước 2: Xem toàn bộ danh sách chương và trạng thái hoàn thành:
./run.sh --list-book nha_gia_kim

# Bước 3: Chế độ ĐĂNG HẰNG NGÀY — tự lấy chương tiếp theo, render video & lưu DONE:
./run.sh --book nha_gia_kim --daily

# Bước 4: Khai thác 4 góc nhìn sắc bén từ 1 chương bất kỳ:
./run.sh --mine nha_gia_kim --chunk 14
```

---

### 4. Luồng Bán Tự Động Với Google Flow (4 Block Liền Mạch)

```bash
# Bước 1: Sinh 4 block prompt liền mạch & audio thuyết minh:
./run.sh --flow-prep "Bí ẩn sa mạc Sahara từng là rừng xanh"

# Bước 2: Tải các clip từ Google Flow về thư mục flow_clips/

# Bước 3: Dựng thành phẩm hoàn chỉnh:
./run.sh --flow-render "workspace/flow_Sahara_..."
```

---

### 5. Bảng Tra Cứu Giọng Đọc TikTok Trendy

| Mã giọng (`--voice`) | Giới tính / Phong cách | Tốc độ | Đặc điểm |
|---|---|---|---|
| `vanthanhthu` | Nam Trầm Điện Ảnh ⭐ | 1.34x (hoặc 1.15x cho video dài) | Chuẩn phong cách kênh khoa học vũ trụ triệu view |
| `clone` | Offline F5-TTS Clone 🔥 | 0.68x | Giọng clone từ `voice-preview.mp3`, nhả chữ từ tốn |
| `review_phim` | Nữ Review Phim | 1.40x | Dồn dập, ngắt nhịp punchy cực cuốn hút drama |
| `gen_z` | Nữ Gen Z | 1.35x | Tươi sáng, bắt trend giới trẻ |
| `giat_gan` | Nam Giật Gân | 1.35x | Kịch tính, bí ẩn, dẫn dắt câu chuyện giật tít |
| `nam_review` | Nam Hiện Đại | 1.40x | Nhanh, dứt khoát, chuyên tài chính & công nghệ |

---

## 📁 Cấu Trúc Thư Mục Dự Án (Project Structure)

```text
wav2video/
├── main.py                         # Điểm vào chính của ứng dụng CLI
├── run.sh                          # Runner script tự động liên kết môi trường ảo trên Linux/macOS
├── run.bat                         # Runner script tiện lợi trên Windows Command Prompt
├── run.ps1                         # Runner script tiện lợi trên Windows PowerShell
├── HUONG_DAN_SU_DUNG.md            # Tài liệu cẩm nang sản xuất chi tiết
├── config/
│   └── settings.py                 # Nạp cấu hình từ .env, FPS, thông số 9:16
├── graph/
│   ├── broll_director.py           # Pipeline B-roll tài liệu dài (Zero Graph Library)
│   ├── voice_clone_vietnamese.py   # Mô-đun F5-TTS nhân bản giọng tiếng Việt cục bộ
│   ├── audio_sync.py               # Hòa âm Studio, Auto-Ducking BGM, LUFS -14
│   ├── book_rag.py                 # Bộ xử lý sách (.epub/.pdf) & Hybrid Search
│   ├── flow_bundler.py             # Bộ điều phối chia Block cho Google Flow
│   └── video_renderer.py           # Bộ dựng phim FFmpeg 9:16 nâng cao
├── models/
│   └── f5tts_vi/
│       ├── vocab.txt               # Từ điển phát âm tiếng Việt cho F5-TTS
│       └── model_latest.safetensors# (Trọng số model F5-TTS - lưu cục bộ)
├── assets/
│   └── bgm/                        # Nhạc nền điện ảnh bản quyền sạch
└── workspace/                      # Thư mục lưu trữ video thành phẩm & dữ liệu tạm
    ├── voice-preview.mp3           # File audio giọng mẫu để clone (Không xóa)
    ├── script_sample.json          # File mẫu cấu hình kịch bản B-Roll
    └── logs/                       # Log chi tiết các lần chạy
```

---

## ❓ Xử Lý Sự Cố Thường Gặp (Troubleshooting & FAQ)

### Q1: Tại sao video tạo ra lại có chữ/phụ đề lạ ở góc dưới?
> **Nguyên nhân**: Video tư liệu tải từ YouTube có thể bị gắn cứng phụ đề tin tức từ video gốc.  
> **Giải pháp**: Hệ thống đã tích hợp thuật toán `_is_cut_usable` tự động phát hiện mật độ chữ trắng ở đáy khung hình để bỏ qua các đoạn này. Đồng thời, bạn có thể truyền video tư liệu sạch của riêng bạn qua tham số `--footage <đường_dẫn>`.

### Q2: Giọng Clone F5-TTS trên CPU chạy mất bao lâu?
> Model chạy hoàn toàn bằng CPU đa nhân (12 threads). Với đoạn kịch bản 3 phút (khoảng 500 từ), quá trình tổng hợp câu đơn mất khoảng **15–20 phút** nhưng đổi lại chất lượng âm thanh dày dặn, không tốn credit AI và không phụ thuộc kết nối mạng.

### Q3: Làm sao để tắt hẳn phụ đề chữ chạy trên video?
> Mặc định hệ thống đã đặt chế độ phụ đề là `none`. Video xuất ra sẽ hoàn toàn sạch sẽ, thuận tiện để bạn tự thêm caption bằng CapCut hoặc TikTok Editor.

---

## 🗺️ Lộ Trình Phát Triển (Roadmap)

- [x] **Phase 1: Pure-Python B-Roll Engine** — Dựng phim 3–5 phút tự động, cắt nhịp 3s–5s, auto-ducking BGM.
- [x] **Phase 2: Local Vietnamese F5-TTS** — Tích hợp nhân bản giọng tiếng Việt với nhịp đọc tài liệu `0.68x`.
- [x] **Phase 3: Clean B-Roll Guard** — Lọc tự động cảnh tối và cảnh dính phụ đề gốc.
- [x] **Phase 4: Book RAG Daily Pipeline** — Tự động hóa sản xuất video từ sách với Hybrid Search BM25 + Vector.
- [x] **Phase 5: Declarative Script Config** — Hỗ trợ file cấu hình kịch bản JSON (`script_sample.json`) không cần Web UI.
- [ ] **Phase 6: Multi-voice Dialogue** — Hỗ trợ 2 nhân vật đối thoại luân phiên trong cùng 1 video.

---

## ⭐ Star History

<div align="center">

<a href="https://star-history.com/#dungna13/wav2video&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=dungna13/wav2video&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=dungna13/wav2video&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=dungna13/wav2video&type=Date" />
 </picture>
</a>

</div>

---

## 🤝 Đóng Góp & Giấy Phép (Contributing & License)

Mọi đóng góp, báo lỗi (Issues) hoặc yêu cầu tính năng mới (Pull Requests) đều được chào đón!

Dự án được phân phối dưới giấy phép **MIT License**. Xem chi tiết tại file [LICENSE](LICENSE).

<div align="center">
  <b>Phát triển với sự tận tâm dành cho cộng đồng Content Creator & Developer Việt Nam 🇻🇳</b>
</div>
