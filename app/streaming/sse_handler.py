"""SSE Handler — formats agent events into Server-Sent Events strings."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.streaming.event_mapper import get_sse_event_name

logger = logging.getLogger(__name__)


class SSEHandler:
    """Formats internal event dicts into SSE-formatted strings.

    Implements BaseStreamHandler protocol.
    Never contains agent logic — only formatting.
    """

    def format_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """Format an event dict into an SSE dictionary for EventSourceResponse.

        Args:
            event: Internal event dict with at least a "type" key

        Returns:
            Dictionary with 'event' and 'data' keys for SSE response
        """
        event_type = event.get("type", "unknown")
        sse_event_name = get_sse_event_name(event_type)

        # Build payload (everything except the internal "type" key)
        payload = {k: v for k, v in event.items()}

        data = json.dumps(payload, ensure_ascii=False)

        return {
            "event": sse_event_name,
            "data": data
        }
