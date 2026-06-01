import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import src.tools as tools_module
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger


class ReActAgentV2:
    """
    Improved travel ReAct agent with better few-shot prompting, parsing retry,
    guardrails for empty tool results, and trace capture for the demo UI.
    """

    NOT_FOUND_MARKERS = (
        "không tìm thấy",
        "khong tim thay",
        "not found",
        "no data",
        "không có dữ liệu",
        "khong co du lieu",
    )

    def __init__(
        self,
        llm: LLMProvider,
        tools: List[Dict[str, Any]],
        max_steps: int = 6,
        max_parse_retries: int = 2,
    ):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.max_parse_retries = max_parse_retries
        self.history: List[Dict[str, Any]] = []
        self.last_trace: List[Dict[str, Any]] = []

    def get_system_prompt(self) -> str:
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])
        return f"""You are Travel Planner Agent V2, a careful ReAct agent for Vietnamese travel planning.

MISSION:
Create grounded travel advice by using tools for weather, destinations, hotels, and budgets.

AVAILABLE TOOLS:
{tool_descriptions}

STRICT RULES:
1. Use exactly this format when a tool is needed:
Thought: <short reasoning>
Action: <tool_name>
Action Input: <raw JSON object>
2. Use exactly this format when finished:
Thought: <short reasoning>
Final Answer: <Vietnamese answer>
3. Call only one tool at a time.
4. Never invent weather, hotel prices, destinations, or costs.
5. If an Observation says "Không tìm thấy", stop searching blindly and offer available alternatives.
6. If the user asks for a full itinerary, use this order: weather -> destinations -> hotels -> budget.
7. Keep Action Input as raw JSON only. Do not wrap JSON in markdown fences.

WHY FEW-SHOT MATTERS:
Local models such as Phi-3 are weaker at following strict formats than Gemini. The examples below are part of the contract; follow them exactly.

FEW-SHOT 1: Full itinerary
User: Lên lịch Đà Nẵng 3 ngày, ngân sách 5 triệu, thích nghỉ dưỡng.
Thought: Tôi cần kiểm tra thời tiết Đà Nẵng trước khi lập lịch.
Action: get_weather_forecast
Action Input: {{"city": "Đà Nẵng"}}
Observation: Dự báo thời tiết 3 ngày cho Đà Nẵng: nắng đẹp.
Thought: Thời tiết phù hợp, tiếp theo cần tìm địa điểm nghỉ dưỡng.
Action: search_destinations
Action Input: {{"city": "Đà Nẵng", "travel_style": "nghỉ dưỡng"}}
Observation: Địa điểm ở Đà Nẵng phù hợp với phong cách nghỉ dưỡng: Bãi biển Mỹ Khê, Bà Nà Hills.
Thought: Tôi cần tìm khách sạn trong ngân sách hợp lý.
Action: check_hotel_prices
Action Input: {{"city": "Đà Nẵng", "budget_per_night": 800000}}
Observation: Có khách sạn phù hợp.
Thought: Tôi cần kiểm tra tổng chi phí với ngân sách 5 triệu.
Action: calculate_budget
Action Input: {{"hotel_cost": 800000, "days": 3, "flight_cost": 1500000, "food_daily": 300000, "total_budget": 5000000}}
Observation: Tổng chi phí dự kiến nằm trong ngân sách.
Thought: Tôi đã có đủ dữ kiện để trả lời.
Final Answer: Lịch trình 3 ngày ở Đà Nẵng phù hợp với ngân sách 5 triệu...

FEW-SHOT 2: Unknown city guardrail
User: Tìm khách sạn ở Nha Trang dưới 500 nghìn.
Thought: Tôi cần kiểm tra dữ liệu khách sạn cho thành phố được hỏi.
Action: check_hotel_prices
Action Input: {{"city": "Nha Trang", "budget_per_night": 500000}}
Observation: Không tìm thấy dữ liệu khách sạn cho thành phố 'Nha Trang'. Hiện hệ thống hỗ trợ: Đà Nẵng, Hà Nội, Hội An.
Thought: Tool không có dữ liệu cho Nha Trang, tôi phải gợi ý thành phố thay thế thay vì tự bịa khách sạn.
Final Answer: Hiện hệ thống chưa có dữ liệu khách sạn cho Nha Trang. Bạn có thể chọn Đà Nẵng, Hà Nội hoặc Hội An để tôi tìm khách sạn theo ngân sách.

FEW-SHOT 3: Direct weather question
User: Thời tiết Hội An 3 ngày tới thế nào?
Thought: Người dùng chỉ hỏi thời tiết, tôi cần gọi tool thời tiết cho Hội An.
Action: get_weather_forecast
Action Input: {{"city": "Hội An"}}
Observation: Dự báo thời tiết 3 ngày cho Hội An: nắng ấm, trời dễ chịu, trời mát.
Thought: Tôi đã có đủ thông tin thời tiết để trả lời.
Final Answer: Hội An 3 ngày tới khá thuận lợi để đi du lịch...
"""

    def run(self, user_input: str) -> str:
        result = self.run_with_trace(user_input)
        return result["answer"]

    def run_with_trace(self, user_input: str) -> Dict[str, Any]:
        logger.log_event("AGENT_V2_START", {"input": user_input, "model": self.llm.model_name})

        self.last_trace = []

        if self._use_local_safe_mode():
            return self._run_local_safe_plan(user_input)

        current_prompt = f"User: {user_input}\n"
        steps = 0
        parse_retries = 0
        llm_calls = 0

        while steps < self.max_steps:
            result = self.llm.generate(current_prompt, system_prompt=self.get_system_prompt())
            llm_calls += 1
            content = (result.get("content") or "").strip()
            logger.log_event("AGENT_V2_LLM_RESPONSE", {"content": content, "step": steps})

            final_answer = self._parse_final_answer(content)
            if final_answer:
                self._add_trace(steps, "final", content, final_answer=final_answer)
                logger.log_event(
                    "AGENT_V2_END",
                    {"steps": steps, "llm_calls": llm_calls, "parse_retries": parse_retries},
                )
                return self._result(final_answer, steps, llm_calls, parse_retries)

            parsed = self._parse_action(content)
            if parsed is None:
                parse_retries += 1
                logger.log_event(
                    "PARSING_ERROR",
                    {"agent": "v2", "content": content, "retry": parse_retries},
                )
                self._add_trace(steps, "parse_error", content, error="Invalid ReAct format")

                if parse_retries > self.max_parse_retries:
                    answer = (
                        "Xin lỗi, mô hình trả về sai định dạng quá nhiều lần. "
                        "Bạn hãy thử lại với yêu cầu ngắn hơn hoặc chuyển sang Gemini để ổn định hơn."
                    )
                    logger.log_event("AGENT_V2_END", {"steps": steps, "error": "parse_retry_exceeded"})
                    return self._result(answer, steps, llm_calls, parse_retries)

                current_prompt += (
                    f"{content}\n"
                    "Observation: FORMAT_ERROR. You must answer with exactly either:\n"
                    "Thought: ...\nAction: tool_name\nAction Input: {\"key\": \"value\"}\n"
                    "or:\nThought: ...\nFinal Answer: ...\n"
                    "Do not use markdown fences. Retry now.\n"
                )
                logger.log_event("AGENT_V2_RETRY", {"reason": "parse_error", "retry": parse_retries})
                continue

            parse_retries = 0
            tool_name, action_input_str = parsed
            logger.log_event("TOOL_CALL", {"agent": "v2", "tool": tool_name, "args": action_input_str})

            observation = self._execute_tool(tool_name, action_input_str)
            logger.log_event("TOOL_RESULT", {"agent": "v2", "tool": tool_name, "observation": observation})
            self._add_trace(
                steps,
                "tool",
                content,
                action=tool_name,
                action_input=action_input_str,
                observation=observation,
            )

            current_prompt += f"{content}\nObservation: {observation}\n"

            if self._should_trigger_guardrail(observation):
                answer = self._build_guardrail_answer(tool_name, observation)
                logger.log_event(
                    "GUARDRAIL_TRIGGERED",
                    {"agent": "v2", "tool": tool_name, "observation": observation},
                )
                self._add_trace(steps, "guardrail", content, final_answer=answer)
                logger.log_event("AGENT_V2_END", {"steps": steps + 1, "guardrail": True})
                return self._result(answer, steps + 1, llm_calls, parse_retries)

            steps += 1

        answer = (
            "Xin lỗi, tôi đã đạt giới hạn số bước suy luận. "
            "Bạn có thể thử rút gọn yêu cầu hoặc hỏi riêng từng phần: thời tiết, địa điểm, khách sạn, ngân sách."
        )
        logger.log_event("AGENT_V2_END", {"steps": steps, "error": "max_steps_reached"})
        return self._result(answer, steps, llm_calls, parse_retries)

    def _parse_final_answer(self, content: str) -> Optional[str]:
        match = re.search(r"Final Answer\s*:?\s*(.*)", content, re.DOTALL | re.IGNORECASE)
        if not match:
            return None
        answer = match.group(1).strip()
        return answer or None

    def _parse_action(self, content: str) -> Optional[Tuple[str, str]]:
        cleaned = self._strip_markdown_fences(content)
        action_match = re.search(r"Action:\s*([a-zA-Z0-9_]+)", cleaned)
        if not action_match:
            return None

        tool_name = action_match.group(1).strip()
        input_match = re.search(r"Action Input\s*:?\s*(.*)", cleaned, re.DOTALL | re.IGNORECASE)
        if input_match:
            raw_input = input_match.group(1).strip()
        else:
            raw_input = cleaned[action_match.end() :].strip()

        raw_input = re.split(r"\n(?:Observation:|Thought:|Final Answer:)", raw_input, maxsplit=1)[0].strip()
        json_input = self._extract_json_object(raw_input)
        if json_input is None:
            return None

        return tool_name, json_input

    def _strip_markdown_fences(self, content: str) -> str:
        return re.sub(r"```(?:json)?\s*|\s*```", "", content, flags=re.IGNORECASE).strip()

    def _extract_json_object(self, text: str) -> Optional[str]:
        text = text.strip()
        if text.startswith("{") and text.endswith("}"):
            return text

        start = text.find("{")
        end = text.rfind("}")
        if start == -1:
            return None
        if end == -1 or end <= start:
            candidate = text[start:].strip()
            if candidate.count("{") > candidate.count("}"):
                candidate += "}" * (candidate.count("{") - candidate.count("}"))
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                return None
        return text[start : end + 1]

    def _use_local_safe_mode(self) -> bool:
        setting = os.getenv("AGENT_V2_LOCAL_SAFE_MODE", "auto").lower()
        if setting in ("1", "true", "yes", "on"):
            return True
        if setting in ("0", "false", "no", "off"):
            return False
        model_name = (getattr(self.llm, "model_name", "") or "").lower()
        return model_name.endswith(".gguf") or "phi-3" in model_name or "phi3" in model_name

    def _run_local_safe_plan(self, user_input: str) -> Dict[str, Any]:
        logger.log_event("AGENT_V2_LOCAL_SAFE_MODE", {"input": user_input, "model": self.llm.model_name})

        details = self._infer_trip_details(user_input)
        observations: Dict[str, str] = {}
        step = 0

        def call_tool(thought: str, tool_name: str, args: Dict[str, Any]) -> str:
            nonlocal step
            content = (
                f"Thought: {thought}\n"
                f"Action: {tool_name}\n"
                f"Action Input: {json.dumps(args, ensure_ascii=False)}"
            )
            observation = self._execute_tool(tool_name, json.dumps(args, ensure_ascii=False))
            self._add_trace(
                step,
                "tool",
                content,
                action=tool_name,
                action_input=json.dumps(args, ensure_ascii=False),
                observation=observation,
            )
            logger.log_event("TOOL_CALL", {"agent": "v2-local-safe", "tool": tool_name, "args": args})
            logger.log_event("TOOL_RESULT", {"agent": "v2-local-safe", "tool": tool_name, "observation": observation})
            step += 1
            return observation

        observations["weather"] = call_tool(
            f"Tôi cần kiểm tra thời tiết ở {details['city']} trước khi lập lịch.",
            "get_weather_forecast",
            {"city": details["city"]},
        )
        observations["destinations"] = call_tool(
            f"Tôi cần tìm địa điểm phù hợp phong cách {details['style']}.",
            "search_destinations",
            {"city": details["city"], "travel_style": details["style"]},
        )
        observations["hotels"] = call_tool(
            f"Tôi cần tìm khách sạn trong ngân sách khoảng {details['budget_per_night']:,} VND mỗi đêm.",
            "check_hotel_prices",
            {"city": details["city"], "budget_per_night": details["budget_per_night"]},
        )

        hotel_cost = self._pick_hotel_cost(observations["hotels"], details["budget_per_night"])
        observations["budget"] = call_tool(
            "Tôi cần tính tổng chi phí và so sánh với ngân sách người dùng.",
            "calculate_budget",
            {
                "hotel_cost": hotel_cost,
                "days": details["days"],
                "flight_cost": details["flight_cost"],
                "food_daily": details["food_daily"],
                "total_budget": details["total_budget"],
            },
        )

        answer = self._compose_local_safe_answer(details, observations)
        self._add_trace(
            step,
            "final",
            "Thought: Tôi đã có đủ dữ liệu từ tools để tổng hợp lịch trình.\nFinal Answer: ...",
            final_answer=answer,
        )
        logger.log_event("AGENT_V2_END", {"steps": step, "local_safe_mode": True})
        return self._result(answer, step, 0, 0)

    def _infer_trip_details(self, user_input: str) -> Dict[str, Any]:
        text = user_input.lower()
        city = "Đà Nẵng"
        if any(token in text for token in ("hội an", "hoi an", "hoian")):
            city = "Hội An"
        elif any(token in text for token in ("hà nội", "ha noi", "hanoi")):
            city = "Hà Nội"
        elif any(token in text for token in ("đà nẵng", "da nang", "danang")):
            city = "Đà Nẵng"

        style = "nghỉ dưỡng"
        if any(token in text for token in ("ẩm thực", "am thuc", "food", "culinary")):
            style = "ẩm thực"
        elif any(token in text for token in ("khám phá", "kham pha", "explore", "exploration", "adventure")):
            style = "khám phá"
        elif any(token in text for token in ("relax", "relaxation", "resort", "nghỉ dưỡng", "nghi duong")):
            style = "nghỉ dưỡng"

        days = 3
        days_match = re.search(r"(\d+)\s*-?\s*(?:ngày|day|days)", text)
        if days_match:
            days = max(1, int(days_match.group(1)))

        total_budget = 5_000_000
        budget_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:triệu|trieu|million)", text)
        if budget_match:
            total_budget = int(float(budget_match.group(1).replace(",", ".")) * 1_000_000)

        budget_per_night = max(300_000, min(1_200_000, int(total_budget * 0.45 / max(days, 1))))
        return {
            "city": city,
            "style": style,
            "days": days,
            "total_budget": total_budget,
            "budget_per_night": budget_per_night,
            "flight_cost": 1_500_000,
            "food_daily": 300_000,
        }

    def _pick_hotel_cost(self, hotel_observation: str, fallback: int) -> int:
        prices = []
        for raw in re.findall(r"Giá:\s*([\d,]+)\s*VND", hotel_observation):
            try:
                prices.append(int(raw.replace(",", "")))
            except ValueError:
                continue
        return max(prices) if prices else fallback

    def _compose_local_safe_answer(self, details: Dict[str, Any], observations: Dict[str, str]) -> str:
        return (
            f"Dưới đây là kế hoạch {details['days']} ngày cho {details['city']} "
            f"theo phong cách {details['style']} với ngân sách khoảng {details['total_budget']:,} VND.\n\n"
            "1. Thời tiết\n"
            f"{observations['weather']}\n\n"
            "2. Địa điểm phù hợp\n"
            f"{observations['destinations']}\n\n"
            "3. Khách sạn gợi ý\n"
            f"{observations['hotels']}\n\n"
            "4. Kiểm tra ngân sách\n"
            f"{observations['budget']}\n\n"
            "Ghi chú demo: câu trả lời này dùng local-safe ReAct path cho Phi-3. "
            "Agent vẫn gọi tools theo Thought -> Action -> Observation, nhưng tránh phụ thuộc quá nhiều "
            "vào khả năng giữ format JSON của model local."
        )

    def _execute_tool(self, tool_name: str, args_str: str) -> str:
        valid_names = {tool["name"] for tool in self.tools}
        if tool_name not in valid_names:
            logger.log_event("HALLUCINATION_ERROR", {"agent": "v2", "tool": tool_name})
            return f"Error: Tool '{tool_name}' không tồn tại trong danh sách cho phép."

        try:
            args = json.loads(args_str)
        except json.JSONDecodeError:
            return f"Error: Action Input không phải là JSON hợp lệ: {args_str}"

        try:
            func = getattr(tools_module, tool_name, None)
            if not callable(func):
                return f"Error: Không tìm thấy implement cho hàm '{tool_name}'."
            return str(func(**args))
        except TypeError as exc:
            return f"Error: Truyền sai tham số cho tool {tool_name}. Chi tiết: {exc}"
        except Exception as exc:
            return f"Error khi thực thi tool {tool_name}: {exc}"

    def _should_trigger_guardrail(self, observation: str) -> bool:
        normalized = observation.lower()
        return any(marker in normalized for marker in self.NOT_FOUND_MARKERS)

    def _build_guardrail_answer(self, tool_name: str, observation: str) -> str:
        if tool_name == "check_hotel_prices":
            next_step = "Bạn có thể chọn Đà Nẵng, Hà Nội hoặc Hội An, hoặc tăng ngân sách mỗi đêm."
        elif tool_name == "search_destinations":
            next_step = "Bạn có thể thử một trong ba phong cách: nghỉ dưỡng, ẩm thực, khám phá."
        elif tool_name == "get_weather_forecast":
            next_step = "Bạn có thể chọn Đà Nẵng, Hà Nội hoặc Hội An để xem thời tiết."
        else:
            next_step = "Bạn có thể chỉnh lại thành phố, số ngày hoặc ngân sách để tôi tính lại."

        return (
            "Mình chưa thể tiếp tục lập kế hoạch vì dữ liệu công cụ không đủ:\n"
            f"{observation}\n\n"
            f"Gợi ý xử lý: {next_step}"
        )

    def _add_trace(self, step: int, event: str, llm_response: str, **kwargs: Any) -> None:
        trace_item = {"step": step, "event": event, "llm_response": llm_response}
        trace_item.update(kwargs)
        self.last_trace.append(trace_item)

    def _result(self, answer: str, steps: int, llm_calls: int, parse_retries: int) -> Dict[str, Any]:
        return {
            "answer": answer,
            "trace": self.last_trace,
            "metrics": {
                "steps": steps,
                "llm_calls": llm_calls,
                "parse_retries": parse_retries,
                "tool_calls": len([item for item in self.last_trace if item.get("event") == "tool"]),
            },
        }
