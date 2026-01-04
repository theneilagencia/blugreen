import json
import logging
from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    app_name: str = "Blugreen Autonomous Engineering Platform"
    debug: bool = False
    database_url: str = "sqlite:///./blugreen.db"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama2:latest"
    
    @computed_field
    @property
    def ollama_url(self) -> str:
        """Alias for ollama_base_url for backward compatibility."""
        return self.ollama_base_url
    workspace_root: str = "/tmp/blugreen_workspaces"
    cors_origins_raw: str = "http://localhost:3000"
    coolify_url: str = ""
    coolify_token: str = ""

    @computed_field
    @property
    def cors_origins(self) -> list[str]:
        """Parse CORS_ORIGINS from comma-separated string or JSON array.
        
        Supports:
        - JSON array: '["https://example.com", "https://app.example.com"]'
        - Comma-separated: 'https://example.com,https://app.example.com'
        
        Raises:
            ValueError: If CORS_ORIGINS is empty in production mode
        """
        v = self.cors_origins_raw
        origins: list[str] = []
        
        if isinstance(v, str):
            # Try to parse as JSON first
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    origins = [str(origin).strip() for origin in parsed if origin]
                else:
                    logger.warning(f"CORS_ORIGINS_RAW is JSON but not a list: {type(parsed)}")
            except (json.JSONDecodeError, ValueError):
                # If not JSON, split by comma
                origins = [origin.strip() for origin in v.split(",") if origin.strip()]
        else:
            origins = [str(v)]
        
        # Validation: CORS_ORIGINS cannot be empty in production
        if not origins and not self.debug:
            raise ValueError(
                "CORS_ORIGINS cannot be empty in production mode. "
                "Set CORS_ORIGINS_RAW environment variable to a comma-separated list or JSON array. "
                "Example: 'https://app.example.com,https://example.com' or "
                "'[\"https://app.example.com\", \"https://example.com\"]'"
            )
        
        # Log loaded origins for debugging
        if origins:
            logger.info(f"CORS origins loaded: {origins}")
        else:
            logger.warning("CORS origins list is empty (debug mode)")
        
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
