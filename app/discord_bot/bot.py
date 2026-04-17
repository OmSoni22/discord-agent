"""Discord client setup and event handlers."""

from __future__ import annotations

import logging

import discord

from app.agent.runner import AgentRunner
from app.config.settings import settings
from app.discord_bot.message_handler import handle_message

logger = logging.getLogger(__name__)

# ── Client setup ─────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True          # Required to read message text
                                        # Must also be enabled in Discord Developer Portal

bot = discord.Client(intents=intents)

# Module-level reference to the AgentRunner (set by bootstrap before bot.run())
_agent_runner: AgentRunner | None = None


def set_agent_runner(runner: AgentRunner) -> None:
    """Wire the AgentRunner into the bot (called from bootstrap.py)."""
    global _agent_runner
    _agent_runner = runner


# ── Event handlers ────────────────────────────────────────────────────────────

@bot.event
async def on_ready() -> None:
    """Called when the bot has connected to Discord."""
    logger.info("Discord bot ready | logged in as %s (ID: %s)", bot.user, bot.user.id)
    if settings.discord_allowed_channel_ids:
        logger.info(
            "Restricted to channels: %s", settings.discord_allowed_channel_ids
        )
    else:
        logger.info("Listening on all channels")


@bot.event
async def on_message(message: discord.Message) -> None:
    """Called for every message sent in any channel the bot can see."""

    # Never respond to ourselves — prevents infinite loops
    if message.author == bot.user:
        return

    # Channel filter — if configured, only respond in listed channels
    if settings.discord_allowed_channel_ids:
        allowed_ids = [
            cid.strip()
            for cid in settings.discord_allowed_channel_ids.split(",")
            if cid.strip()
        ]
        if allowed_ids and str(message.channel.id) not in allowed_ids:
            return

    # Show "Bot is typing..." indicator while the agent works
    async with message.channel.typing():
        await handle_message(message, _agent_runner)


@bot.event
async def on_error(event: str, *args, **kwargs) -> None:
    """Log unhandled Discord errors without crashing the bot."""
    logger.exception("Unhandled Discord error in event '%s'", event)
