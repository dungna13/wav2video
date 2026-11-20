# 🎬 HƯỚNG DẪN SẢN XUẤT VIDEO TỰ ĐỘNG CHUẨN TIKTOK TRIỆU VIEW

> Hệ thống hỗ trợ 3 mô hình sản xuất nội dung hàng đầu hiện nay:
> 1. **Video Dài 3 Phút – 5 Phút B-Roll Tư Liệu Tự Động (Chuẩn @vanthanhthu09)**: Tự động LLM viết kịch bản dài 5p/3p, tự động tìm và tải video tư liệu 4K phù hợp trên mạng hoặc nhận video có sẵn, tự động cắt ghép 3-5s và lồng tiếng + phụ đề TikTok. **Chi phí 0 credit AI, không dùng thư viện pipeline đồ thị phức tạp**.
> 2. **Hoạt Hình Người Que Lịch Sử (Historical Stickman)**: Chuẩn tài liệu `Historical_Stickman_Video_Instructions.docx` (4-6 cảnh x 8-10s, Character Sheet, Veo/Omni prompts, BGM dồn dập).
> 3. **Điện Ảnh B-Roll Ngắn 30s-60s (Web Cinematic Auto)**: Tự động tải video thật HD từ web, ghép lồng giọng đọc và nhạc nền xuất file ngay.

---

## ⚔️ PHẦN 1: HOẠT HÌNH NGƯỜI QUE LỊCH SỬ (HISTORICAL STICKMAN 60S)

Chuẩn 100% khung chỉ dẫn sản xuất chuyên nghiệp:
- **Thời lượng:** Chuẩn 60 giây (6 clips x 10 giây). Tỷ lệ 9:16 dọc.
- **Kịch bản:** 18–24 từ/cảnh. Hook kịch tính 2s đầu tiên, twist ở cảnh 4, cao trào cảnh 5, kết luận sâu sắc cảnh 6.
- **Tính nhất quán nhân vật (Character Consistency):** Tự động sinh bảng Character Reference Sheet và chỉ thị hệ thống Continuity Agent.
- **Prompt 2 tầng cho Veo / Omni / Flow:** 1 Ảnh tĩnh xuất phát điểm (Starting Frame) + 1 Video chuyển động 4 nhịp thời gian (0-2s, 2-5s, 5-8s, 8-10s).
- **Âm thanh:** Tự động thu âm giọng đọc dồn dập, hòa âm nhạc nền chiến trận bí ẩn (Du Sơn Luyến x TCMHUC) với hiệu ứng Auto-Ducking chuẩn studio.

### 1. Xem 8 chủ đề sự kiện lịch sử mẫu:
```bash
./run.sh --stickman-topics
```

### 2. Tạo toàn bộ gói sản xuất chỉ bằng 1 lệnh:
```bash
./run.sh --stickman "Trận Bạch Đằng 938: Bẫy cọc ngầm đánh tan quân Nam Hán"
# Hoặc:
./run.sh --stickman "The 1814 London Beer Flood: Đại hồng thủy bia ở London"
```

### 3. Kết quả xuất ra trong thư mục `workspace/run_Stickman_.../`:
1. `historical_stickman_package.md`: Toàn văn hồ sơ sản xuất, kịch bản song ngữ, phân tích lịch sử, nhân vật mẫu và prompt chi tiết.
2. `flow_prompts.txt`: Toàn bộ prompt ảnh & video đã được chuẩn hóa để dán thẳng vào Google Flow / Veo 3.1.
3. `audio_16k_mono.wav`: File âm thanh 60 giây hoàn chỉnh (lời đọc + nhạc nền dồn dập).
4. `flow_manifest.json`: Metadata kỹ thuật.
5. `clips/`: Thư mục lưu 6 clip tải về từ Flow (`1.mp4` đến `6.mp4`).

### 4. Dựng & xuất video 60s hoàn thiện sau khi tạo clip trên Flow:
Sau khi tạo xong 6 clip trên Flow và tải về thả vào thư mục `clips/`:
```bash
./run.sh --flow-render "workspace/run_Stickman_..."
```
Hệ thống sẽ tự động ghép 6 clip, cắt bỏ watermark Veo, phủ hạt film grain, chèn phụ đề TikTok Safe Zone và xuất `final_master.mp4`.

---

## 🎥 PHẦN 2: VIDEO REVIEW / KHOA HỌC / ĐỜI SỐNG (B-ROLL TỰ ĐỘNG)

---

## 🏛️ PHẦN 3: VIDEO DÀI 3P - 5P B-ROLL TỰ ĐỘNG (CHUẨN KÊNH @VANTHANHTHU09)

Mô hình sản xuất video dài 3 đến 5 phút (hoặc tùy ý 1–10 phút) giống hệt các kênh tài liệu triệu view:
- **Tự động viết kịch bản dài**: LLM tính toán chính xác số từ (~155 từ/phút ở tốc độ 1.35x), chia thành 10–22 phân đoạn lôi cuốn.
- **Tự động tìm & tải B-roll 4K**: Hệ thống tự động dịch từ khóa sang tiếng Anh và dùng `yt-dlp` kéo các thước phim tư liệu sắc nét từ YouTube về máy.
- **Hỗ trợ video có sẵn**: Nếu bạn đã có sẵn video tư liệu, chỉ cần đưa đường dẫn vào `--footage <file_hoặc_thư_mục>`.
- **Dựng phim tự động**: Cắt thành các nhịp 3s–5s đan xen, phủ kín 100% thời lượng audio, tự động căn tỉ lệ 9:16 (TikTok) hoặc 16:9 (YouTube).
- **Phụ đề TikTok Safe Zone**: Chữ vàng viền đen nổi bật, căn chỉnh vị trí an toàn tránh bị che bởi UI của TikTok.
- **Thuần Python (Zero Graph Libraries)**: Tuyệt đối không dùng các thư viện pipeline vẽ đồ thị phức tạp.

### Cách chạy:
```bash
# 1. Tự động từ A-Z (Hệ thống tự viết kịch bản 5 phút + tự tìm tải video tư liệu + render):
./run.sh --broll "Bí ẩn bãi đá Stonehenge" --duration 5

# 2. Làm video 3 phút với chủ đề bí ẩn khác:
./run.sh --broll "Bí mật bên dưới Kim Tự Tháp Giza" --duration 3

# 3. Sử dụng video tư liệu có sẵn của bạn:
./run.sh --broll "Bí ẩn Stonehenge" --duration 5 --footage /duong/dan/video_stonehenge.mp4

# 4. Xuất video ngang 16:9 cho YouTube:
./run.sh --broll "Hố đen vũ trụ" --duration 5 --aspect 16:9
```


Tạo video hoàn chỉnh tự động từ A-Z trong 30 giây:
```bash
./run.sh "Tại sao người trẻ không còn mặn mà mua nhà"
```

### Các tùy chọn giọng đọc:
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

## 🎵 BẢN NHẠC NỀN & CHẤT LƯỢNG ÂM THANH MỚI
- **Nhạc nền:** Đã tích hợp bản beat viral chuẩn từ kênh tham chiếu (**Du Sơn Luyến x TCMHUC beat**) đã tách lời bằng Demucs AI.
- **Âm lượng:** Đã tăng âm lượng BGM lên mức dồn dập (26% khi đọc, 48% khi ngắt nghỉ), hòa âm theo chuẩn -14 LUFS của TikTok.
- **Giọng nữ:** Đã được lọc qua chuỗi Studio EQ (`asetrate=24000*1.12`, `equalizer=3200Hz/180Hz`), loại bỏ hoàn toàn hiện tượng giọng đọc Google Translate đơ cứng.
