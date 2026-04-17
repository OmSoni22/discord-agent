"""Prompt Builder — converts a ContextObject into LangChain message format."""

from __future__ import annotations

import logging

from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage

from app.agent.context_assembler import ContextObject

logger = logging.getLogger(__name__)


class PromptBuilder:
    """Converts a ContextObject into a list of LangChain BaseMessage objects.

    Layout:
    [0]   SystemMessage  — system prompt + rules (static, cache-friendly)
    [1..N-1] BaseMessage — prior conversation history (already LangChain format)
    [N]   HumanMessage  — current user query
    """

    def build(self, context: ContextObject) -> list[BaseMessage]:
        """Build the message list for the LLM.

        Args:
            context: Assembled ContextObject from ContextAssembler

        Returns:
            Ordered list of LangChain messages ready for the model
        """
        messages: list[BaseMessage] = []

        # 1. System message (static — cache-friendly for LLM providers)
        system_content = context.system_prompt
        if context.rules:
            system_content += f"\n\nRules:\n{context.rules}"

        messages.append(SystemMessage(content=system_content))

        # 2. Conversation history (already BaseMessage objects from Discord)
        messages.extend(context.chat_history)

        # 3. Current user query
        messages.append(HumanMessage(content=context.user_query))

        logger.debug("Built %d messages for LLM", len(messages))
        return messages
