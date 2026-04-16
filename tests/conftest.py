"""Pytest configuration and fixtures for the agentic AI system tests."""

import pytest
from app.tools.registry import ToolRegistry
from app.tools.calculator import CalculatorTool
from app.tools.file_reader import FileReaderTool
from app.agent.context_assembler import ContextAssembler
from app.agent.prompt_builder import PromptBuilder
from app.threads.models import Message


@pytest.fixture
def tool_registry():
    """Fresh ToolRegistry with built-in tools registered."""
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(FileReaderTool())
    return registry


@pytest.fixture
def empty_registry():
    """Empty ToolRegistry with no tools."""
    return ToolRegistry()


@pytest.fixture
def context_assembler(tool_registry):
    """ContextAssembler with tools registered."""
    return ContextAssembler(tool_registry)


@pytest.fixture
def prompt_builder():
    """PromptBuilder instance."""
    return PromptBuilder()


@pytest.fixture
def sample_messages():
    """Sample Message objects for testing (mimicking DB rows)."""
    return [
        Message(
            id="msg-1",
            thread_id="thread-1",
            role="human",
            content="Hello",
        ),
        Message(
            id="msg-2",
            thread_id="thread-1",
            role="ai",
            content="Hi there!",
        ),
    ]
