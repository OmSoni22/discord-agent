"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """Central configuration for the Agentic AI System."""

    # Application
    app_name: str = "Agentic-AI-System"
    debug: bool = False
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/agentic_ai"

    # LLM Configuration
    model_provider: str = "anthropic" # Supported: "anthropic", "google_genai", "openai", "ollama", etc.
    model_name: str = "claude-sonnet-4-6"
    max_tokens: int = 4096

    # API Key for the selected provider
    api_key: str = ""

    # Agent loop guards
    max_iterations: int = 10
    max_execution_time: int = 60  # seconds

    model_config = ConfigDict(env_file=".env")


settings = Settings()
