<h1 align="center">Deep Fake (Deep-Live-Cam) 2.1.5</h1>

<p align="center">
  Hoán đổi khuôn mặt thời gian thực và tạo deepfake video chỉ với một cú nhấp chuột và một hình ảnh duy nhất.
</p>

<p align="center">
  <img src="media/Download.png" alt="Deep Fake Banner" width="400">
</p>

---

## 📖 Hướng Dẫn Sử Dụng & Khởi Chạy Nhanh

Chào mừng bạn đến với dự án **Deep Fake** phiên bản Việt hóa toàn diện, đã được tối ưu hóa hiệu năng phần cứng vượt trội cho GPU NVIDIA và dọn dẹp không gian làm việc sạch sẽ nhất.

### ⚡ Cách Khởi Chạy Ứng Dụng (Chỉ với 1-Click)
Dự án đã được tích hợp sẵn các tập lệnh tiếng Việt trực quan tại thư mục gốc:

1. **Khởi chạy ứng dụng:** Nhấp đúp chuột vào tệp **`KHOI_DONG.bat`**. Ứng dụng sẽ tự động kích hoạt môi trường ảo, tự động cấu hình tăng tốc CUDA của GPU NVIDIA và mở giao diện màn hình ngang Dashboard (980x750) tiếng Việt.
2. **Theo dõi hiệu năng:** Nhấp đúp chuột vào tệp **`THEO_DOI.bat`** để xem biểu đồ hiệu suất CPU, GPU, VRAM và FPS theo thời gian thực.
3. **Tắt ứng dụng an toàn:** Nhấp đúp chuột vào tệp **`TAT_TIEN_TRINH.bat`** để đóng nhanh toàn bộ tiến trình chạy ngầm của Python, giúp giải phóng hoàn toàn bộ nhớ máy tính.

---

## 🛠️ Các Bước Sử Dụng Giao Diện

Giao diện mới được sắp xếp cực kỳ khoa học và trực quan theo 4 phân khu chính:

1. **Đối tượng Xử lý (Media Selection):**
   * Chọn **Ảnh Nguồn** (Khuôn mặt muốn hoán đổi).
   * Chọn **Ảnh Đích** hoặc **Video Đích** (Khung hình/video muốn đè mặt lên).
2. **Tùy chọn nâng cao (Options):**
   * Cho phép kích hoạt các tùy chọn như *Hòa trộn Poisson*, *Hiện FPS*, *Sửa lỗi Cam Ánh Xanh*...
3. **Tinh chỉnh & Làm nét (Refinement):**
   * Điều chỉnh độ mờ biên trán tự động (`Dynamic Eyebrow Forehead Fade`) và làm mịn da song phương cao cấp (`Bilateral Beauty Filter`).
4. **Màn hình xem trước (Live Preview):**
   * Nhấp **Xem trước** để xem trực tiếp khuôn mặt hoán đổi đã được làm mịn da hoàn hảo, không còn bất kỳ đường viền hay lằn đen thô cứng nào trên trán!

---

## ⚡ Các Tính Năng Đột Phá & Tối Ưu Hiệu Năng Vừa Thực Hiện

* **Làm mịn da cao cấp (Bilateral Beauty Filter):** Tự động làm mịn các đốm sần sùi trên da mặt nhưng giữ lại độ nét tuyệt đối cho mắt, mũi, miệng. Tỷ lệ hòa trộn 65% mịn da và 35% kết cấu gốc mang lại làn da căng bóng chân thực nhất.
* **Xóa viền trán tự động:** Tự động phát hiện vị trí lông mày để làm mờ hình sin phần trán lên rìa tóc, triệt tiêu 100% đường lằn đen nằm ngang.
* **Bộ đệm IO Binding cấp phiên (Session-Level IO Binding Cache):** Tiết kiệm **4-5ms/khung hình** nhờ tái sử dụng vùng nhớ GPU đã cấp phát sẵn thay vì tạo lại mỗi khung hình.
* **DMA truyền dữ liệu siêu tốc (`update_inplace`):** Chuyển trực tiếp ảnh vào GPU, tăng FPS rõ rệt khi xử lý video và live stream trực tiếp.
* **Dọn dẹp siêu sạch (~73.0 MB):** Loại bỏ hoàn toàn các tệp rác, tệp kiểm thử tự động, tệp kịch bản phát triển tiếng Anh lỗi thời và các tệp gif quảng cáo siêu nặng.

---

## 📜 Điều Khoản Sử Dụng (Disclaimer)
Phần mềm Deep Fake này được thiết kế để phục vụ các mục đích sáng tạo nội dung nghệ thuật, làm phim, thiết kế và nghiên cứu AI có đạo đức. 

* **Sử dụng có đạo đức:** Người dùng phải chịu hoàn toàn trách nhiệm pháp lý và đạo đức đối với các sản phẩm tạo ra. Vui lòng nhận được sự đồng ý của chủ thể khi sử dụng khuôn mặt của họ và gắn nhãn rõ ràng "Sản phẩm Deepfake" khi chia sẻ công khai.
* **Bộ lọc an toàn:** Dự án tích hợp sẵn bộ lọc tự động ngăn chặn việc xử lý các nội dung không phù hợp (nhạy cảm, bạo lực, đồi trụy).
