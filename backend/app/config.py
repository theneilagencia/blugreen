from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Blugreen Autonomous Engineering Platform"
    debug: bool = False
    database_url: str = "sqlite:///./blugreen.db"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    cors_origins: list[str] = ["http://localhost:3000"]
    coolify_url: str = ""
    coolify_token: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
