# 🎬 CẨM NANG SẢN XUẤT VIDEO TỰ ĐỘNG CHUẨN TIKTOK / SHORTS TRIỆU VIEW

> Hệ thống hỗ trợ 3 mô hình sản xuất nội dung hàng đầu hiện nay:
> 1. **Video Dài 3 Phút – 5 Phút B-Roll Tư Liệu Tự Động (Chuẩn @vanthanhthu09)**: Tự động LLM viết kịch bản dài 3p–5p, tự động tìm và tải video tư liệu 4K phù hợp trên mạng hoặc nhận video có sẵn, tự động cắt ghép 3-5s, lồng tiếng và kiểm duyệt khung hình sạch 100%. **Chi phí 0 credit AI, thuần Python tốc độ cao**.
> 2. **Nhân Bản Giọng Đọc Offline Tiếng Việt F5-TTS**: Sử dụng giọng mẫu mộc từ file `workspace/voice-preview.mp3`, nhả chữ từ tốn 0.68x (~175 từ/phút), hòa âm chuẩn -14 LUFS với nhạc nền Auto-Ducking.
> 3. **Quy Trình Tri Thức Sách Hằng Ngày (Book RAG Hybrid)**: Tự động nạp sách (.epub, .pdf, .txt), khai thác góc kể và xuất bản chuỗi video đều đặn mỗi ngày.

---

## 🏛️ PHẦN 1: VIDEO DÀI 3P - 5P B-ROLL TỰ ĐỘNG (CHUẨN KÊNH @VANTHANHTHU09)

Mô hình sản xuất video tài liệu khám phá, khoa học, bí ẩn dài 3 đến 5 phút (hoặc tùy ý 1–10 phút) giống hệt các kênh tài liệu triệu view:
- **Tự động viết kịch bản dài**: LLM tính toán chính xác số từ (~135 từ/phút ở tốc độ tự nhiên 1.15x cho video dài hoặc ~175 từ/phút ở tốc độ 0.68x của giọng Clone), chia thành 10–22 phân đoạn lôi cuốn, giọng đọc tròn vành rõ chữ, không bị vội hay méo tiếng.
- **Tự động tìm & tải B-roll 4K**: Hệ thống tự động dịch từ khóa sang tiếng Anh và dùng `yt-dlp` kéo các thước phim tư liệu sắc nét từ YouTube về máy.
- **Hỗ trợ video có sẵn**: Nếu bạn đã có sẵn video tư liệu, chỉ cần đưa đường dẫn vào `--footage <file_hoặc_thư_mục>`.
- **Dựng phim tự động**: Cắt thành các nhịp 3s–5s đan xen, phủ kín 100% thời lượng audio, tự động căn tỉ lệ 9:16 (TikTok) hoặc 16:9 (YouTube).
- **Kiểm duyệt khung hình sạch 100%**: Tự động phát hiện và loại bỏ cảnh tối hoặc cảnh dính phụ đề gốc từ YouTube qua `_is_cut_usable`.
- **Âm thanh Studio Chống Méo Tiếng**:
  + Tự động tối ưu nhịp đọc 1.15x cho video dài 3–5 phút (người dùng vẫn có thể chỉnh qua `--speed` nếu muốn).
  + Khử triệt để lỗi Gibbs/Aliasing của FFT resample, giữ nguyên độ phân giải 24.000 Hz chuẩn studio.
  + Nhạc nền lặp vô tận có Cross-fade 1.5s, không còn tiếng nổ click/pop tại điểm giao bài.
  + Chuẩn hóa âm lượng `-14 LUFS (linear)` loại bỏ hoàn toàn hiện tượng nghẹt tiếng/bơm xả (pumping).
- **Thuần Python (Zero Graph Libraries)**: Tuyệt đối không dùng các thư viện pipeline vẽ đồ thị phức tạp.

### Cách chạy:
```bash
# Trên Windows PowerShell / Command Prompt:
python main.py --broll "Bí mật bên dưới Kim Tự Tháp Giza" --duration 3
python main.py --broll "Bí ẩn bãi đá Stonehenge" --duration 5

# Hoặc dùng file bat tiện lợi trên Windows:
.\run.bat --broll "Bí mật bên dưới Kim Tự Tháp Giza" --duration 3

# Trên Linux / MacOS / Git Bash:
./run.sh --broll "Bí ẩn bãi đá Stonehenge" --duration 5

# 2. Làm video 3.2 phút với giọng Clone tiếng Việt:
./run.sh --broll "Bí mật lăng mộ Tần Thủy Hoàng" --duration 3.2 --voice clone

# 3. Sử dụng video tư liệu có sẵn của bạn:
./run.sh --broll "Bí ẩn Stonehenge" --duration 5 --footage /duong/dan/video_stonehenge.mp4

# 4. Sử dụng kịch bản JSON đã soạn sẵn:
./run.sh --broll "Lăng mộ Tần Thủy Hoàng" --duration 3 --script-file workspace/script_tan_thuy_hoang_3min.json

# 5. Xuất video ngang 16:9 cho YouTube:
./run.sh --broll "Hố đen vũ trụ" --duration 5 --aspect 16:9
```

---

## 🎙️ PHẦN 2: HƯỚNG DẪN GIỌNG ĐỌC & VOICE CLONE TIẾNG VIỆT

### 1. Giọng Clone F5-TTS Cục Bộ (Miễn phí 100% - Khuyên dùng):
Chạy hoàn toàn trên máy local từ file mẫu [workspace/voice-preview.mp3](file:///home/blue/Downloads/Projects/wav2video/workspace/voice-preview.mp3):
```bash
./run.sh --broll "Bí ẩn lăng mộ Tần Thủy Hoàng" --duration 3 --voice clone
```

### 2. Các giọng đọc Edge-TTS trực tuyến theo phong cách TikTok:
```bash
# Giọng Nam Khoa học Vũ trụ (Chuẩn vanthanhthu09 - 1.34x dứt khoát):
./run.sh --voice vanthanhthu "Chủ đề..."

# Giọng Nữ Review Phim / Drama (1.40x dồn nhịp, ngắt punchy):
./run.sh --voice review_phim "Chủ đề..."

# Giọng Nữ Gen Z tươi sáng, bắt trend:
./run.sh --voice gen_z "Chủ đề..."

# Giọng Nam Kể Chuyện Giật Gân (bí ẩn, tài liệu kịch tính):
./run.sh --voice giat_gan "Chủ đề..."

# Giọng Nam Review hiện đại (tài chính, kinh tế, công nghệ):
./run.sh --voice nam_review "Chủ đề..."
```

---

## 📚 PHẦN 3: BIẾN SÁCH THÀNH VIDEO HẰNG NGÀY (BOOK RAG)

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

## 🎵 BẢN NHẠC NỀN & CHẤT LƯỢNG ÂM THANH
- **Nhạc nền:** Tích hợp các bản beat điện ảnh huyền bí bản quyền sạch, hòa âm chuẩn studio.
- **Âm lượng:** Auto-Ducking tự động hạ âm lượng BGM khi có giọng đọc và ngân lên khi hết câu, chuẩn hóa `-14 LUFS` của TikTok.
- **Giọng nữ & nam Edge-TTS:** Đã được lọc qua chuỗi Studio EQ (`atempo=...`, `equalizer=180Hz/3200Hz`), loại bỏ hoàn toàn hiện tượng giọng đọc Google Translate đơ cứng.
