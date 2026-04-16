"""Agent Runner — orchestrates the LangChain ReAct loop with streaming."""

from __future__ import annotations

import json
import logging
from typing import AsyncGenerator, Any

from langchain.chat_models import init_chat_model
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import BaseTool

from app.agent.context_assembler import ContextAssembler
from app.agent.prompt_builder import PromptBuilder
from app.config.settings import settings
from app.threads.thread_store import ThreadStore
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class AgentRunner:
    """Orchestrates the ReAct loop.

    Stateless — all state lives in ThreadStore (PostgreSQL).
    Importable as a class so an orchestrator can instantiate N of them.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        thread_store: ThreadStore,
        context_assembler: ContextAssembler,
        prompt_builder: PromptBuilder,
    ) -> None:
        self._tool_registry = tool_registry
        self._thread_store = thread_store
        self._context_assembler = context_assembler
        self._prompt_builder = prompt_builder

        # Initialize the LLM dynamically based on the configured provider
        model_kwargs = {
            "streaming": True,
        }
        
        # We handle max_tokens here for providers that support it directly.
        # Alternatively, init_chat_model handles model-provider mapping well.
        if settings.max_tokens:
            model_kwargs["max_tokens"] = settings.max_tokens

        # Inject the generic API key
        if settings.api_key:
            model_kwargs["api_key"] = settings.api_key
            
        self._llm = init_chat_model(
            model=settings.model_name,
            model_provider=settings.model_provider,
            **model_kwargs
        )

    async def run(
        self,
        thread_id: str,
        query: str,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Run the ReAct loop for a query, yielding SSE event dicts.

        Args:
            thread_id: Thread ID (must exist — created via API first)
            query: User's query

        Yields:
            Dict events for the SSE handler to format
        """
        logger.info("Agent run started | thread=%s | query=%s", thread_id, query[:100])

        # Yield thread info
        yield {
            "type": "thread_info",
            "thread_id": thread_id,
            "source_agent": "primary",
        }

        # Persist the user's query
        await self._thread_store.add_message(thread_id, "human", query)

        # Load full chat history from DB
        db_messages = await self._thread_store.get_messages(thread_id)

        # Bind tools to the LLM
        tools = self._tool_registry.get_all()
        tools_by_name: dict[str, BaseTool] = {t.name: t for t in tools}
        llm_with_tools = self._llm.bind_tools(tools) if tools else self._llm

        # Assemble context and build messages
        context = self._context_assembler.assemble(thread_id, db_messages, query)
        messages = self._prompt_builder.build(context)

        iteration = 0

        while iteration < settings.max_iterations:
            iteration += 1
            logger.info("ReAct iteration %d | thread=%s", iteration, thread_id)

            # Stream LLM response
            full_content = ""
            tool_calls = []

            yield {"type": "content_block_start", "block_type": "text", "source_agent": "primary"}

            async for chunk in llm_with_tools.astream(messages):
                # Text content
                if chunk.content:
                    if isinstance(chunk.content, str):
                        full_content += chunk.content
                        yield {
                            "type": "text_delta",
                            "delta": chunk.content,
                            "source_agent": "primary",
                        }
                    elif isinstance(chunk.content, list):
                        for block in chunk.content:
                            if isinstance(block, dict):
                                if block.get("type") == "text":
                                    text = block.get("text", "")
                                    full_content += text
                                    yield {
                                        "type": "text_delta",
                                        "delta": text,
                                        "source_agent": "primary",
                                    }
                                elif block.get("type") == "thinking":
                                    yield {
                                        "type": "thinking_delta",
                                        "delta": block.get("thinking", ""),
                                        "source_agent": "primary",
                                    }

                # Tool calls
                if hasattr(chunk, "tool_calls") and chunk.tool_calls:
                    tool_calls.extend(chunk.tool_calls)

                if hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks:
                    for tc_chunk in chunk.tool_call_chunks:
                        yield {
                            "type": "input_json_delta",
                            "tool_name": tc_chunk.get("name", ""),
                            "delta": tc_chunk.get("args", ""),
                            "source_agent": "primary",
                        }

            yield {"type": "content_block_stop", "source_agent": "primary"}

            # If no tool calls, we're done — final answer
            if not tool_calls:
                # Persist AI response
                await self._thread_store.add_message(thread_id, "ai", full_content)
                yield {
                    "type": "message_delta",
                    "stop_reason": "end_turn",
                    "source_agent": "primary",
                }
                break

            # Execute tool calls
            ai_message = AIMessage(content=full_content, tool_calls=tool_calls)
            messages.append(ai_message)

            # Persist AI message (with tool call intent)
            await self._thread_store.add_message(thread_id, "ai", full_content)

            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_call_id = tool_call.get("id", tool_name)

                logger.info("Executing tool: %s | args: %s", tool_name, json.dumps(tool_args)[:200])

                yield {
                    "type": "tool_start",
                    "tool_name": tool_name,
                    "tool_input": tool_args,
                    "source_agent": "primary",
                }

                # Execute the tool
                tool = tools_by_name.get(tool_name)
                if tool:
                    try:
                        result = await tool.ainvoke(tool_args)
                        tool_output = str(result)
                    except Exception as e:
                        tool_output = f"Error executing {tool_name}: {e}"
                        logger.error("Tool execution failed: %s - %s", tool_name, e)
                else:
                    tool_output = f"Error: Unknown tool '{tool_name}'"
                    logger.error("Unknown tool requested: %s", tool_name)

                yield {
                    "type": "tool_result",
                    "tool_name": tool_name,
                    "output": tool_output,
                    "source_agent": "primary",
                }

                # Persist tool result
                await self._thread_store.add_message(
                    thread_id,
                    "tool",
                    tool_output,
                    tool_call_id=tool_call_id,
                    tool_name=tool_name,
                    tool_input=tool_args,
                )

                # Append tool result for next LLM iteration
                from langchain_core.messages import ToolMessage
                messages.append(ToolMessage(content=tool_output, tool_call_id=tool_call_id))

        else:
            # Max iterations reached
            logger.warning("Max iterations reached for thread %s", thread_id)
            warning_msg = "\n\nI've reached the maximum number of reasoning steps. Here's my best answer so far."
            yield {
                "type": "text_delta",
                "delta": warning_msg,
                "source_agent": "primary",
            }
            await self._thread_store.add_message(thread_id, "ai", warning_msg)
            yield {
                "type": "message_delta",
                "stop_reason": "max_iterations",
                "source_agent": "primary",
            }

        yield {"type": "message_stop", "source_agent": "primary"}
        logger.info("Agent run completed | thread=%s | iterations=%d", thread_id, iteration)
