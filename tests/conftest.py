"""Pytest configuration and shared fixtures."""

import pytest
from langchain_core.messages import HumanMessage, AIMessage

from app.tools.registry import ToolRegistry
from app.tools.web_search_tool import WebSearchTool
from app.tools.notion_tool import NotionTool
from app.agent.context_assembler import ContextAssembler
from app.agent.prompt_builder import PromptBuilder


@pytest.fixture
def tool_registry():
    """Fresh ToolRegistry with production tools registered."""
    registry = ToolRegistry()
    registry.register(WebSearchTool())
    registry.register(NotionTool())
    return registry


@pytest.fixture
def empty_registry():
    """Empty ToolRegistry with no tools."""
    return ToolRegistry()


@pytest.fixture
def context_assembler(tool_registry):
    """ContextAssembler with production tools registered."""
    return ContextAssembler(tool_registry)


@pytest.fixture
def prompt_builder():
    """PromptBuilder instance."""
    return PromptBuilder()


@pytest.fixture
def sample_messages():
    """Two LangChain BaseMessages representing prior conversation history."""
    return [
        HumanMessage(content="Hello"),
        AIMessage(content="Hi there!"),
    ]
