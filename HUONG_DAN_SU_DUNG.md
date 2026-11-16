# 🎬 HƯỚNG DẪN DỰNG VIDEO TỰ ĐỘNG BẰNG DÒNG LỆNH (CLI)

Hệ thống hỗ trợ 2 chế độ dựng video dọc 9:16 cho **TikTok / YouTube Shorts / Reels**:
1. ⭐ **Chế độ STICKMAN DIRECTOR (Khuyên dùng)**: Tự động hóa 100% từ A-Z, không cần mở web hay Google Flow.
2. 🔄 **Chế độ FLOW RENDER**: Dành cho ai muốn tự tạo clip từ Google Flow / AI Video rồi ghép lại.

---

## 🌟 PHẦN 1: CHẾ ĐỘ STICKMAN DIRECTOR (TỰ ĐỘNG 100%)
*Lấy cảm hứng từ kiến trúc `kaomei/stickman-video-director`. Sử dụng hình tượng Người Que và ẩn dụ trực quan (Visual Metaphor) thông minh, dồn dập, cực kỳ viral.*

### ⚡ Lệnh chạy ngay (Chỉ 1 câu lệnh duy nhất):
```powershell
python main.py --stickman "Quy luật 80/20: Vì sao 20% nỗ lực tạo ra 80% kết quả?"
```

### 🤖 Hệ thống tự động làm toàn bộ:
1. **Lên kịch bản đạo diễn**: Chia thành 5 - 7 cảnh người que sắc sảo kèm các đạo cụ ẩn dụ hài hước.
2. **Thu âm giọng đọc 1.5x**: Sử dụng Microsoft Neural (Nam Minh) giọng đọc nhanh, cuốn hút, kèm nhạc nền BGM tự động hạ âm.
3. **Tự động vẽ tranh Người Que**: AI tự động sinh bộ tranh người que vector chuẩn 9:16 cho từng cảnh.
4. **Dựng video hoàn thiện**: Chèn hiệu ứng chuyển cảnh dứt khoát, âm thanh SFX (pop, thud, whoosh) và phụ đề nhảy chữ kiểu CapCut.
5. **Xuất file video thành phẩm** ngay trong thư mục `workspace/stickman_<chủ_đề>_<thời_gian>/final_master.mp4`.

### 🎨 Các Phong cách Chuẩn tích hợp trực tiếp từ repo `stickman-video-director`:
* **`--style amber_noir`** *(Style 6 - Phong cách chính thức của video mẫu git `style-6-amber-noir-mcp.mp4`)*: Người que đầu tròn đen nhám, ánh sáng vàng hổ phách điện ảnh và bóng đổ mận chín huyền bí. Rất cuốn hút và sâu sắc.
* **`--style modern_tech`**: Style 2A Apple Tech Studio, nền phẳng cao cấp, điểm xuyết holographic xanh cyan, cực kỳ hút mắt trên TikTok.
* **`--style modern_story`**: Style 2B Người que Beanie Zeke phiêu lưu trong không gian điện ảnh màu sắc.
* **`--style historical`**: Style 5 Lịch sử hào hùng / châm biếm, người que đội mũ nón và trang bị lịch sử đặc trưng.
* **`--style classic_dark`**: Style 1 Dark nền đen tuyền, nét vẽ trắng nổi bật với điểm nhấn neon.
* **`--style classic_light`**: Style 1 Light nền trắng tinh khiết, nét mực đen phong cách *MinutePhysics* / *Casually Explained*.
* **`--style cozy`**: Style 4 Hoạt hình kể chuyện ấm áp, chiêm nghiệm cuộc sống.
* **`--style prehistoric`**: Style 3 Hài hước châm biếm thời kỳ tiền sử.

---

## 🔄 PHẦN 2: CHẾ ĐỘ GOOGLE FLOW PROMPT (TẠO VIDEO MƯỢT NHƯ GIT)

Để tạo video động mượt mà bằng Google Flow (model **Veo 3.1 Fast**) theo đúng chuẩn phong cách Người Que Amber Noir của git:

### Bước 1: Chuẩn bị Prompt & Giọng đọc 1.5x cho BẤT KỲ chủ đề nào
```powershell
python main.py --flow-prep --stickman "Nhập bất kỳ chủ đề nào bạn muốn"
```
*(Nếu muốn chọn style khác: thêm `--style historical` hoặc `--style modern_tech`... Mặc định là `amber_noir` chuẩn git).*

* Hệ thống tự động:
  1. AI Đạo diễn lên kịch bản ẩn dụ trực quan riêng cho chủ đề đó.
  2. Thu âm giọng đọc Studio 1.5x dồn dập + nhạc nền BGM.
  3. Xuất file `flow_prompts.txt` chứa các đoạn prompt tiếng Anh chuẩn phong cách Amber Noir Stickman (9:16).

### Bước 2: Dán prompt vào Google Flow
* Mở Google Flow -> chọn tỷ lệ dọc **9:16** (model Veo 3.1 Fast).
* Copy từng đoạn Prompt trong `flow_prompts.txt` vào Google Flow để tạo clip (Block 1 tạo mới, Block 2 trở đi bấm Extend).
* Tải các video clip về thư mục: `workspace/flow_<tên_chủ_đề>/flow_clips/` (đặt tên `1.mp4`, `2.mp4`...).

### Bước 3: Dựng thành video hoàn chỉnh
```powershell
python main.py --flow-render latest
```
* Hệ thống sẽ tự động ghép các clip mượt mà, hòa âm giọng đọc 1.5x, nhạc nền, SFX và phụ đề karaoke CapCut ở dưới cùng (khung hình trên sạch bóng 100%).
```
*(Thêm `--speed 1.5` nếu muốn tăng tốc).*

---

## ⚙️ CẤU HÌNH TRONG FILE `.env`

```ini
# Giọng đọc Microsoft Edge Neural Studio
TTS_ENGINE=edge-tts
TTS_VOICE=vi-VN-NamMinhNeural
TTS_RATE=+45%
TTS_PITCH=+0Hz

# Giọng đọc dự phòng Offline
VITS_SPEAKING_RATE=1.45
```
