# 🎬 HƯỚNG DẪN TẠO VIDEO TỰ ĐỘNG TỪ A-Z (CHUẨN TIKTOK TRIỆU VIEW)

> Hệ thống đã được thiết kế lại **hoàn toàn tự động từ A-Z**: Tự động viết kịch bản giật tít, lồng giọng đọc Nữ Review Phim siêu cuốn (1.42x), hòa âm nhạc nền bí ẩn kịch tính (Dark Suspense Bass), tự động kéo video b-roll HD từ web (Mixkit / Pexels / Pixabay), ghép phụ đề Safe Zone và xuất thành phẩm ngay trong 1 lệnh duy nhất! **Không còn dính nhãn AI, không cần tạo prompt hay thao tác thủ công trên Google Flow.**

---

## 🚀 CÁCH CHẠY 1 LỆNH DUY NHẤT TỪ A-Z (KHUYÊN DÙNG SỐ 1):

Chỉ cần gõ chủ đề của bạn:
```bash
cd /home/blue/Downloads/Projects/wav2video
../.venv/bin/python main.py "Tại sao người trẻ không còn mặn mà mua nhà"
```

### 🎯 Máy sẽ tự động làm 100% trong ~30 giây:
1. **Kịch bản & Hook 3s:** Viết kịch bản theo mô hình tương phản, giữ chân người xem ngay từ giây đầu tiên.
2. **Giọng đọc Review Phim (1.42x):** Tự động dùng giọng Nữ Review Phim (`review_phim` - Hoài My +4Hz, ngắt nhịp siêu ngắn 0.05s) dồn dập, sắc sảo y hệt các kênh triệu view (như `vanthanhthu09`).
3. **Nhạc nền bí ẩn kịch tính:** Tự động hòa âm bản nhạc **Cinematic Mystery / Suspense Bass** đập ngầm kịch tính ở mức 28% âm lượng, có tính năng Sidechain Ducking (nhạc tự hạ xuống khi giọng đọc cất lên).
4. **Săn Footage HD thật từ Web:** Tự động tìm và tải các đoạn video stock HD thật từ web (Mixkit, Pexels, Pixabay) cho từng cảnh, cắt đúng nhịp câu thoại.
5. **Dựng & Xuất thành phẩm:** Tự động crop 9:16 dọc, vi hạt film grain, phụ đề vàng viền đen Safe Zone và xuất ra:
   - 🎬 `final_master.mp4`: Video hoàn chỉnh sẵn sàng đăng TikTok (100% không bị gắn nhãn AI).
   - 🖼️ `cover.jpg`: Ảnh bìa TikTok 9:16 chuẩn lưới hiển thị profile.
   - 📋 `post_info.txt`: Tiêu đề + Caption gợi ý + 7 Hashtags xu hướng.

---

## 🎙️ CÁC TÙY CHỌN MÀU GIỌNG KHÁC (NẾU MUỐN THAY ĐỔI):
```bash
# Giọng Nữ Review Phim / Drama dồn nhịp, kịch tính (Mặc định):
../.venv/bin/python main.py --voice review_phim "Chủ đề..."

# Giọng Nữ Gen Z tươi sáng, bắt trend:
../.venv/bin/python main.py --voice gen_z "Chủ đề..."

# Giọng Nam Review hiện đại (kinh tế, tài chính, công nghệ):
../.venv/bin/python main.py --voice nam_review "Chủ đề..."

# Giọng Nam Kể Chuyện Giật Gân (bí ẩn, tài liệu đen):
../.venv/bin/python main.py --voice giat_gan "Chủ đề..."
```

---

## 💡 NẾU MUỐN DÙNG LẠI GOOGLE FLOW (TÙY CHỌN):
Nếu bạn vẫn muốn tự tay sinh video AI trên Google Flow bằng prompt:
```bash
../.venv/bin/python main.py --flow-prep "Chủ đề..."
```
Hệ thống sẽ chuẩn bị audio và file `flow_prompts.txt` để bạn copy sang Google Flow như trước.
