# 🎬 HƯỚNG DẪN QUY TRÌNH GOOGLE FLOW (NGƯỜI THẬT ĐIỆN ẢNH)

> Hệ thống đã được **tinh gọn và thống nhất 100%** vào quy trình tạo video **Người Thật Điện Ảnh (Photorealistic Cinematic)** với Google Flow. Đã loại bỏ hoàn toàn các luồng cũ (router 3 chế độ và người que).

---

## 🚀 QUY TRÌNH TẠO VIDEO 2 BƯỚC:

### BƯỚC 1: Tạo Prompt Google Flow & Audio Giọng Đọc
Chỉ cần chạy lệnh với chủ đề bạn muốn làm:
```bash
cd /home/blue/Downloads/Projects/wav2video
../.venv/bin/python main.py "Tư duy của người Do Thái giúp họ làm chủ đồng tiền" --voice hoai_my
```
*(Hoặc chọn `--voice nam_tram` cho giọng nam trầm điện ảnh)*

#### 🎯 Máy sẽ tự động làm:
1. Viết kịch bản người thật điện ảnh, tối ưu câu mở đầu (Hook 3s) giật tít.
2. Sinh audio giọng đọc chuẩn TikTok (`-14 LUFS`).
3. Chia các Block vừa khít Google Flow, viết sẵn các Prompt chuyên sâu:
   - Tỷ lệ dọc **9:16**.
   - Phong cách **35mm film photography, 8k resolution, volumetric cinematic lighting, shallow depth of field**.
   - Chi tiết da người, biểu cảm tự nhiên, hành động thật (không nhìn chằm chằm ống kính, không biến dạng tay).
   - Tự động liên kết mượt mà từ frame cuối của block trước (Seamless continuation).
4. In các prompt ra màn hình + lưu vào file `flow_prompts.txt`.

---

### BƯỚC 2: Dán vào Google Flow & Tải Clip
1. Mở web **Google Flow**.
2. Copy từng Block Prompt dán vào để tạo video.
3. Tải các file video `.mp4` lưu vào thư mục `flow_clips/` mà máy vừa in ra (ví dụ: `1.mp4`, `2.mp4`).

---

### BƯỚC 3: Ráp Video Hoàn Chỉnh & Làm Sạch Anti-AI
Chạy đúng 1 lệnh render (đường dẫn thư mục đã được in sẵn ở cuối Bước 1):
```bash
../.venv/bin/python main.py --flow-render "workspace/flow_Tu_duy_cua_nguoi_Do_Thai_xxxx"
```

#### 📦 Kết quả nhận được ngay trong thư mục:
- 🎬 `final_master_clean.mp4`: Video hoàn chỉnh đã khớp audio, thêm phụ đề TikTok Safe Zone (viền đen chữ vàng không bị nút like/share che), phủ vi hạt film grain và micro-tilt phá mã AI SynthID.
- 🖼️ `cover.jpg`: Ảnh bìa TikTok 9:16 có tiêu đề giật tít đặt đúng tâm lưới trang cá nhân.
- 📋 `post_info.txt`: Tiêu đề + Caption gợi ý + 7 Hashtags xu hướng + Hướng dẫn đăng điện thoại 100% không bị gán nhãn AI.

---

## 🎙️ DANH SÁCH GIỌNG ĐỌC:
- `hoai_my` (Mặc định): Nữ truyền cảm chuẩn TikTok
- `nam_tram`: Nam trầm ấm điện ảnh (phim tài liệu, lịch sử, tài chính)
- `nu_nhe_nhang`: Nữ nhẹ nhàng, sâu lắng, chill
- `nam_tre`: Nam trẻ trung, dứt khoát
