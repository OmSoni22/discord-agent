"""Base stream handler — abstract interface for streaming implementations."""

from __future__ import annotations

from typing import Any, Protocol


class BaseStreamHandler(Protocol):
    """Abstract interface for stream handlers (Dependency Inversion).

    Any streaming implementation (SSE, WebSocket, etc.) can replace this.
    """

    def format_event(self, event: dict[str, Any]) -> Any:
        """Format an event dict into the transport-specific format (string or dict)."""
        ...
