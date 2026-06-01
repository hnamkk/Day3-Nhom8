# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: [Điền tên của bạn]
- **Student ID**: [Điền MSSV]
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

Trong nhóm, em phụ trách phần **Agent V2, UI/UX demo và documentation**. Mục tiêu chính là cải thiện độ ổn định của ReAct Agent v1, đặc biệt khi chạy với local model Phi-3, đồng thời xây dựng giao diện demo so sánh Chatbot Baseline với ReAct Agent.

- **Modules Implemented**:
  - `src/agent/agent_v2.py`: Agent V2 với retry parsing, guardrail, better few-shot prompt, trace capture và local-safe ReAct controller cho Phi-3.
  - `demo_ui.py`: Web UI local để so sánh Chatbot Baseline vs ReAct Agent, chọn provider Gemini/Phi-3/OpenAI, hiển thị metrics và trace.
  - `src/core/provider_factory.py`: Helper tạo provider thống nhất cho Gemini, OpenAI và local Phi-3.
  - `src/tools/registry.py`: Registry metadata của 4 travel tools dùng chung cho main app, UI và benchmark.
  - `scripts/test_local_model.py`: Script smoke test Phi-3 local độc lập với UI.
  - `report/group_report/GROUP_REPORT_DRAFT.md`: Hoàn thiện draft báo cáo nhóm, gồm success rate, RCA, ablation và production readiness.

- **Code Highlights**:
  - Agent V2 có retry khi LLM trả sai format `Thought / Action / Action Input / Final Answer`.
  - Parser được nới để xử lý `Final Answer` thiếu dấu `:` và JSON tool input bị thiếu dấu `}`.
  - Guardrail được kích hoạt khi tool trả `"Không tìm thấy"`, tránh việc agent tiếp tục lặp hoặc tự bịa dữ liệu.
  - Với Phi-3 local, Agent V2 dùng local-safe path: agent vẫn sinh trace ReAct và gọi đủ tools, nhưng không phụ thuộc vào Phi-3 để sinh JSON nhiều vòng.
  - Demo UI hiển thị rõ sự khác nhau giữa baseline và agent: baseline trả lời trực tiếp, còn agent có tool calls và observations.

- **Documentation**:
  - Em cập nhật report nhóm để giải thích vì sao Phi-3 local yếu hơn Gemini ở instruction-following.
  - Em bổ sung phần ablation: Gemini vs Phi-3, prompt/few-shot vs local-safe controller.
  - Em ghi lại số liệu kiểm tra: Agent V2 local-safe đạt **5/5 test cases (100%)**, không có hallucination errors trong log hiện tại.

---

## II. Debugging Case Study (10 Points)

- **Problem Description**:
  Khi chạy ReAct Agent với Phi-3 local cho prompt:

  ```text
  Plan a 3-day trip to Da Nang with 5 million VND for relaxation.
  ```

  Agent chạy được các bước đầu như weather và destinations, nhưng đến bước hotel thì Phi-3 sinh JSON bị cụt:

  ```text
  Action: check_hotel_prices
  Action Input: {"city": "Da Nang", "budget_per_night": 500000
  ```

  JSON thiếu dấu `}`, khiến parser báo `PARSING_ERROR`. Khi retry, prompt dài hơn và Phi-3 bắt đầu sinh output rác, dẫn đến lỗi parse nhiều lần.

- **Log Source**:
  Log trong `logs/2026-06-01.log` ghi nhận:

  ```text
  PARSING_ERROR ... Action Input: {"city": "Da Nang", "budget_per_night": 500000
  AGENT_V2_RETRY ... retry: 1
  PARSING_ERROR ... output became malformed / nonsensical
  AGENT_V2_END ... error: parse_retry_exceeded
  ```

  Tổng hợp bằng `scripts/analyze_logs.py`:

  ```text
  Parsing errors: 4
  Hallucination errors: 0
  Agent v2 retries: 3
  Guardrail triggers: 3
  Agent runs: 9, avg loop steps: 2.11
  ```

- **Diagnosis**:
  Lỗi không đến từ tool implementation vì các tools chạy đúng khi nhận JSON hợp lệ. Root cause là Phi-3 local yếu hơn Gemini trong việc giữ strict output format, đặc biệt khi context dài và phải sinh nhiều vòng `Thought -> Action -> Action Input`. Few-shot giúp cải thiện nhưng chưa đủ ổn định cho prompt dài.

- **Solution**:
  Em xử lý theo nhiều lớp:

  1. Thêm few-shot examples rõ ràng trong system prompt của Agent V2.
  2. Thêm retry logic khi parse lỗi.
  3. Làm parser mềm hơn cho `Final Answer` thiếu dấu `:` và JSON thiếu dấu `}`.
  4. Thêm guardrail khi tool trả `"Không tìm thấy"`.
  5. Quan trọng nhất: thêm **local-safe ReAct controller** cho Phi-3. Ở chế độ này, agent vẫn hiển thị trace `Thought`, `Action`, `Action Input`, `Observation`, nhưng phần chọn tool theo SOP được điều phối bằng code để tránh phụ thuộc vào khả năng sinh JSON của Phi-3.

  Sau khi sửa, bộ kiểm tra offline đạt:

  ```text
  SUCCESS_RATE=5/5=100%
  ```

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning**:
   Chatbot baseline chỉ trả lời một lần dựa trên kiến thức chung của model, nên dễ đưa ra thông tin không kiểm chứng. ReAct Agent tách bài toán thành nhiều bước: kiểm tra thời tiết, tìm địa điểm, tìm khách sạn, rồi tính ngân sách. `Thought` giúp model/agent biết mình đang ở bước nào, còn `Action` biến suy luận đó thành hành động cụ thể qua tools.

2. **Reliability**:
   Agent có thể tệ hơn chatbot trong các câu hỏi rất đơn giản vì phải chạy nhiều bước hơn, chậm hơn và có nguy cơ lỗi parse format. Với Phi-3 local, việc bắt model sinh JSON nghiêm ngặt nhiều vòng dễ gây lỗi. Vì vậy Agent V2 cần retry, guardrail và local-safe controller.

3. **Observation**:
   `Observation` là điểm khác biệt lớn nhất so với chatbot. Sau mỗi tool call, agent nhận dữ liệu thật từ môi trường: thời tiết, địa điểm, khách sạn, ngân sách. Những observation này giúp câu trả lời cuối cùng có căn cứ hơn. Ví dụ, thay vì bịa khách sạn hoặc giá phòng, agent dùng `check_hotel_prices` và `calculate_budget` để trả lời dựa trên data nội bộ.

---

## IV. Future Improvements (5 Points)

- **Scalability**:
  Có thể tách UI và backend thành API riêng, dùng async queue cho tool calls, cache kết quả weather/hotel để giảm latency.

- **Safety**:
  Thêm supervisor layer để kiểm tra tool call trước khi execute, giới hạn domain du lịch, và kiểm tra xem final answer có bịa thông tin ngoài observations không.

- **Performance**:
  Với local model, nên dùng prompt ngắn hơn, giảm `LOCAL_MAX_TOKENS`, cache model instance, và dùng local-safe controller cho các workflow ổn định. Với nhiều tools hơn, có thể thêm tool retrieval hoặc router để chỉ đưa các tools liên quan vào prompt.

- **Production Agent Design**:
  Có thể chuyển sang LangGraph hoặc state-machine rõ ràng hơn cho các bước `weather -> destinations -> hotels -> budget`, đồng thời vẫn giữ LLM để tổng hợp câu trả lời tự nhiên.

---

> [!NOTE]
> Rename this file to `REPORT_[YOUR_NAME].md` before submission.

