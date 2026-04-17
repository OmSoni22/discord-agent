"""Tests for ContextAssembler and PromptBuilder."""

import pytest
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from app.agent.context_assembler import ContextAssembler
from app.agent.prompt_builder import PromptBuilder


class TestContextAssembler:
    """Tests for context assembly."""

    def test_assemble_returns_context(self, context_assembler):
        """assemble() returns a ContextObject with all fields populated."""
        ctx = context_assembler.assemble([], "What is 2+2?")
        assert ctx.user_query == "What is 2+2?"
        assert ctx.role == "primary"
        assert ctx.tool_specs  # not empty — tools are registered

    def test_assemble_includes_history(self, context_assembler, sample_messages):
        """Chat history is included in the context object."""
        ctx = context_assembler.assemble(sample_messages, "Follow up question")
        assert len(ctx.chat_history) == 2

    def test_assemble_custom_role(self, context_assembler):
        """Role parameter is passed through to ContextObject."""
        ctx = context_assembler.assemble([], "test", role="worker")
        assert ctx.role == "worker"

    def test_assemble_empty_history(self, context_assembler):
        """Empty history is accepted without errors."""
        ctx = context_assembler.assemble([], "Hello")
        assert ctx.chat_history == []


class TestPromptBuilder:
    """Tests for prompt building."""

    def test_build_basic_messages(self, prompt_builder, context_assembler):
        """build() produces at least system + human messages."""
        ctx = context_assembler.assemble([], "Hello")
        messages = prompt_builder.build(ctx)

        assert len(messages) >= 2
        assert isinstance(messages[0], SystemMessage)
        assert isinstance(messages[-1], HumanMessage)
        assert messages[-1].content == "Hello"

    def test_build_includes_history(self, prompt_builder, context_assembler, sample_messages):
        """History messages appear between system and current query."""
        ctx = context_assembler.assemble(sample_messages, "second")
        messages = prompt_builder.build(ctx)

        # System (1) + history (2) + current query (1) = 4
        assert len(messages) == 4
        assert isinstance(messages[1], HumanMessage)
        assert messages[1].content == "Hello"
        assert isinstance(messages[2], AIMessage)
        assert messages[2].content == "Hi there!"

    def test_system_message_has_tool_specs(self, prompt_builder, context_assembler):
        """System message contains tool specifications for registered tools."""
        ctx = context_assembler.assemble([], "test")
        messages = prompt_builder.build(ctx)
        system_content = messages[0].content
        assert "web_search" in system_content or "notion" in system_content
