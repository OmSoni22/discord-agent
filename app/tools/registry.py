"""Tool Registry — single source of truth for all registered tools."""

from __future__ import annotations

import logging
from typing import Protocol

from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)


class BaseToolRegistry(Protocol):
    """Abstract interface for tool registries (Dependency Inversion)."""

    def register(self, tool: BaseTool) -> None: ...
    def get_all(self) -> list[BaseTool]: ...
    def get_by_name(self, name: str) -> BaseTool | None: ...
    def generate_specs(self) -> str: ...


class ToolRegistry:
    """Concrete tool registry. Injectable — not a singleton.

    Different agents can have different ToolRegistry instances
    with different tool sets (multi-agent readiness).
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool. Raises ValueError on duplicate names."""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool
        logger.info("Tool registered: %s", tool.name)

    def get_all(self) -> list[BaseTool]:
        """Return all registered tools as a list."""
        return list(self._tools.values())

    def get_by_name(self, name: str) -> BaseTool | None:
        """Look up a tool by name."""
        return self._tools.get(name)

    def generate_specs(self) -> str:
        """Generate formatted tool specifications for the system prompt."""
        if not self._tools:
            return "No tools available."

        specs: list[str] = []
        for tool in self._tools.values():
            # Extract parameter info from args_schema
            params_str = "None"
            if tool.args_schema:
                fields = tool.args_schema.model_fields
                param_lines = []
                for fname, finfo in fields.items():
                    ftype = finfo.annotation.__name__ if hasattr(finfo.annotation, '__name__') else str(finfo.annotation)
                    fdesc = finfo.description or "No description"
                    param_lines.append(f"    - {fname} ({ftype}): {fdesc}")
                if param_lines:
                    params_str = "\n" + "\n".join(param_lines)

            spec = (
                f"Tool: {tool.name}\n"
                f"  Description: {tool.description}\n"
                f"  Parameters: {params_str}\n"
                f"  Returns: string"
            )
            specs.append(spec)

        return "\n\n".join(specs)
