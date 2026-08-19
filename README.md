# 🎬 Dubbing Video Plus+ — AI Video Dubbing & Studio Suite

**Dubbing Video Plus+** là bộ công cụ desktop lồng tiếng video tự động chuyên nghiệp dành cho Windows, hỗ trợ dịch thuật AI đa tầng, tách nhạc nền Demucs, nhân bản giọng nói theo nhân vật (Voice Cloning) và xuất video chất lượng cao.

---

## ✨ Tính Năng Nổi Bật

1. **Tải & Xử Lý Đa Nền Tảng:**
   * Tải video tự động từ **YouTube, TikTok, Douyin, Bilibili** hoặc nạp file video từ máy tính.
   * Tách âm thanh & nhạc nền phòng thu với **Demucs AI**.
   * Nhận dạng giọng nói siêu nhanh với **Faster-Whisper (CUDA / CPU)**.

2. **Dịch Thuật Thông Minh & Zero-Token Web AI (VoxDub Cách A):**
   * **VoxDub Cách A:** Trích xuất kịch bản lời thoại chuẩn hóa, tối ưu cho văn phong lồng tiếng điện ảnh tự nhiên.
   * **Web AI Zero-Token:** Tự động hóa gửi kịch bản lên **Google Gemini Web, ChatGPT, Claude, DeepSeek** không tốn phí API token.
   * Hỗ trợ Google Translate, DeepL, MyMemory, NLLB-200 và Ollama Local LLM.

3. **Thư Viện Giọng Nói & Nhân Bản Giọng (Voice Clone):**
   * Tự động trích xuất và nhân bản giọng nhân vật chính từ video gốc.
   * Phân loại đa nhân vật (Multi-Speaker Diarization).
   * Thu âm trực tiếp bằng micro trong ứng dụng để tạo giọng clone riêng.
   * Thư viện hơn 120+ giọng đọc chất lượng cao.

4. **Trình Chỉnh Sửa Kịch Bản (Editor Workbench):**
   * Nghe thử giọng đọc từng câu.
   * Gán giọng đọc riêng biệt cho từng nhân vật.
   * Tự động căn chỉnh tốc độ giọng (Smart Fit / Time Stretch) khớp khẩu hình.

5. **Dọn Dẹp & Quản Lý Workspace Thông Minh:**
   * Quản lý toàn bộ video đã xuất và dự án trong thư mục `workspace/`.
   * Hỗ trợ xóa đơn lẻ, xóa hàng loạt (Multi-Select) và dọn dẹp dung lượng tự động.

---

## 🚀 Hướng Dẫn Khởi Chạy

```powershell
# Chạy ứng dụng
python main.py
```

## 📦 Backup & Đẩy Lên GitHub

Chỉ cần chạy file `backup_to_github.bat` hoặc lệnh:
```powershell
python backup_to_github.py
```
