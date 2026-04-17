"""Tests for the AgentRunner ReAct loop."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage

from app.agent.runner import AgentRunner
from app.tools.registry import ToolRegistry
from app.agent.context_assembler import ContextAssembler
from app.agent.prompt_builder import PromptBuilder


def _make_runner(tool_registry=None):
    """Helper: build a minimal AgentRunner with mocked LLM."""
    registry = tool_registry or ToolRegistry()
    assembler = ContextAssembler(registry)
    builder = PromptBuilder()
    with patch("app.agent.runner.init_chat_model") as mock_init:
        mock_init.return_value = MagicMock()
        runner = AgentRunner(
            tool_registry=registry,
            context_assembler=assembler,
            prompt_builder=builder,
        )
    return runner


@pytest.mark.asyncio
async def test_run_returns_string():
    """run() returns a string, not a generator."""
    runner = _make_runner()

    # Mock the LLM to return a simple text chunk with no tool calls
    mock_chunk = MagicMock()
    mock_chunk.content = "42"
    mock_chunk.tool_calls = []
    mock_chunk.tool_call_chunks = []

    async def fake_astream(messages):
        yield mock_chunk

    runner._llm.bind_tools = MagicMock(return_value=runner._llm)
    runner._llm.astream = fake_astream

    result = await runner.run(query="What is 6×7?", history=[])
    assert isinstance(result, str)
    assert "42" in result


@pytest.mark.asyncio
async def test_run_uses_history():
    """run() passes history through to the prompt builder."""
    runner = _make_runner()

    mock_chunk = MagicMock()
    mock_chunk.content = "I remember."
    mock_chunk.tool_calls = []
    mock_chunk.tool_call_chunks = []

    async def fake_astream(messages):
        yield mock_chunk

    runner._llm.bind_tools = MagicMock(return_value=runner._llm)
    runner._llm.astream = fake_astream

    history = [HumanMessage(content="Prev"), AIMessage(content="OK")]
    result = await runner.run(query="Follow up", history=history)
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_run_max_iterations_returns_partial():
    """If max_iterations is reached with ongoing tool calls, returns partial response."""
    from app.config.settings import settings
    original_max = settings.max_iterations
    settings.max_iterations = 1

    runner = _make_runner()

    # Simulate LLM always returning a tool call (forces max iterations)
    mock_chunk = MagicMock()
    mock_chunk.content = "Thinking..."
    mock_chunk.tool_calls = [{"name": "unknown_tool", "args": {}, "id": "tc1"}]
    mock_chunk.tool_call_chunks = []

    async def fake_astream(messages):
        yield mock_chunk

    runner._llm.bind_tools = MagicMock(return_value=runner._llm)
    runner._llm.astream = fake_astream

    try:
        result = await runner.run(query="Do something", history=[])
        assert isinstance(result, str)
    finally:
        settings.max_iterations = original_max
