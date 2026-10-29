# 📂 Phần Mềm Tự Động Sắp Xếp File Vào Thư Mục Con (Auto File Organizer)

Ứng dụng đồ họa (GUI) độc lập trên Windows giúp tự động dọn dẹp và sắp xếp file vào các thư mục con tương ứng một cách an toàn và thông minh.

---

## 🎯 1. CHẾ ĐỘ MẶC ĐỊNH: PHÂN LOẠI THEO DẠNG TỆP (FILE-FIRST)

Bình thường, ứng dụng luôn **ưu tiên phân loại nhanh toàn bộ file theo định dạng tệp chuẩn** mà không tốn tài nguyên chạy AI:

| Nhóm Danh Mục | Đuôi File Hỗ Trợ | Thư Mục Đích Tạo Ra |
| :--- | :--- | :--- |
| **Tài Liệu** | `.pdf`, `.docx`, `.doc`, `.xlsx`, `.xls`, `.pptx`, `.ppt`, `.txt`, `.csv`, `.md`, `.epub`... | `📁 Tài Liệu` |
| **Hình Ảnh** | `.jpg`, `.jpeg`, `.png`, `.heic`, `.webp`, `.svg`, `.ico`, `.bmp`, `.psd`, `.ai`... | `📁 Hình Ảnh` |
| **Video** | `.mp4`, `.mkv`, `.mov`, `.avi`, `.wmv`, `.flv`, `.webm`, `.3gp`... | `📁 Video` |
| **Âm Thanh** | `.mp3`, `.wav`, `.flac`, `.aac`, `.m4a`, `.ogg`, `.wma`... | `📁 Âm Thanh` |
| **Nén & Cài Đặt** | `.zip`, `.rar`, `.7z`, `.tar`, `.gz`, `.iso`, `.exe`, `.msi`, `.apk`... | `📁 Nén & Cài Đặt` |
| **Code & Dữ Liệu**| `.py`, `.js`, `.ts`, `.html`, `.css`, `.json`, `.xml`, `.sql`, `.java`, `.cpp`... | `📁 Code & Dữ Liệu` |
| **Khác** | Tất cả các định dạng còn lại | `📁 Khác` |

*(Tính năng khớp thông minh: Nếu thư mục mẹ đã có sẵn thư mục như `Ảnh`, `Word`, `Nhạc`, `Video`... ứng dụng tự động gom vào đúng thư mục có sẵn đó mà không tạo thêm thư mục mới).*

---

## 📷 2. TÙY CHỌN: PHÂN LOẠI ẢNH THEO THIẾT BỊ, ÁNH SÁNG & TIÊU CỰ

Khi bạn muốn sắp xếp ảnh chụp một cách chuyên nghiệp theo máy ảnh / điện thoại và thông số chụp, hãy gạt bật:  
👉 **`📱 PHÂN LOẠI ẢNH THEO THIẾT BỊ CHỤP (iPhone, Samsung, Sony, Canon...)`**

* **Phân loại theo Thiết Bị (Device Model)**: Tự động trích xuất siêu dữ liệu EXIF máy ảnh để gom ảnh vào thư mục riêng:
  - `📁 Hình Ảnh / iPhone 18 Pro Max`
  - `📁 Hình Ảnh / Samsung Galaxy S24 Ultra`
  - `📁 Hình Ảnh / Sony ILCE-7M4`
  - `📁 Hình Ảnh / Canon EOS R5`
  - *(Ảnh không có thông tin thiết bị sẽ vào `📁 Hình Ảnh / Thiết Bị Khác`)*
* **☀️ Tùy chọn xếp theo Điều Kiện Ánh Sáng**:
  - `📁 Hình Ảnh / [Tên Thiết Bị] / Đủ Sáng` (Ảnh chụp ban ngày, đủ sáng qua chỉ số APEX Brightness hoặc đo sáng điểm ảnh)
  - `📁 Hình Ảnh / [Tên Thiết Bị] / Thiếu Sáng` (Ảnh chụp đêm, phơi sáng dài, ISO cao hoặc thiếu sáng)
* **🔭 Tùy chọn xếp theo Tiêu Cự (Focal Length)**:
  - `📁 Hình Ảnh / [Tên Thiết Bị] / ... / 13mm (Góc Siêu Rộng)`
  - `📁 Hình Ảnh / [Tên Thiết Bị] / ... / 24mm (Góc Rộng)`
  - `📁 Hình Ảnh / [Tên Thiết Bị] / ... / 48mm (Tiêu Chuẩn)`
  - `📁 Hình Ảnh / [Tên Thiết Bị] / ... / 77mm (Tele)`
  - `📁 Hình Ảnh / [Tên Thiết Bị] / ... / 120mm (Siêu Tele)`

* **🧠 Khả năng Nhận Diện Ngữ Cảnh Đa Tầng Thông Minh (Context-Aware Drill-down)**:
  - Nếu bạn đã sắp xếp ảnh vào `iPhone 18 Pro Max / Đủ Sáng`, sau đó bạn mở lại tool và chọn thư mục `Đủ Sáng` đó để tiếp tục lọc theo tiêu cự:
  - Tool sẽ **tự động nhận biết ngữ cảnh cây thư mục** (đang ở sẵn trong iPhone và Đủ Sáng), và sẽ **CHỈ TẠO các thư mục tiêu cự ngay bên trong thư mục 'Đủ Sáng'**, tuyệt đối không tạo lặp lại `Hình Ảnh`, `iPhone 18 Pro Max` hay `Đủ Sáng` từ đầu!

---

## 🤖 3. TÙY CHỌN NÂNG CAO: PHÂN TÍCH MEDIA BẰNG AI (CHỈ BẬT KHI CẦN)

Khi bạn muốn **chia nhỏ thư mục Hình Ảnh hoặc Video theo từng nội dung cụ thể**, hãy gạt công tắc:  
👉 **`🔍 TÙY CHỌN NÂNG CAO: BẬT AI PHÂN TÍCH NỘI DUNG ẢNH & VIDEO`**

Lúc này, AI sẽ nhận diện nội dung từng file và chia thành các thư mục con:
* `📁 Hình Ảnh / Người & Chân Dung` (hoặc `Video/Người & Chân Dung`)
* `📁 Hình Ảnh / Xe Cộ & Phương Tiện` (Ô tô, xe máy, xe đạp, máy bay, tàu thuyền...)
* `📁 Hình Ảnh / Động Vật & Thú Cưng` (Chó, mèo, chim, thú cưng...)
* `📁 Hình Ảnh / Phong Cảnh & Thiên Nhiên` (Biển, núi rừng, hoàng hôn, đường phố...)
* `📁 Hình Ảnh / Đồ Ăn & Ẩm Thực` (Món ăn, đồ uống, cà phê...)
* `📁 Hình Ảnh / Tài Liệu & Hóa Đơn` (Hóa đơn, giấy tờ chụp...)
* `📁 Hình Ảnh / Ảnh Chụp Màn Hình` (Screenshot máy tính, điện thoại, meme...)

### 🛠️ Hai chế độ AI để bạn chọn:
1. **🟢 AI Offline (Mặc định)**: Chạy 100% trên máy tính của bạn bằng OpenCV DNN + SqueezeNet + Haar Cascade. Không cần Internet, bảo mật tuyệt đối, tốc độ cực nhanh.
2. **☁️ Cloud AI (Google Gemini đa mô hình + Auto-Failover)**:
   - Tự động luân chuyển thông minh (Auto-Failover): Khi một model chạm giới hạn RPM (lỗi 429 Quota Exceeded), hệ thống sẽ **ngay lập tức tự động chuyển sang model khả dụng kế tiếp** mà không làm gián đoạn tiến trình sắp xếp file!
   - Danh sách model được luân chuyển: `gemini-2.5-flash-lite`, `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, `gemini-2.0-flash-lite`, `gemini-2.5-flash`, `gemini-3.8-flash`, `gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-3-flash`, `gemini-2.0-flash`... (tổng cộng hơn 70 RPM).
   - Nếu toàn bộ các model Cloud đều hết hạn mức trong phút đó, hệ thống sẽ tự động dùng tiếp AI Offline để đảm bảo 100% file đều được xử lý gọn gàng.

---

## ⚡ 4. CHẾ ĐỘ TỰ ĐỘNG THỜI GIAN THỰC (REAL-TIME AUTO MODE)

- Gạt công tắc **"⚡ BẬT CHẾ ĐỘ TỰ ĐỘNG THEO DÕI & SẮP XẾP"**:
  - Bất kỳ file nào copy vào thư mục mẹ sẽ **tự động bay vào đúng thư mục con ngay lập tức**!
- **Khởi động cùng Windows**: Tự chạy ngầm khi bạn bật máy.
- **Khay hệ thống (System Tray)**: Thu nhỏ xuống góc dưới bên phải màn hình khi tắt cửa sổ.

---

## 🚀 Hướng Dẫn Sử Dụng Nhanh

### Cách 1: Sử dụng bản Portable (Không cần cài đặt)
1. Tải về và giải nén hoặc mở trực tiếp `SapXepFile.exe`.
2. Nhấp **"📁 Chọn Thư Mục..."** và chọn thư mục cần sắp xếp (ví dụ thư mục `Downloads`, thư mục ảnh máy ảnh...).
3. Chọn tùy chọn bạn muốn:
   - **Mặc định:** Gom sạch file theo dạng tệp chuẩn (Tài liệu, Hình ảnh, Video, Nén...).
   - **Phân loại ảnh theo thiết bị:** Nhóm theo iPhone, Samsung, Sony, Canon... cùng tùy chọn Đủ Sáng / Thiếu Sáng và Tiêu Cự.
   - **Tùy chọn nâng cao:** Bật AI nhận diện nội dung (Người, Xe cộ, Động vật, Phong cảnh...).
4. Bấm **"🚀 SẮP XẾP FILE NGAY"**.

---

## 🛠️ Cài Đặt & Chạy Từ Mã Nguồn (Developer)

Nếu muốn chạy trực tiếp từ mã nguồn Python:

1. Clone repository về máy:
   ```bash
   git clone https://github.com/ducdinh98/Auto-File-Organizer.git
   cd Auto-File-Organizer
   ```

2. Cài đặt các thư viện phụ thuộc:
   ```bash
   pip install -r requirements.txt
   ```

3. Chạy ứng dụng:
   ```bash
   python app.py
   ```

4. Đóng gói thành file Portable `.exe`:
   ```bash
   pyinstaller SapXepFile.spec
   ```
