"""Prompt Builder — converts ContextObject into LangChain message format."""

from __future__ import annotations

import logging

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage, BaseMessage

from app.agent.context_assembler import ContextObject
from app.threads.models import Message

logger = logging.getLogger(__name__)


class PromptBuilder:
    """Converts a ContextObject into a list of LangChain BaseMessage objects.

    The system prompt (identity + rules + tool specs) is placed first as a
    SystemMessage. The SYSTEM_PROMPT_DYNAMIC_BOUNDARY splits static vs dynamic
    content so prompt caching works correctly.
    """

    def build(self, context: ContextObject) -> list[BaseMessage]:
        """Build the message list for the LLM.

        Args:
            context: Assembled ContextObject

        Returns:
            List of LangChain messages ready for the model
        """
        messages: list[BaseMessage] = []

        # 1. System message (static part — cached by the LLM provider)
        system_content = context.system_prompt
        if context.rules:
            system_content += f"\n\nRules:\n{context.rules}"

        messages.append(SystemMessage(content=system_content))

        # 2. Chat history (dynamic part — after the boundary)
        for msg in context.chat_history:
            messages.append(self._convert_message(msg))

        # 3. Current user query
        messages.append(HumanMessage(content=context.user_query))

        logger.debug("Built %d messages for LLM", len(messages))
        return messages

    @staticmethod
    def _convert_message(msg: Message) -> BaseMessage:
        """Convert a DB Message to a LangChain BaseMessage."""
        if msg.role == "human":
            return HumanMessage(content=msg.content)
        elif msg.role == "ai":
            return AIMessage(content=msg.content)
        elif msg.role == "tool":
            return ToolMessage(
                content=msg.content,
                tool_call_id=msg.tool_call_id or "unknown",
            )
        elif msg.role == "system":
            return SystemMessage(content=msg.content)
        else:
            return HumanMessage(content=msg.content)
