# Agentic AI System — Backend

Production-grade single-agent system with **ReAct loop**, **tool calling**, and **SSE streaming**.

Built with **LangChain + Anthropic Claude + FastAPI**, following **SOLID principles** and designed for future multi-agent extension.

## Architecture

```
User Query → Context Assembly → ReAct Loop → SSE Stream → UI
```

- **Context Assembly**: System prompt + rules + tool specs + chat history
- **ReAct Loop**: Think → Decide → Act → Observe → Repeat
- **SSE Stream**: Typed events (thinking, text, tool calls) pushed in real time

## Project Structure

```
app/
├── config/
│   ├── settings.py           # Environment config (Pydantic)
│   ├── system_prompt.txt     # Agent identity + behavior
│   └── rules.txt             # Hard constraints
├── agent/
│   ├── runner.py             # AgentRunner — ReAct loop orchestrator
│   ├── context_assembler.py  # Builds full context per turn
│   └── prompt_builder.py     # Formats context → LangChain messages
├── tools/
│   ├── registry.py           # ToolRegistry — single source of truth
│   ├── calculator.py         # Math expression evaluator
│   └── file_reader.py        # Local file reader
├── streaming/
│   ├── sse_handler.py        # Formats events → SSE wire format
│   └── event_mapper.py       # Maps internal events → SSE event names
├── session/
│   ├── session_store.py      # In-memory session store
│   └── models.py             # Session, Message, ToolResult
├── api/
│   ├── stream_routes.py      # GET /stream SSE endpoint
│   └── router.py             # Central API router
├── bootstrap.py              # Component initialization + DI wiring
└── main.py                   # FastAPI app entrypoint
```

## Setup

### 1. Install Dependencies

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

### 2. Configure Environment

```bash
copy .env.example .env
# Edit .env — set your ANTHROPIC_API_KEY
```

**Required env vars:**

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key | Required |
| `MODEL_NAME` | Claude model to use | `claude-sonnet-4-6` |
| `MAX_TOKENS` | Max tokens per response | `4096` |
| `MAX_ITERATIONS` | ReAct loop iteration limit | `10` |
| `MAX_EXECUTION_TIME` | Max session time (seconds) | `60` |
| `DEBUG` | Enable debug mode + auto-reload | `false` |

### 3. Run

```bash
uvicorn app.main:app --reload
```

Visit: http://localhost:8000/api/docs

### 4. Test the Stream

```
curl "http://localhost:8000/api/v1/stream?query=What+is+2+plus+2"
```

## SSE Event Types

| Event | Description |
|-------|-------------|
| `session_info` | Session ID for the conversation |
| `content_block_start` | LLM begins a new block (text/thinking) |
| `content_block_delta` | Streaming token (text_delta, thinking_delta) |
| `content_block_stop` | Block complete |
| `tool_execution` | Tool is being called |
| `tool_result` | Tool returned a result |
| `message_delta` | Turn complete (end_turn / max_iterations) |
| `message_stop` | Stream ends — close connection |

## How to Add a New Tool

1. Create `app/tools/your_tool.py`:

```python
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

class YourToolInput(BaseModel):
    param: str = Field(description="What this param does")

class YourTool(BaseTool):
    name: str = "your_tool"
    description: str = "What it does + when to use it"
    args_schema: type[BaseModel] = YourToolInput

    def _run(self, param: str) -> str:
        return "result"

    async def _arun(self, param: str) -> str:
        return self._run(param)
```

2. Register in `app/bootstrap.py`:

```python
from app.tools.your_tool import YourTool
registry.register(YourTool())
```

3. Done. Tool spec auto-injected into system prompt.

## Testing

```bash
pytest
```

## Multi-Agent Readiness

The architecture supports future multi-agent orchestration without modifying existing code:

- `AgentRunner` is stateless + injectable (not a singleton)
- `ToolRegistry` is per-agent (different agents = different tools)
- `SessionStore` can be sliced per agent
- All SSE events carry `source_agent` field (`"primary"` in v1)
- Future `OrchestratorAgent` instantiates N `AgentRunner` objects

## License

MIT
