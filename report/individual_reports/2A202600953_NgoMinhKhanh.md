# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Ngô Minh Khánh
- **Student ID**: 2A202600953
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

Vai trò là Telemetry & Analysis Engineer. Công việc chính của em là  thực hiện theo Kế hoạch triển khai:

- **Sửa `src/telemetry/metrics.py`**:
	- Sửa hàm `_calculate_cost()` để dùng giá Gemini Flash thực tế: input $0.075/1M tokens, output $0.30/1M tokens.
	- Thêm `get_summary(session_logs)` trả về tổng quan session (avg latency, total cost, total LLM calls, success rate).
	- Thêm `compare(chatbot_metrics, agent_metrics)` để so sánh hiệu năng và chi phí giữa Chatbot và Agent.

- **Viết Chatbot baseline** (`src/chatbot/chatbot.py`):
	- Triển khai phiên bản đối chứng: nhận input, gọi LLM một lần, trả Final Answer (không gọi tools).

- **Viết script phân tích** (`scripts/analyze_logs.py`):
	- Parse các file `logs/*.log` (mỗi dòng JSON), tính: số lỗi `PARSING_ERROR` / `HALLUCINATION_ERROR`, trung bình số bước (loop count) của Agent, latency trung bình, tổng chi phí.
	- In ra bảng tổng kết và lưu kết quả phân tích ra `report/telemetry_summary_<date>.json`.

- **Viết script benchmark** (`scripts/run_benchmark.py`):
	- Chạy 5–10 câu hỏi test trên cả Chatbot và Agent, thu thập metrics (latency, tokens, cost, success), ghi vào `logs/` và tóm tắt bằng `metrics.get_summary()`.

- **Logging & Traces**: Cập nhật `telemetry/logger.py`  để ensure mỗi event có trường `event_type`, `timestamp`, `session_id`, `loop_index`, `latency_ms`, `tokens_in`, `tokens_out`, `cost`.


---

## II. Debugging Case Study (10 Points)

- **Problem Description**: Trong quá trình benchmark, phát hiện hai lỗi chính ảnh hưởng tới phân tích metrics:
	1. Sai công thức tính chi phí trong `metrics._calculate_cost()` (dùng sai đơn vị tokens → cost bị 10–100x thấp hơn thực tế).
	2. Log format không nhất quán (một số entry thiếu `tokens_in/tokens_out` hoặc `loop_index`), làm cho script phân tích `analyze_logs.py` bỏ sót dữ liệu.

- **Log Source**: Các file log sinh bởi `telemetry/logger.py` trong thư mục `logs/` (mỗi dòng JSON). Ví dụ: `logs/benchmark_2026-06-01.log`.

- **Diagnosis**:
	- `_calculate_cost()` trước đó nhân nhầm đơn vị (đã nhân bằng 1 thay vì /1e6), dẫn tới giá trị cost nhỏ hơn thực tế.
	- Một số module gọi logger mà không truyền `tokens_*` fields (thiếu instrumenting trước khi gọi LLM/tool).

- **Solution**:
	- Sửa `_calculate_cost()` để chia cho 1_000_000 và áp giá Gemini Flash: input 0.075$/1M, output 0.30$/1M.
	- Chuẩn hoá schema log: bắt buộc các trường `tokens_in`, `tokens_out`, `latency_ms`, `loop_index`; cập nhật `telemetry/logger.py` và gọi lại logger ở các điểm LLM/tool.
	- Cập nhật `analyze_logs.py` để bỏ qua entry không hợp lệ nhưng log một dòng summary của danh sách bị bỏ qua để kiểm tra sau.

---

## III. Personal Insights: Telemetry & Evaluation (10 Points)

1. **Instrumenting is critical**: Không có dữ liệu đầy đủ (tokens, latency, loop index) thì mọi phân tích chi phí/hiệu năng đều vô nghĩa. Việc chuẩn hoá log schema là bước đầu tiên và quan trọng nhất.
2. **Trade-offs Chatbot vs Agent**: Agent đa bước tạo nhiều cuộc gọi LLM → chi phí và latency cao hơn, nhưng thường cho câu trả lời chính xác, có trace để debug; Chatbot baseline nhanh rẻ nhưng khó theo dõi reasoning.
3. **Practical observation**: Metrics như `cost per successful answer`, `avg loop count`, và `parsing error rate` cho phép so sánh thực tế giữa hệ thống; trong benchmark ban đầu Agent có avg loop count ≈ 3 và cost ~2–4x Chatbot.

---

## IV. Future Improvements (5 Points)

- **Dashboard & Alerts**: Tích hợp dashboard (Grafana/Prometheus hoặc một dashboard nhẹ) để theo dõi latency, error rate, cost in near real-time; thêm alert khi cost spike hoặc parsing error rate vượt ngưỡng.
- **Better Benchmarks**: Mở rộng `scripts/run_benchmark.py` để chạy nhiều truy vấn đa dạng hơn và thêm kiểm tra A/B giữa phiên bản Agent v1/v2.
- **Automated Regression**: Thiết lập CI step để chạy `scripts/analyze_logs.py` sau mỗi PR lớn để phát hiện regressions về trace/logging.


---


