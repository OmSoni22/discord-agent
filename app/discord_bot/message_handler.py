"""Discord message handler — fetches history, calls agent, sends response."""

from __future__ import annotations

import logging

import discord
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from app.agent.runner import AgentRunner
from app.config.settings import settings
from app.discord_bot.formatter import format_response

logger = logging.getLogger(__name__)


async def handle_message(
    message: discord.Message,
    agent_runner: AgentRunner | None,
) -> None:
    """Process a Discord message through the agent and send the response.

    1. Fetch the last DISCORD_HISTORY_LIMIT messages before this one
    2. Convert them to LangChain BaseMessages (oldest first)
    3. Run the agent with the current message as the query
    4. Split and send the response respecting Discord's 2000-char limit

    Args:
        message:      The incoming Discord message (the current user query)
        agent_runner: The initialized AgentRunner — if None, sends an error
    """
    if agent_runner is None:
        logger.error("agent_runner is None — was bootstrap.py called before bot.run()?")
        await message.channel.send(
            "⚠️ Agent not initialized. Please restart the bot."
        )
        return

    logger.info(
        "Handling message | channel=%s | author=%s | content=%s",
        message.channel.id,
        message.author.name,
        message.content[:80],
    )

    # ── Build history from Discord channel ────────────────────────────────────
    # Fetch messages sent *before* this one (excludes the current message).
    # Discord returns them newest-first, so we reverse to get chronological order.
    history: list[BaseMessage] = []

    async for past_msg in message.channel.history(
        limit=settings.discord_history_limit,
        before=message,
    ):
        if not past_msg.content:
            continue  # skip empty messages (e.g. embeds-only)
        if past_msg.author.bot:
            history.append(AIMessage(content=past_msg.content))
        else:
            history.append(HumanMessage(content=past_msg.content))

    history.reverse()  # oldest → newest (correct LLM input order)

    logger.debug("History built | %d messages", len(history))

    # ── Run the agent ─────────────────────────────────────────────────────────
    try:
        response = await agent_runner.run(
            query=message.content,
            history=history,
        )
    except Exception as e:
        logger.exception("Agent run failed: %s", e)
        await message.channel.send(
            f"⚠️ Something went wrong while processing your request: `{e}`"
        )
        return

    if not response:
        response = "(No response generated)"

    # ── Send response (split if > 2000 chars) ─────────────────────────────────
    chunks = format_response(response)
    for chunk in chunks:
        await message.channel.send(chunk)

    logger.info("Response sent | %d chunk(s) | total_chars=%d", len(chunks), len(response))
