# Product Requirements Document
## Agentic AI System

**Version:** 1.0  
**Status:** Ready for Development  
**Framework:** LangChain (Python)  
**Architecture:** SOLID — Single-Agent, Multi-Agent Ready  

---

## 1. Overview

This document describes the full requirements for building a production-grade agentic AI system. The system takes a user query, assembles a rich context, runs a ReAct (Reason + Act) loop using an LLM, calls tools as needed, and streams the entire process back to the user in real time via SSE.

The codebase must be written following **SOLID principles** so that adding a multi-agent orchestration layer in the future requires zero refactoring of existing components — only new modules on top.

---

## 2. Goals

- Build a working single-agent system end to end
- Stream all LLM output (thinking, text, tool calls) to the UI in real time
- Make the codebase clean enough that a future developer can plug in multi-agent support without touching core agent logic
- Use LangChain as the primary framework for LLM calls, tool binding, and the ReAct loop

---

## 3. Out of Scope (v1)

- Multi-agent orchestration (but architecture must support it — see Section 10)
- Long-term / persistent memory (episodic, semantic)
- RAG / vector store retrieval
- Authentication and user management
- Production deployment and scaling

---

## 4. System Architecture Overview

The system has five sequential layers:

```
User Query
    ↓
Context Assembly        ← CLI / backend collects everything before LLM call
    ↓
ReAct Loop              ← LLM thinks → tool call → observe → repeat
    ↓
SSE Stream              ← typed event chunks pushed over HTTP
    ↓
UI                      ← reacts to each event type, renders components
    ↓
Final Answer
```

Each layer is a self-contained module with a clear interface. No layer reaches into another's internals.

---

## 5. Context Assembly

Before the first LLM call, the backend assembles a complete context object. The LLM never resolves environment questions itself — the backend collects all facts programmatically at session start.

### 5.1 Components

| Component | Source | Description |
|---|---|---|
| System prompt | Static config file | Who the agent is, how it should behave |
| Rules / guidelines | Static config file | Hard constraints, tone, refusal rules |
| Tool specs | Auto-generated at startup | Full 4-part spec for every registered tool |
| Chat history | Session store | All prior messages + tool results in this session |
| User query | Current request | The goal for this turn |

### 5.2 Tool Specification Format (Strategy 1 — Static Injection)

Every tool must expose a 4-part specification. All tool specs are injected into the system prompt at session start (Strategy 1 — static injection). No dynamic retrieval is required for v1.

```
Tool name        — unique identifier, snake_case (e.g. web_search)
Description      — what it does AND when to use it (action-verb first)
Input parameters — name, type, description for each parameter
Output schema    — what the tool returns and in what shape
```

The system prompt is assembled once per session. The static portion (identity + rules + tool specs) is kept stable so prompt caching works. The dynamic portion (chat history + user query) is appended after a `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` marker each turn.

### 5.3 Context Assembly Sequence

```
SessionStarted
    → load system_prompt.txt
    → load rules.txt
    → collect all registered tools → generate specs → inject into system prompt
    → mark SYSTEM_PROMPT_DYNAMIC_BOUNDARY
    → [per turn] append chat history + new user query
    → send to LLM
```

---

## 6. ReAct Loop

The core agentic loop. Runs entirely inside `AgentExecutor` (LangChain). The loop continues until `stop_reason = end_turn`.

### 6.1 Loop Steps

```
1. THINK   — LLM receives full context, reasons about next action
2. DECIDE  — Does it have enough info to answer?
             Yes → emit final text → stop_reason = end_turn → exit loop
             No  → emit tool_use block → continue
3. ACT     — LangChain executes the selected tool with the emitted args
4. OBSERVE — Tool result appended to message history as a ToolMessage
5. REPEAT  — Full updated context sent to LLM again → back to step 1
```

### 6.2 LangChain Implementation

- Use `create_react_agent` with a custom prompt template
- Use `AgentExecutor` with `return_intermediate_steps=True` and `stream=True`
- Tool results are automatically appended as `ToolMessage` objects by LangChain
- The loop termination condition is handled by LangChain's built-in `AgentFinish`

### 6.3 Loop Guards

| Guard | Value | Reason |
|---|---|---|
| `max_iterations` | 10 | Prevents infinite loops |
| `max_execution_time` | 60s | Prevents runaway sessions |
| On max reached | Return partial answer with warning | Never silently fail |

---

## 7. Tool System

### 7.1 Tool Interface

Every tool must implement the `BaseTool` interface (LangChain). No exceptions.

```python
class BaseTool(ABC):
    name: str                    # snake_case unique identifier
    description: str             # what it does + when to use it
    args_schema: BaseModel       # Pydantic model for input validation
    
    @abstractmethod
    def _run(self, **kwargs) -> str:
        """Synchronous execution. Must return a string result."""
    
    async def _arun(self, **kwargs) -> str:
        """Async execution. Required for streaming support."""
```

### 7.2 Tool Registration

Tools are registered in a central `ToolRegistry`. The registry is the single source of truth. No tool is ever instantiated directly in agent code.

```python
class ToolRegistry:
    def register(self, tool: BaseTool) -> None
    def get_all(self) -> list[BaseTool]
    def get_by_name(self, name: str) -> BaseTool
    def generate_specs(self) -> str   # returns formatted specs for system prompt
```

### 7.3 Built-in Tools (v1)

| Tool | Description |
|---|---|
| `web_search` | Searches the web for current information |
| `calculator` | Evaluates mathematical expressions |
| `file_reader` | Reads a file from the local filesystem |
| `code_executor` | Executes a Python snippet, returns stdout |

Each tool is in its own file under `tools/`. Adding a new tool = add one file + register it. Nothing else changes.

---

## 8. Streaming (SSE)

All LLM output is streamed to the client via Server-Sent Events. The stream carries typed event chunks. The UI reacts to each event type independently.

### 8.1 Event Types

| Event | When emitted | UI renders |
|---|---|---|
| `content_block_start` (thinking) | LLM begins reasoning | Collapsible thinking block |
| `thinking_delta` | Each reasoning token | Appended inside thinking block |
| `content_block_start` (text) | LLM begins answering | New chat bubble |
| `text_delta` | Each answer token | Appended to bubble (typewriter) |
| `content_block_start` (tool_use) | LLM picks a tool | Tool card with tool name + spinner |
| `input_json_delta` | Tool args streaming | Args fill in progressively |
| `content_block_stop` | Block complete | Finalize that block |
| `message_delta` (tool_use) | Tool about to execute | Tool card → "executing" state |
| `message_delta` (end_turn) | LLM finished | Remove cursor, show token count |
| `message_stop` | Stream ends | Close SSE connection |

### 8.2 Stream Pause During Tool Execution

When a tool call is emitted:
1. SSE stream pauses (LLM is waiting)
2. Backend executes the tool synchronously
3. Result is appended to message history
4. New LLM API call is made
5. SSE stream resumes with the next response

This pause/resume is invisible to the user — the UI shows the tool card in "running" state during the gap.

### 8.3 SSE Endpoint

```
GET /stream?session_id=<id>&query=<user_query>
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

Each event follows the SSE format:
```
event: content_block_delta
data: {"type":"text_delta","delta":"Hello"}

```

---

## 9. SOLID Code Structure

The entire codebase is written following SOLID principles. This is the primary architectural constraint and must be respected by every module.

### 9.1 Principles Applied

**S — Single Responsibility**  
Each class does exactly one thing. `ContextAssembler` only assembles context. `ToolRegistry` only manages tools. `StreamHandler` only handles SSE. They never reach into each other's logic.

**O — Open/Closed**  
The system is open for extension, closed for modification. Adding a new tool = new file. Adding a new streaming event type = new handler class. Core `AgentRunner` never changes.

**L — Liskov Substitution**  
Any tool can replace any other tool without the agent caring. Any `BaseTool` implementation can be swapped in. Any `BaseStreamHandler` can be swapped in.

**I — Interface Segregation**  
No class is forced to implement methods it doesn't need. Tool interface, streaming interface, and memory interface are separate. A simple tool never needs to implement memory methods.

**D — Dependency Inversion**  
`AgentRunner` depends on `BaseToolRegistry` (abstract), not `ToolRegistry` (concrete). `StreamController` depends on `BaseStreamHandler`, not a specific SSE implementation. High-level modules never import low-level modules directly.

### 9.2 Directory Structure

```
project/
│
├── config/
│   ├── system_prompt.txt         # agent identity + rules
│   ├── settings.py               # env vars, model name, limits
│   └── tool_specs_template.txt   # optional: spec format template
│
├── agent/
│   ├── __init__.py
│   ├── runner.py                 # AgentRunner — orchestrates the loop
│   ├── context_assembler.py      # ContextAssembler — builds full context
│   └── prompt_builder.py        # PromptBuilder — formats system prompt
│
├── tools/
│   ├── __init__.py
│   ├── base.py                   # BaseTool abstract class
│   ├── registry.py               # ToolRegistry
│   ├── web_search.py             # WebSearchTool(BaseTool)
│   ├── calculator.py             # CalculatorTool(BaseTool)
│   ├── file_reader.py            # FileReaderTool(BaseTool)
│   └── code_executor.py          # CodeExecutorTool(BaseTool)
│
├── streaming/
│   ├── __init__.py
│   ├── base.py                   # BaseStreamHandler abstract class
│   ├── sse_handler.py            # SSEHandler(BaseStreamHandler)
│   └── event_mapper.py           # maps LangChain events → SSE event types
│
├── session/
│   ├── __init__.py
│   ├── session_store.py          # in-memory session + chat history
│   └── models.py                 # Session, Message, ToolResult dataclasses
│
├── api/
│   ├── __init__.py
│   ├── routes.py                 # FastAPI routes
│   └── dependencies.py           # DI — injects registry, assembler, etc.
│
└── main.py                       # app entrypoint
```

### 9.3 Key Class Responsibilities

```
ContextAssembler
  └── assemble(session, query) → ContextObject
      reads: system_prompt, rules, tool specs, chat history, query
      returns: single structured object ready for LLM

PromptBuilder
  └── build(context: ContextObject) → list[BaseMessage]
      formats context into LangChain message format
      places SYSTEM_PROMPT_DYNAMIC_BOUNDARY correctly

ToolRegistry
  └── register(tool) / get_all() / generate_specs()
      single source of truth for all tools
      specs auto-generated from tool metadata

AgentRunner
  └── run(context, stream_handler) → AsyncGenerator
      creates LangChain agent with registered tools
      drives the ReAct loop
      delegates all streaming to stream_handler

SSEHandler(BaseStreamHandler)
  └── handle(event) → SSE formatted string
      maps each LangChain streaming event to correct SSE event type
      never contains agent logic
```

---

## 10. Multi-Agent Readiness (Out of Scope — Architecture Guidance)

Multi-agent support is **not built in v1**, but the architecture must not prevent it. The following constraints ensure a future developer can add it cleanly:

- `AgentRunner` must accept a `session_id` and be fully stateless — all state lives in `SessionStore`
- `ToolRegistry` must be injectable (not a singleton) so different agents can have different tool sets
- `ContextAssembler` must accept a `role` parameter (reserved, unused in v1) so orchestrator-vs-worker context can differ
- Tools must never hold state between calls
- The SSE stream must support a `source_agent` field in each event (reserved, always `"primary"` in v1)
- `AgentRunner` must be importable as a class, not a script, so an orchestrator can instantiate N of them

When the time comes, a future `OrchestratorAgent` simply instantiates multiple `AgentRunner` objects, each with their own `ToolRegistry` and `SessionStore` slice — zero changes to existing code.

---

## 11. Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| LLM Framework | LangChain |
| LLM Provider | Anthropic Claude (claude-sonnet-4-6) |
| API Framework | FastAPI |
| Streaming Protocol | SSE via `sse-starlette` |
| Input validation | Pydantic v2 |
| Session store | In-memory dict (v1), Redis-ready interface |
| Env management | `python-dotenv` |
| Testing | `pytest` + `pytest-asyncio` |

---

## 12. Non-Functional Requirements

| Requirement | Target |
|---|---|
| Time to first token | < 1 second after query submitted |
| Max loop iterations | 10 (configurable) |
| Max session duration | 60 seconds (configurable) |
| Streaming protocol | SSE (not WebSocket) |
| Error handling | All tool failures caught, returned as ToolMessage with error string — loop continues |
| Logging | Every context assembly, tool call, and loop iteration logged with session_id |

---

## 13. Deliverables

- [ ] Working FastAPI app with `/stream` SSE endpoint
- [ ] `AgentRunner` driving a LangChain ReAct loop
- [ ] `ContextAssembler` building full context per turn
- [ ] `ToolRegistry` with all 4 built-in tools registered
- [ ] `SSEHandler` mapping all event types correctly
- [ ] `SessionStore` maintaining chat history per session
- [ ] Unit tests for `ToolRegistry`, `ContextAssembler`, `PromptBuilder`
- [ ] Integration test: full query → tool call → final answer via stream
- [ ] `README.md` with setup, env vars, and how to add a new tool

---

## 14. How to Add a New Tool (Developer Guide)

1. Create `tools/your_tool_name.py`
2. Implement `BaseTool` — fill in `name`, `description`, `args_schema`, `_run`, `_arun`
3. In `main.py` (or `tools/__init__.py`), import and register: `registry.register(YourTool())`
4. Done. The tool spec is auto-generated and injected into the system prompt at next session start.

No other file changes required.

---

*End of PRD v1.0*