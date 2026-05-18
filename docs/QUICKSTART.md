# Hướng dẫn nhanh — Deep-Live-Cam

## Tổng quan
Deep-Live-Cam là công cụ thay mặt (face-swap) thời gian thực và xử lý video sử dụng mô hình ONNX. Tài liệu này tóm tắt các bước cần thiết để cài đặt và sử dụng dự án một cách an toàn và hợp pháp.

## Yêu cầu
- Python 3.11
- pip
- Git
- (Tuỳ chọn) GPU NVIDIA/AMD hoặc Apple Silicon để tăng tốc
- ffmpeg (để xử lý video)

## Cài đặt nhanh (Windows)
1. Tạo và kích hoạt môi trường ảo:

```powershell
python -m venv venv
venv\Scripts\activate
```

2. Cài đặt phụ thuộc:

```powershell
pip install -r requirements.txt
```

3. Tải các mô hình cần thiết và đặt vào thư mục `models/` (tham khảo mô tả ở README)

## Chạy
- Chế độ đơn giản (webcam hoặc video):

```powershell
python run.py
```

- Chế độ CLI (ví dụ chuyển file):

```powershell
python run.py --source models/source.png --target media/input.mp4 --output output.mp4
```

## Lời khuyên sử dụng an toàn và đạo đức
- Chỉ sử dụng khuôn mặt khi bạn có sự cho phép rõ ràng của người đó.
- Khi chia sẻ nội dung tạo ra, dán nhãn rõ ràng rằng đó là deepfake.
- Không dùng công cụ để quấy rối, lừa đảo, hoặc vi phạm pháp luật.

## Gói phát hành nhanh (optional)
- Đóng gói bằng `PyInstaller` để tạo file thực thi cho Windows:

```powershell
pip install pyinstaller
pyinstaller --onefile run.py
```

- Hoặc tạo wheel bằng `setuptools`/`pyproject.toml` để phát hành lên PyPI.

## Gợi ý đóng góp
- Xin đọc `CONTRIBUTING.md` để biết quy tắc đóng góp và hướng dẫn kiểm thử.

## Hỗ trợ
- Vấn đề kỹ thuật: mở issue trên repo.
- Nếu cần bản build sẵn cho người dùng cuối, cân nhắc cung cấp release kèm hướng dẫn và kiểm tra pháp lý.
