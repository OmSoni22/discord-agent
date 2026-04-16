"""Application bootstrap — initialize all components on startup."""

from __future__ import annotations

import logging

from app.core.db.session import AsyncSessionLocal, init_db, close_db
from app.tools.registry import ToolRegistry
from app.tools.calculator import CalculatorTool
from app.tools.file_reader import FileReaderTool
from app.agent.context_assembler import ContextAssembler
from app.agent.prompt_builder import PromptBuilder
from app.agent.runner import AgentRunner
from app.threads.thread_store import ThreadStore
from app.streaming.sse_handler import SSEHandler

logger = logging.getLogger(__name__)


def create_tool_registry() -> ToolRegistry:
    """Create and populate the tool registry with built-in tools."""
    registry = ToolRegistry()

    # Register built-in tools
    registry.register(CalculatorTool())
    registry.register(FileReaderTool())

    # Future: registry.register(WebSearchTool())
    # Future: registry.register(CodeExecutorTool())

    logger.info("Tool registry initialized with %d tools", len(registry.get_all()))
    return registry


async def create_components() -> dict:
    """Create all application components with proper dependency injection.

    Returns a dict of components to attach to app.state.
    """
    # 0. Initialize DB connection
    await init_db()

    # 1. Create the tool registry
    tool_registry = create_tool_registry()

    # 2. Create the thread store (PostgreSQL-backed)
    thread_store = ThreadStore(session_factory=AsyncSessionLocal)

    # 3. Create the context assembler (depends on tool_registry)
    context_assembler = ContextAssembler(tool_registry)

    # 4. Create the prompt builder
    prompt_builder = PromptBuilder()

    # 5. Create the agent runner (depends on all above)
    agent_runner = AgentRunner(
        tool_registry=tool_registry,
        thread_store=thread_store,
        context_assembler=context_assembler,
        prompt_builder=prompt_builder,
    )

    # 6. Create the SSE handler
    sse_handler = SSEHandler()

    logger.info("All components initialized successfully")

    return {
        "tool_registry": tool_registry,
        "thread_store": thread_store,
        "context_assembler": context_assembler,
        "prompt_builder": prompt_builder,
        "agent_runner": agent_runner,
        "sse_handler": sse_handler,
    }


async def shutdown_components() -> None:
    """Cleanup on shutdown — close DB connections."""
    close_db()
    logger.info("DB connections closed")
