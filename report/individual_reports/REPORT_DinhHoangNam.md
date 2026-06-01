# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Đinh Hoàng Nam
- **Student ID**: 2A202600884
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

Trong nhóm, em phụ trách phần **Tool Developer #2 — Khách sạn & Ngân sách**. Mục tiêu là xây dựng 2 tools quan trọng nhất để demo logic đa bước của ReAct Agent: tra cứu khách sạn theo ngân sách và tính toán chi tiết tổng chi phí chuyến đi.

- **Modules Implemented**:
  - `src/tools/hotel_tool.py`: Tool tra cứu khách sạn, lọc theo ngân sách mỗi đêm, trả về top 3 gợi ý tốt nhất theo rating.
  - `src/tools/budget_tool.py`: Tool tính toán và kiểm tra tổng ngân sách chuyến đi (khách sạn + vé máy bay + ăn uống + phát sinh 10%), có logic gợi ý cắt giảm chi phí khi vượt ngân sách.
  - `data/hotels.json`: Database khách sạn cho 3 thành phố (Đà Nẵng, Hà Nội, Hội An), mỗi thành phố có 5 khách sạn với các mức giá, rating và tiện nghi khác nhau.

- **Code Highlights**:

  **`check_hotel_prices`** — lọc khách sạn theo ngân sách, hỗ trợ alias tên thành phố (cả tiếng Việt có dấu):
  ```python
  def check_hotel_prices(city: str, budget_per_night: int) -> str:
      city_key = _normalize_city(city)
      if city_key is None:
          return f"Không tìm thấy dữ liệu khách sạn cho thành phố '{city}'..."
      affordable = [h for h in hotels if h["price_per_night"] <= budget_per_night]
      top3 = sorted(affordable, key=lambda h: h["rating"], reverse=True)[:3]
      ...
  ```

  **`calculate_budget`** — phân tích chi tiết với buffer 10% phát sinh và gợi ý thông minh:
  ```python
  misc = int((total_hotel + total_food + flight_cost) * 0.10)
  grand_total = total_hotel + total_food + flight_cost + misc
  # Nếu vượt ngân sách → gợi ý cụ thể cách cắt giảm
  if remaining < 0:
      if hotel_cost > 500_000:
          lines.append(f"• Chọn khách sạn rẻ hơn (tiết kiệm ~{hotel_cost * days // 2:,} VND)")
  ```

- **Documentation**:
  - `hotel_tool.py` tích hợp vào vòng lặp ReAct thông qua `_execute_tool()` trong `agent.py`: agent parse `Action: check_hotel_prices` → gọi hàm → nhận chuỗi văn bản làm `Observation` → tiếp tục lên kế hoạch.
  - `budget_tool.py` thường được agent gọi ở bước cuối cùng sau khi đã có thông tin khách sạn và điểm đến, đây là bước xác nhận tính khả thi về tài chính của lịch trình.
  - Cả 2 tools đều trả về chuỗi text có định dạng rõ ràng (emoji + số liệu cụ thể) để LLM dễ đọc và tổng hợp `Final Answer`.

---

## II. Debugging Case Study (10 Points)

- **Problem Description**:
  Khi agent gọi `check_hotel_prices` với city = `"Da Nang"` (không dấu, cách) nhưng dữ liệu JSON lưu key là `"da_nang"`, hàm `_normalize_city()` ban đầu chưa có alias mapping nên trả về `None`, dẫn đến tool báo:

  ```text
  Không tìm thấy dữ liệu khách sạn cho thành phố 'Da Nang'.
  ```

  Agent nhận Observation này, sau đó lặp lại bằng cách thử `"Đà Nẵng"` — lần này parse encoding sai nên vẫn trả lỗi. Agent bị kẹt trong vòng lặp thử-lại 3 lần trước khi `max_iterations` dừng lại.

- **Log Source**:
  Log trong `logs/2026-06-01.log` ghi nhận chuỗi sự kiện:

  ```text
  TOOL_CALL ... tool=check_hotel_prices args={"city": "Da Nang", "budget_per_night": 600000}
  TOOL_RESULT ... result="Không tìm thấy dữ liệu khách sạn cho thành phố 'Da Nang'..."
  TOOL_CALL ... tool=check_hotel_prices args={"city": "Đà Nẵng", "budget_per_night": 600000}
  TOOL_RESULT ... result="Không tìm thấy dữ liệu khách sạn cho thành phố 'Đà Nẵng'..."
  PARSING_ERROR ... max_iterations reached without Final Answer
  ```

- **Diagnosis**:
  Lỗi không đến từ LLM mà từ lớp data layer: hàm `_normalize_city()` không có mapping giữa tên người dùng nhập tự nhiên (`"Da Nang"`, `"Đà Nẵng"`, `"danang"`) và key trong JSON (`"da_nang"`). LLM sinh Action đúng format, nhưng tool không thể resolve tên thành phố.

- **Solution**:
  Em bổ sung dict `_CITY_ALIASES` bao phủ tất cả biến thể tên phổ biến (có dấu / không dấu / viết liền):

  ```python
  _CITY_ALIASES = {
      "đà nẵng": "da_nang",
      "da nang": "da_nang",
      "danang":  "da_nang",
      "hà nội":  "ha_noi",
      "ha noi":  "ha_noi",
      "hanoi":   "ha_noi",
      "hội an":  "hoi_an",
      "hoi an":  "hoi_an",
      "hoian":   "hoi_an",
  }
  ```

  Sau khi sửa, agent gọi tool với bất kỳ biến thể tên nào cũng resolve đúng, không còn vòng lặp lỗi.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning**:
   Chatbot baseline trả lời câu hỏi "Đi Đà Nẵng 3 ngày 5 triệu có đủ không?" bằng kiến thức chung của model — đôi khi đưa ra con số ước tính thiếu căn cứ. ReAct Agent tách bài toán thành các bước: kiểm tra thời tiết → tìm địa điểm → gọi `check_hotel_prices` với ngân sách cụ thể → gọi `calculate_budget` với số liệu thật. `Thought` ở mỗi bước cho thấy agent đang lý luận có cấu trúc thay vì trả lời ngay.

2. **Reliability**:
   Agent thực sự tệ hơn chatbot trong các câu hỏi đơn giản như "Đà Nẵng có bãi biển đẹp không?" — chatbot trả lời tức thì, còn agent chạy qua 3-4 tool calls không cần thiết, làm chậm hơn và tốn token. Đặc biệt với `calculate_budget`, nếu người dùng không cung cấp đủ 4 tham số, agent phải mò thêm các giá trị giả định, dẫn đến kết quả kém chính xác.

3. **Observation**:
   `Observation` từ `check_hotel_prices` và `calculate_budget` tạo ra sự khác biệt rõ nhất so với chatbot. Thay vì bịa ra "khách sạn khoảng 400k/đêm", agent trả về danh sách cụ thể với tên, địa chỉ, tiện nghi. `calculate_budget` thậm chí tính cả buffer 10% chi phí phát sinh và đưa ra gợi ý cắt giảm nếu vượt ngân sách — điều chatbot không thể làm được một cách đáng tin cậy.

---

## IV. Future Improvements (5 Points)

- **Scalability**:
  `hotel_tool.py` hiện đọc file JSON mỗi lần gọi (`_load_hotels()` không cache). Với production, nên load một lần vào memory hoặc dùng SQLite/vector DB để hỗ trợ tìm kiếm ngữ nghĩa (ví dụ: "khách sạn gần biển" thay vì chỉ lọc theo giá).

- **Safety**:
  `calculate_budget` nhận số nguyên từ LLM — nếu LLM truyền sai kiểu (string thay vì int) hoặc số âm, hiện tại có validation cơ bản nhưng chưa đầy đủ. Cần thêm input schema validation (Pydantic) và giới hạn giá trị hợp lý (vd: ngân sách tối đa 1 tỷ VND) để tránh hallucination số liệu phi thực tế.

- **Performance**:
  Hiện tại `check_hotel_prices` chỉ lọc theo `price_per_night`. Có thể mở rộng thêm filter theo số sao, tiện nghi (hồ bơi, wifi, bãi đỗ xe) để agent trả về gợi ý sát nhu cầu hơn. Với nhiều thành phố hơn, nên tách database thành file JSON riêng theo thành phố hoặc dùng async I/O.

- **Production Agent Design**:
  Cặp tools `check_hotel_prices` → `calculate_budget` phản ánh một sub-workflow rõ ràng. Với LangGraph hoặc state-machine, có thể define node riêng cho "Hotel Search" và "Budget Validation", đảm bảo agent luôn chạy đúng thứ tự thay vì phụ thuộc vào LLM tự suy luận thứ tự gọi tools.

---

> [!NOTE]
> Submit this report by renaming it to `REPORT_[YOUR_NAME].md` and placing it in this folder.
