"""Event mapper — maps internal event types to SSE event names."""

from __future__ import annotations

# Maps internal event type → SSE event name
EVENT_TYPE_MAP: dict[str, str] = {
    "thread_info": "thread_info",
    "content_block_start": "content_block_start",
    "thinking_delta": "content_block_delta",
    "text_delta": "content_block_delta",
    "input_json_delta": "content_block_delta",
    "content_block_stop": "content_block_stop",
    "tool_start": "tool_execution",
    "tool_result": "tool_result",
    "message_delta": "message_delta",
    "message_stop": "message_stop",
}


def get_sse_event_name(internal_type: str) -> str:
    """Map an internal event type to the SSE event name."""
    return EVENT_TYPE_MAP.get(internal_type, "unknown")
