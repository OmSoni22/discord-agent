"""Agent Runner — orchestrates the LangChain ReAct loop."""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.messages import BaseMessage, AIMessage, ToolMessage
from langchain_core.tools import BaseTool

from app.agent.context_assembler import ContextAssembler
from app.agent.prompt_builder import PromptBuilder
from app.config.settings import settings
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class AgentRunner:
    """Orchestrates the ReAct loop and returns the final response as a string.

    Stateless — receives pre-built conversation history (list[BaseMessage])
    from the Discord layer on every call. No database dependency.
    Injectable — not a singleton, can be instantiated multiple times.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        context_assembler: ContextAssembler,
        prompt_builder: PromptBuilder,
    ) -> None:
        self._tool_registry = tool_registry
        self._context_assembler = context_assembler
        self._prompt_builder = prompt_builder

        model_kwargs: dict[str, Any] = {"streaming": True}
        if settings.max_tokens:
            model_kwargs["max_tokens"] = settings.max_tokens
        if settings.api_key:
            model_kwargs["api_key"] = settings.api_key

        self._llm = init_chat_model(
            model=settings.model_name,
            model_provider=settings.model_provider,
            **model_kwargs,
        )

    async def run(self, query: str, history: list[BaseMessage]) -> str:
        """Run the ReAct loop and return the final text response.

        Args:
            query:   The current user message text
            history: Prior conversation as LangChain BaseMessages
                     (built by the Discord layer from channel.history())

        Returns:
            The agent's final response as a plain string
        """
        logger.info("Agent run started | query=%s", query[:100])

        # Bind tools to the LLM
        tools = self._tool_registry.get_all()
        tools_by_name: dict[str, BaseTool] = {t.name: t for t in tools}
        llm_with_tools = self._llm.bind_tools(tools) if tools else self._llm

        # Assemble context and build message list
        context = self._context_assembler.assemble(history, query)
        messages = self._prompt_builder.build(context)

        final_response = ""
        iteration = 0

        for iteration in range(1, settings.max_iterations + 1):
            logger.info("ReAct iteration %d", iteration)

            full_content = ""
            tool_calls: list[dict] = []

            # Stream LLM response
            async for chunk in llm_with_tools.astream(messages):
                # Collect text content
                if chunk.content:
                    if isinstance(chunk.content, str):
                        full_content += chunk.content
                    elif isinstance(chunk.content, list):
                        for block in chunk.content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                full_content += block.get("text", "")

                # Collect tool calls (fully-resolved chunks)
                if hasattr(chunk, "tool_calls") and chunk.tool_calls:
                    tool_calls.extend(chunk.tool_calls)

            # No tool calls → final answer
            if not tool_calls:
                final_response = full_content
                logger.info("Agent finished in %d iteration(s)", iteration)
                break

            # Append AI message with tool call intent
            ai_message = AIMessage(content=full_content, tool_calls=tool_calls)
            messages.append(ai_message)

            # Execute each tool call
            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_call_id = tool_call.get("id", tool_name)

                logger.info(
                    "Executing tool: %s | args: %s",
                    tool_name,
                    json.dumps(tool_args)[:200],
                )

                tool = tools_by_name.get(tool_name)
                if tool:
                    try:
                        result = await tool.ainvoke(tool_args)
                        tool_output = str(result)
                    except Exception as e:
                        tool_output = f"Error executing {tool_name}: {e}"
                        logger.error("Tool execution failed: %s — %s", tool_name, e)
                else:
                    tool_output = f"Error: Unknown tool '{tool_name}'"
                    logger.error("Unknown tool requested: %s", tool_name)

                messages.append(
                    ToolMessage(content=tool_output, tool_call_id=tool_call_id)
                )

        else:
            # Max iterations reached — return whatever we last generated
            logger.warning("Max iterations (%d) reached", settings.max_iterations)
            final_response = (
                full_content
                + "\n\n*(Reached maximum reasoning steps — this is my best answer so far.)*"
            )

        logger.info("Agent run complete | iterations=%d", iteration)
        return final_response
