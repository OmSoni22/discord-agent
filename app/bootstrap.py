"""Application bootstrap — initialize all components and wire them together."""

from __future__ import annotations

import logging

from app.tools.registry import ToolRegistry
from app.tools.web_search_tool import WebSearchTool
from app.tools.notion_tool import NotionTool
from app.agent.context_assembler import ContextAssembler
from app.agent.prompt_builder import PromptBuilder
from app.agent.runner import AgentRunner
from app.discord_bot.bot import set_agent_runner

logger = logging.getLogger(__name__)


def create_tool_registry() -> ToolRegistry:
    """Create and populate the tool registry."""
    registry = ToolRegistry()
    registry.register(WebSearchTool())
    registry.register(NotionTool())
    logger.info("Tool registry initialized with %d tools", len(registry.get_all()))
    return registry


def create_agent_runner() -> AgentRunner:
    """Create and wire all agent components. Returns the configured AgentRunner."""
    tool_registry = create_tool_registry()
    context_assembler = ContextAssembler(tool_registry)
    prompt_builder = PromptBuilder()

    runner = AgentRunner(
        tool_registry=tool_registry,
        context_assembler=context_assembler,
        prompt_builder=prompt_builder,
    )

    # Wire runner into the Discord bot's module-level reference
    set_agent_runner(runner)

    logger.info(
        "AgentRunner initialized | tools=%s",
        [t.name for t in tool_registry.get_all()],
    )
    return runner
