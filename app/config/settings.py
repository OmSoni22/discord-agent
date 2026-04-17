"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """Central configuration for the Discord AI Agent."""

    # Application
    app_name: str = "Discord-Agent"
    debug: bool = False
    log_level: str = "INFO"

    # LLM Configuration
    model_provider: str = "groq"
    model_name: str = "llama-3.3-70b-versatile"
    api_key: str = ""                # API key for the provider
    llm_base_url: str | None = None  # Base URL (e.g., https://openrouter.ai/api/v1)
    max_tokens: int = 4096

    # Agent loop guards
    max_iterations: int = 10
    max_execution_time: int = 60  # seconds

    # Discord
    discord_bot_token: str = ""
    discord_history_limit: int = 20          # last N messages fetched as context
    discord_allowed_channel_ids: str = ""    # comma-separated channel IDs; empty = all

    # Notion
    notion_api_key: str = ""
    notion_default_page_id: str = ""         # fallback parent for create_page

    model_config = ConfigDict(env_file=".env")


settings = Settings()
