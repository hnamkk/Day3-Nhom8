# Lab 3: Chatbot vs ReAct Agent (Industry Edition)

Welcome to Phase 3 of the Agentic AI course! This lab focuses on moving from a simple LLM Chatbot to a sophisticated **ReAct Agent** with industry-standard monitoring.

## 🚀 Getting Started

### 1. Setup Environment
Copy the `.env.example` to `.env` and fill in your API keys:
```bash
cp .env.example .env
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Directory Structure
- `src/tools/`: Extension point for your custom tools.

## 🏠 Running with Local Models (CPU)

If you don't want to use OpenAI or Gemini, you can run open-source models (like Phi-3) directly on your CPU using `llama-cpp-python`.

### 1. Download the Model
Download the **Phi-3-mini-4k-instruct-q4.gguf** (approx 2.2GB) from Hugging Face:
- [Phi-3-mini-4k-instruct-GGUF](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf)
- Direct Download: [phi-3-mini-4k-instruct-q4.gguf](https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf)

### 2. Place Model in Project
Create a `model/` folder in the root and move the downloaded `.gguf` file there.

### 3. Update `.env`
Change your `DEFAULT_PROVIDER` and set the path:
```env
DEFAULT_PROVIDER=local
LOCAL_MODEL_PATH=./model/Phi-3-mini-4k-instruct-q4.gguf
```

## Demo UI: Chatbot vs ReAct Agent

Run the local comparison UI:

```bash
python demo_ui.py
```

Open `http://127.0.0.1:7860`, enter a travel prompt, then run either:
- `Run Compare`: runs both the baseline chatbot and the ReAct agent.
- `Run Agent`: shows the Agent V2 trace (`Thought`, `Action`, `Observation`, `Final Answer`).

Useful environment options:

```env
DEFAULT_PROVIDER=google
AGENT_VERSION=v2
LOCAL_MODEL_PATH=./model/Phi-3-mini-4k-instruct-q4.gguf
```

For local-only Phi-3 testing, force the demo backend to ignore the UI provider selector:

```powershell
$env:DEMO_FORCE_PROVIDER="local"
$env:LOCAL_MAX_TOKENS="128"
python demo_ui.py
```

To switch back to Gemini in the same PowerShell session:

```powershell
Remove-Item Env:DEMO_FORCE_PROVIDER -ErrorAction SilentlyContinue
$env:DEMO_PROVIDER="google"
python demo_ui.py
```

Agent V2 is designed to improve weaker local models such as Phi-3 by using stricter few-shot examples, parsing retry logic, and guardrails when tools return missing data.

Quick local-only smoke test:

```bash
python scripts/test_local_model.py
```

If Phi-3 feels too slow during demo, reduce output length:

```env
LOCAL_MAX_TOKENS=256
```

To include the Phi-3 baseline in comparison, keep `LOCAL_BASELINE_LLM` unset or set it to `1`.

## 🎯 Lab Objectives

1.  **Baseline Chatbot**: Observe the limitations of a standard LLM when faced with multi-step reasoning.
2.  **ReAct Loop**: Implement the `Thought-Action-Observation` cycle in `src/agent/agent.py`.
3.  **Provider Switching**: Swap between OpenAI and Gemini seamlessly using the `LLMProvider` interface.
4.  **Failure Analysis**: Use the structured logs in `logs/` to identify why the agent fails (hallucinations, parsing errors).
5.  **Grading & Bonus**: Follow the [SCORING.md](file:///Users/tindt/personal/ai-thuc-chien/day03-lab-agent/SCORING.md) to maximize your points and explore bonus metrics.

## 🛠️ How to Use This Baseline
The code is designed as a **Production Prototype**. It includes:
- **Telemetry**: Every action is logged in JSON format for later analysis.
- **Robust Provider Pattern**: Easily extendable to any LLM API.
- **Clean Skeletons**: Focus on the logic that matters—the agent's reasoning process.

---

*Happy Coding! Let's build agents that actually work.*
