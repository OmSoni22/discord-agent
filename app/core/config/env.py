"""Environment configuration validation."""

from typing import List
from app.core.config.settings import settings
from app.core.logging.logger import add_to_log


class ConfigValidator:
    """Validates required configuration on startup."""
    
    @staticmethod
    def validate() -> None:
        """
        Validate all required configuration.
        
        Raises:
            ValueError: If required configuration is missing or invalid
        """
        errors: List[str] = []
        
        # Validate database URL
        if not settings.database_url:
            errors.append("DATABASE_URL is required")
        elif not settings.database_url.startswith(("postgresql", "sqlite")):
            errors.append("DATABASE_URL must be PostgreSQL or SQLite")
            

        # Validate log settings
        if not settings.log_dir:
            errors.append("LOG_DIR is required")
            
        if settings.log_level.upper() not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            errors.append(f"Invalid LOG_LEVEL: {settings.log_level}")
            
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            add_to_log("error", error_msg)
            raise ValueError(error_msg)
            
        add_to_log("info", "Configuration validation passed")


def validate_config() -> None:
    """Convenience function to validate configuration."""
    ConfigValidator.validate()
