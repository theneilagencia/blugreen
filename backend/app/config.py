import json
from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    app_name: str = "Blugreen Autonomous Engineering Platform"
    debug: bool = False
    database_url: str = "sqlite:///./blugreen.db"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"
    
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
        """Parse CORS_ORIGINS from comma-separated string or JSON array."""
        v = self.cors_origins_raw
        if isinstance(v, str):
            # Try to parse as JSON first
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
            # If not JSON, split by comma
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return [v]


@lru_cache
def get_settings() -> Settings:
    return Settings()
