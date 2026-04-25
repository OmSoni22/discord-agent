# Discord AI Agent

A production-grade Discord bot powered by a **ReAct loop** agent with **tool calling** and **multi-provider LLM support**.

Built with **LangChain + discord.py**, following **SOLID principles** and designed to be extended with new tools and providers.

## Features

- 🤖 **ReAct Loop Agent** — Think → Decide → Act → Observe → Repeat
- 🔍 **Web Search** — DuckDuckGo search, no API key required
- 📄 **Notion Integration** — Read, create, update, and search Notion pages & databases
- 🔀 **Multi-Provider LLM** — Supports Groq, OpenRouter, and Google Gemini
- 💬 **Discord History** — Fetches channel history for conversational context
- 📌 **Channel Filtering** — Optionally restrict the bot to specific channels
- 🧪 **Fully Tested** — pytest + pytest-asyncio test suite

## Architecture

```
Discord Message → Context Assembly → ReAct Loop → Discord Reply
```

- **Context Assembly**: System prompt + rules + tool specs + channel history
- **ReAct Loop**: LLM reasons, decides which tool to call, observes result, repeats
- **Discord Bot**: `discord.py` client wired to the agent runner via dependency injection

## Project Structure

```
app/
├── config/
│   ├── settings.py           # Environment config (Pydantic Settings)
│   ├── system_prompt.txt     # Agent identity + behavior
│   └── rules.txt             # Hard constraints for the agent
├── agent/
│   ├── runner.py             # AgentRunner — ReAct loop orchestrator
│   ├── context_assembler.py  # Builds full context per turn
│   └── prompt_builder.py     # Formats context → LangChain messages
├── tools/
│   ├── base.py               # BaseTool contract
│   ├── registry.py           # ToolRegistry — single source of truth
│   ├── web_search_tool.py    # DuckDuckGo web search (no API key)
│   └── notion_tool.py        # Notion pages & database operations
├── discord_bot/
│   ├── bot.py                # Discord client + event handlers
│   ├── message_handler.py    # Dispatches messages to the agent
│   └── formatter.py          # Formats agent output for Discord
├── bootstrap.py              # Component initialization + DI wiring
└── main.py                   # Application entrypoint
tests/
├── test_tools.py             # Tool unit tests
├── test_notion_tool.py       # Notion tool tests
├── test_runner.py            # AgentRunner tests
├── test_formatter.py         # Discord formatter tests
├── test_context_and_prompt.py
└── test_tool_registry.py
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
# Edit .env with your API keys
```

**Required env vars:**

| Variable | Description | Default |
|----------|-------------|---------|
| `MODEL_PROVIDER` | LLM provider (`groq`, `openrouter`, `google_genai`) | `openrouter` |
| `MODEL_NAME` | Model to use (see examples below) | `anthropic/claude-3.5-sonnet` |
| `API_KEY` | API key for the chosen provider | Required |
| `LLM_BASE_URL` | Custom base URL (for OpenRouter) | *(empty)* |
| `MAX_TOKENS` | Max tokens per response | `4096` |
| `MAX_ITERATIONS` | ReAct loop iteration limit | `10` |
| `MAX_EXECUTION_TIME` | Max agent execution time (seconds) | `60` |
| `DISCORD_BOT_TOKEN` | Your Discord bot token | Required |
| `DISCORD_HISTORY_LIMIT` | Messages to fetch for context | `20` |
| `DISCORD_ALLOWED_CHANNEL_IDS` | Comma-separated channel IDs to restrict bot; leave empty for all | *(empty)* |
| `NOTION_API_KEY` | Notion integration token | Optional |
| `NOTION_DEFAULT_PAGE_ID` | Default parent page for new Notion pages | Optional |
| `DEBUG` | Enable debug logging | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |

**Provider + model examples:**

```env
# Groq (fast and free tier available)
MODEL_PROVIDER=groq
MODEL_NAME=llama-3.3-70b-versatile
API_KEY=gsk_...

# OpenRouter (access to Claude, GPT-4, etc.)
MODEL_PROVIDER=openrouter
MODEL_NAME=anthropic/claude-3.5-sonnet
API_KEY=sk-or-...
LLM_BASE_URL=https://openrouter.ai/api/v1

# Google Gemini
MODEL_PROVIDER=google_genai
MODEL_NAME=gemini-1.5-flash
API_KEY=AIza...
```

### 3. Create a Discord Bot

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2. Create a new application → add a **Bot**
3. Under **Privileged Gateway Intents**, enable **Message Content Intent**
4. Copy the bot token into `DISCORD_BOT_TOKEN`
5. Generate an invite URL with `bot` scope + `Send Messages` / `Read Message History` permissions

### 4. (Optional) Set Up Notion Integration

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations) and create an integration
2. Copy the token into `NOTION_API_KEY`
3. Share the relevant Notion pages/databases with your integration from the Notion UI

### 5. Run

```bash
python -m app.main
```

## Available Tools

### `web_search`
Searches the web via DuckDuckGo. Returns the top 5 results with title, URL, and snippet. No API key required.

### `notion`
Interact with Notion workspaces. Supports:
- **read_page** — Read content from a Notion page
- **create_page** — Create a new page under a parent
- **update_page_title** — Update a page's title
- **update_block** — Update the content of a specific block
- **replace_page_content** — Replace all content of a page
- **search_pages** — Search for pages by title
- **query_database** — Query a Notion database with optional filters

## How to Add a New Tool

1. Create `app/tools/your_tool.py`:

```python
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

class YourToolInput(BaseModel):
    param: str = Field(description="What this param does")

class YourTool(BaseTool):
    name: str = "your_tool"
    description: str = "What it does and when to use it."
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

3. Done. The tool spec is auto-injected into the agent's context.

## Testing

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=app --cov-report=term-missing
```

## License

MIT
