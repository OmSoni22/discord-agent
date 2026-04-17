"""Discord AI Agent — application entrypoint."""

import logging

from app.bootstrap import create_agent_runner
from app.config.settings import settings
from app.discord_bot.bot import bot

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Starting %s...", settings.app_name)

    # Create and wire all components (tools → assembler → runner → bot)
    create_agent_runner()

    logger.info("All components initialized. Starting Discord bot...")
    bot.run(settings.discord_bot_token)


if __name__ == "__main__":
    main()
