"""Tests for Thread and Message models (unit-level, no DB)."""

import pytest
from app.threads.models import Thread, Message


class TestThreadModel:
    """Tests for the Thread SQLAlchemy model (in-memory only)."""

    def test_thread_creation(self):
        """Thread can be instantiated with basic fields."""
        thread = Thread(id="test-uuid", title="My Chat")
        assert thread.id == "test-uuid"
        assert thread.title == "My Chat"

    def test_thread_with_title(self):
        """Thread can be created with a title."""
        thread = Thread(title="Test Chat")
        assert thread.title == "Test Chat"

    def test_thread_repr(self):
        """Thread has a useful repr."""
        thread = Thread(title="Test")
        assert "Thread" in repr(thread)


class TestMessageModel:
    """Tests for the Message SQLAlchemy model (in-memory only)."""

    def test_message_creation(self):
        """Message can be instantiated with required fields."""
        msg = Message(id="msg-uuid", thread_id="test-thread", role="human", content="Hello")
        assert msg.id == "msg-uuid"
        assert msg.role == "human"
        assert msg.content == "Hello"

    def test_tool_message_fields(self):
        """Tool messages have extra fields."""
        msg = Message(
            thread_id="test-thread",
            role="tool",
            content="42",
            tool_call_id="call_123",
            tool_name="calculator",
            tool_input={"expression": "6 * 7"},
        )
        assert msg.tool_name == "calculator"
        assert msg.tool_input == {"expression": "6 * 7"}
        assert msg.tool_call_id == "call_123"

    def test_message_repr(self):
        """Message has a useful repr."""
        msg = Message(thread_id="t1", role="ai", content="Hello")
        assert "Message" in repr(msg)
