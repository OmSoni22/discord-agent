"""Context Assembler — builds the full context object before each LLM call."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from langchain_core.messages import BaseMessage
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# Path to config files (relative to this file)
_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


@dataclass
class ContextObject:
    """Assembled context ready for the PromptBuilder."""
    system_prompt: str
    rules: str
    tool_specs: str
    chat_history: list[BaseMessage]   # Already-converted LangChain messages
    user_query: str
    role: str = "primary"             # Reserved for multi-agent (always "primary" in v1)


class ContextAssembler:
    """Assembles a complete ContextObject from all sources.

    Reads static config files (system prompt, rules), generates tool specs
    from the registry, and combines with pre-built history + current query.

    History is passed in as a list[BaseMessage] — the Discord layer is
    responsible for converting Discord messages to LangChain format.
    """

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self._tool_registry = tool_registry
        self._system_prompt_template: str | None = None
        self._rules: str | None = None

    def _load_file(self, filename: str) -> str:
        """Load a text file from the config directory."""
        path = _CONFIG_DIR / filename
        if not path.exists():
            logger.warning("Config file not found: %s", path)
            return ""
        return path.read_text(encoding="utf-8").strip()

    def _get_system_prompt_template(self) -> str:
        """Load and cache the system prompt template."""
        if self._system_prompt_template is None:
            self._system_prompt_template = self._load_file("system_prompt.txt")
        return self._system_prompt_template

    def _get_rules(self) -> str:
        """Load and cache the rules."""
        if self._rules is None:
            self._rules = self._load_file("rules.txt")
        return self._rules

    def assemble(
        self,
        messages: list[BaseMessage],
        query: str,
        role: str = "primary",
    ) -> ContextObject:
        """Assemble the full context for a single LLM turn.

        Args:
            messages: Prior conversation history as LangChain BaseMessages
                      (converted by the Discord layer from channel.history())
            query:    The current user message text
            role:     Agent role — reserved for multi-agent, default "primary"

        Returns:
            ContextObject ready for PromptBuilder
        """
        logger.info("Assembling context | history_len=%d | query=%s", len(messages), query[:80])

        tool_specs = self._tool_registry.generate_specs()
        system_prompt_template = self._get_system_prompt_template()

        system_prompt = system_prompt_template.replace("{tool_specs}", tool_specs)

        # Inject dynamic date and time (UTC)
        from datetime import datetime, timezone
        current_time = datetime.now(timezone.utc).strftime("%A, %Y-%m-%d %H:%M:%S UTC")
        system_prompt += f"\n\nCurrent Date and Time: {current_time}"

        return ContextObject(
            system_prompt=system_prompt,
            rules=self._get_rules(),
            tool_specs=tool_specs,
            chat_history=messages,
            user_query=query,
            role=role,
        )
