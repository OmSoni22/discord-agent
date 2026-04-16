"""Tests for ContextAssembler and PromptBuilder."""

import pytest
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from app.agent.context_assembler import ContextAssembler
from app.agent.prompt_builder import PromptBuilder
from app.threads.models import Message


class TestContextAssembler:
    """Tests for context assembly."""

    def test_assemble_returns_context(self, context_assembler):
        """assemble() returns a ContextObject with all fields populated."""
        ctx = context_assembler.assemble("thread-1", [], "What is 2+2?")
        assert ctx.user_query == "What is 2+2?"
        assert ctx.role == "primary"
        assert ctx.tool_specs  # not empty
        assert "calculator" in ctx.tool_specs

    def test_assemble_includes_history(self, context_assembler, sample_messages):
        """Chat history from thread is included in context."""
        ctx = context_assembler.assemble("thread-1", sample_messages, "Follow up question")
        assert len(ctx.chat_history) == 2

    def test_assemble_custom_role(self, context_assembler):
        """Role parameter is passed through."""
        ctx = context_assembler.assemble("thread-1", [], "test", role="worker")
        assert ctx.role == "worker"


class TestPromptBuilder:
    """Tests for prompt building."""

    def test_build_basic_messages(self, prompt_builder, context_assembler):
        """build() produces system + human messages."""
        ctx = context_assembler.assemble("thread-1", [], "Hello")
        messages = prompt_builder.build(ctx)

        assert len(messages) >= 2
        assert isinstance(messages[0], SystemMessage)
        assert isinstance(messages[-1], HumanMessage)
        assert messages[-1].content == "Hello"

    def test_build_includes_history(self, prompt_builder, context_assembler, sample_messages):
        """History messages appear between system and current query."""
        ctx = context_assembler.assemble("thread-1", sample_messages, "second")
        messages = prompt_builder.build(ctx)

        # System + 2 history + current query = 4
        assert len(messages) == 4

    def test_system_message_has_tool_specs(self, prompt_builder, context_assembler):
        """System message contains tool specifications."""
        ctx = context_assembler.assemble("thread-1", [], "test")
        messages = prompt_builder.build(ctx)
        system_content = messages[0].content
        assert "calculator" in system_content.lower() or "Calculator" in system_content
