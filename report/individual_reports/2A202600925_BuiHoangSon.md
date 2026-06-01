# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Bùi Hoàng Sơn
- **Student ID**: 2A202600925
- **Date**: 01/06/2026

---

## I. Technical Contribution (15 Points)

- **Modules Implemented**:
  - `src/tools/destination_tool.py`
  - `src/tools/weather_tool.py`
  - `src/tools/__init__.py`
  - `data/destinations.json`
  - `data/weather_forecasts.json`

- **Code Highlights**:
  - `search_destinations(city: str, travel_style: str) -> str`
    - Đọc dữ liệu từ `data/destinations.json`
    - Chuẩn hóa tên thành phố và phong cách du lịch
    - Lọc địa điểm theo phong cách `nghỉ dưỡng`, `ẩm thực`, `khám phá`
    - Trả về kết quả dạng văn bản dễ đọc để agent sử dụng trực tiếp
  - `get_weather_forecast(city: str) -> str`
    - Chuyển sang mock data cục bộ trong `data/weather_forecasts.json`
    - Trả về dự báo trong 3 ngày tiếp theo với nhiệt độ và mô tả thời tiết
    - Loại bỏ phụ thuộc vào API key bên ngoài để đảm bảo chạy ổn định trong lab

- **Documentation**:
  - Các tool này được thiết kế tương thích với ReAct Agent bằng cách trả về string kết quả.
  - `src/tools/__init__.py` expose hai hàm tool, giúp agent import dễ dàng.
  - `search_destinations` và `get_weather_forecast` là phần data layer quan trọng cho agent giai đoạn đầu.

---

## II. Debugging Case Study (10 Points)

- **Problem Description**:
  - Lúc đầu, `weather_tool` được triển khai để gọi OpenWeatherMap API và cần `OPENWEATHER_API_KEY`.
  - Trong môi trường lab hiện tại, API key không có sẵn, khiến chức năng weather tool không hoạt động.

- **Log Source**:
  - Thư mục `logs/` chưa tồn tại trong project nên chưa có file log cụ thể để trích dẫn.
  - Việc debug chủ yếu dựa trên kiểm tra code và chạy thử trực tiếp hai tool.

- **Diagnosis**:
  - Vấn đề là phụ thuộc vào dịch vụ bên ngoài và key môi trường gây ra lỗi triển khai, không phải lỗi logic nội tại.
  - Nếu dùng OpenWeatherMap mà không có API key, tool sẽ không trả về dự báo và làm agent bị gián đoạn.

- **Solution**:
  - Chuyển `weather_tool` sang dùng dữ liệu mock cục bộ trong `data/weather_forecasts.json`.
  - Giữ nguyên API của hàm để agent không cần thay đổi cách gọi.
  - Thêm xử lý khi file dữ liệu không tồn tại, báo lỗi rõ ràng.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning**:
   - `Thought` giúp agent tách biệt giai đoạn suy nghĩ và giai đoạn thực thi tool.
   - Bằng cách này, agent có thể chọn công cụ phù hợp trước khi trả lời, thay vì trả lời trực tiếp qua Chatbot.

2. **Reliability**:
   - Agent có thể kém hơn Chatbot khi tool spec không đầy đủ hoặc tool trả về lỗi.
   - Trong tình huống yêu cầu thông tin đơn giản, Chatbot có thể trả lời nhanh hơn vì không cần vòng gọi tool.

3. **Observation**:
   - Các kết quả `Observation` từ tool giúp agent điều chỉnh bước tiếp theo.
   - Nếu tool trả về "không tìm thấy", agent có thể yêu cầu người dùng cung cấp lại thông tin hoặc thử phong cách khác.

---

## IV. Future Improvements (5 Points)

- **Scalability**:
  - Xây dựng registry tool động để dễ thêm nhiều tool mới.
  - Dùng bộ nhớ cache hoặc database để lưu data destination và weather khi mở rộng quy mô.

- **Safety**:
  - Thêm kiểm tra và validate đầu vào cho tên thành phố, phong cách.
  - Triển khai cơ chế xác thực tool call trước khi thực thi.

- **Performance**:
  - Cache dữ liệu weather và destination để giảm số lần đọc file.
  - Nếu có nhiều tool, dùng một service trung gian hoặc queue để quản lý và giám sát.

---

> Báo cáo này được tạo lại chính xác theo template và phản ánh phần mình đã đóng góp: xây dựng data layer và hai tool Destination + Weather.
