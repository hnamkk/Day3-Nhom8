import os
import re
import json
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
import src.tools as tools_module

class ReActAgent:

    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []

    def get_system_prompt(self) -> str:
        """
        Production-grade System prompt for the ReAct Agent.
        """
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])
        return f"""You are a "Smart Itinerary Planner" - an elite, professional travel assistant following the ReAct (Reasoning and Acting) framework. 

YOUR MISSION:
Help users plan perfect trips by combining weather forecasts, destination suggestions, hotel prices, and budget calculations.

AVAILABLE TOOLS:
{tool_descriptions}

STRICT GUARDRAILS & RULES (CRITICAL):
1. NO HALLUCINATION: NEVER invent or guess hotel prices, weather, or locations. You MUST ONLY use information returned by your tools. If a tool returns no data, tell the user honestly.
2. DOMAIN RESTRICTION: You are a travel agent. If the user asks about coding, math, politics, or anything unrelated to travel, politely refuse and pivot back to travel planning.
3. ONE TOOL AT A TIME: You must only call ONE tool per Action. Always wait for the Observation before continuing your thought process.
4. ERROR HANDLING: If a tool returns an error (e.g., "City not found"), do NOT try to hallucinate the answer. Ask the user to clarify or suggest available cities based on the error message.

STANDARD OPERATING PROCEDURE (SOP) FOR FULL ITINERARY:
If the user asks for a full itinerary or plan, follow this logical order:
Step 1: Check the weather (get_weather_forecast) to ensure the timing is good.
Step 2: Find destinations matching their style (search_destinations).
Step 3: Check hotel prices (check_hotel_prices).
Step 4: Calculate the total budget (calculate_budget).

OUTPUT FORMAT (YOU MUST STRICTLY FOLLOW THIS):
When you need to use a tool, use this EXACT format:
Thought: <what you are thinking and which tool you should use next>
Action: <tool_name>
Action Input: <a valid JSON string containing the tool's arguments>

When you have enough information to answer the user, use this EXACT format:
Thought: <what you are thinking to synthesize the final answer>
Final Answer: <your polite, concise, and structured response to the user>

--- FEW-SHOT EXAMPLE ---
User: Lên lịch trình nghỉ dưỡng ở Đà Nẵng giúp tôi.
Thought: Người dùng muốn lên lịch trình nghỉ dưỡng ở Đà Nẵng. Theo SOP, bước 1 tôi cần kiểm tra thời tiết ở Đà Nẵng trước.
Action: get_weather_forecast
Action Input: {{"city": "Đà Nẵng"}}
Observation: 2026-06-02: 32.0°C, nắng đẹp.
Thought: Thời tiết rất đẹp. Bước 2, tôi cần tìm các địa điểm phong cách nghỉ dưỡng ở Đà Nẵng.
Action: search_destinations
Action Input: {{"city": "Đà Nẵng", "travel_style": "nghỉ dưỡng"}}
Observation: - Bãi biển Mỹ Khê: Cát trắng, nước trong. - Bà Nà Hills: Khu nghỉ dưỡng trên núi.
Thought: Tôi đã có đủ dữ kiện cơ bản (thời tiết, địa điểm) để tư vấn bước đầu cho người dùng.
Final Answer: Đà Nẵng hiện đang có nắng đẹp (32°C), rất lý tưởng để đi nghỉ dưỡng! Bạn có thể ghé thăm Bãi biển Mỹ Khê hoặc Bà Nà Hills. Bạn có muốn tôi tìm thêm khách sạn và tính ngân sách cho chuyến đi này không?
------------------------
"""

    def run(self, user_input: str) -> str:
        """
        The ReAct loop logic.
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        
        current_prompt = f"User: {user_input}\n"
        steps = 0

        while steps < self.max_steps:
            # 1. Generate LLM response
            result = self.llm.generate(current_prompt, system_prompt=self.get_system_prompt())
            content = result.get("content", "")
            
            # Log raw thought for debugging
            logger.log_event("LLM_RESPONSE", {"content": content, "step": steps})
            
            # 2. Parse Final Answer
            final_answer_match = re.search(r'Final Answer:\s*(.*)', content, re.DOTALL | re.IGNORECASE)
            if final_answer_match:
                final_answer = final_answer_match.group(1).strip()
                logger.log_event("AGENT_END", {"steps": steps, "final_answer": final_answer})
                return final_answer
            
            # 3. Parse Thought, Action, Action Input
            action_match = re.search(r'Action:\s*([a-zA-Z0-9_]+)', content)
            action_input_match = re.search(r'Action Input:\s*(.*?)(?:\nObservation:|$)', content, re.DOTALL)
            
            if action_match and action_input_match:
                tool_name = action_match.group(1).strip()
                action_input_str = action_input_match.group(1).strip()
                
                # Nối những gì LLM đã sinh ra vào prompt (để nhớ ngữ cảnh)
                current_prompt += f"{content}\n"
                
                logger.log_event("TOOL_CALL", {"tool": tool_name, "args": action_input_str})
                
                # Thực thi công cụ
                observation = self._execute_tool(tool_name, action_input_str)
                
                # Append kết quả vào prompt cho vòng lặp sau
                current_prompt += f"Observation: {observation}\n"
                logger.log_event("TOOL_RESULT", {"tool": tool_name, "observation": observation})
            else:
                # Nếu LLM trả về format sai, báo lỗi và ép LLM trả lại
                logger.log_event("PARSING_ERROR", {"content": content})
                current_prompt += f"{content}\nObservation: Error! Invalid format. Please strictly use 'Action:' and 'Action Input:' or 'Final Answer:'.\n"
            
            steps += 1
            
        logger.log_event("AGENT_END", {"steps": steps, "error": "Max steps reached"})
        return "Xin lỗi, tôi đã hết thời gian để suy nghĩ (Max steps reached)."

    def _execute_tool(self, tool_name: str, args_str: str) -> str:
        """
        Dynamic tool execution.
        """
        valid_tool = False
        for tool in self.tools:
            if tool['name'] == tool_name:
                valid_tool = True
                break
                
        if not valid_tool:
            return f"Error: Tool '{tool_name}' không tồn tại trong danh sách cho phép."
            
        try:
            # Parse chuỗi Action Input thành dictionary
            args = json.loads(args_str)
        except json.JSONDecodeError:
            return f"Error: Action Input không phải là định dạng JSON hợp lệ: {args_str}"
            
        try:
            # Lấy hàm thực tế từ module src.tools
            func = getattr(tools_module, tool_name, None)
            if func and callable(func):
                result = func(**args)
                return str(result)
            else:
                return f"Error: Không tìm thấy implement cho hàm '{tool_name}'."
        except TypeError as e:
            return f"Error: Truyền sai tham số cho tool {tool_name}. Chi tiết: {str(e)}"
        except Exception as e:
            return f"Error khi thực thi tool {tool_name}: {str(e)}"
