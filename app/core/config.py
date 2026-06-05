from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "SmartBiz API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/smartbiz"
    AI_PROVIDER: str = "claude"
    AI_REQUEST_TIMEOUT_SECONDS: int = 60
    OLLAMA_MODEL_NAME: str = "llama3.1"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    CLAUDE_MODEL_NAME: str = "claude-sonnet-4-20250514"
    ANTHROPIC_API_KEY: str | None = None

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str) and value.lower() in {
            "release",
            "production",
            "prod",
        }:
            return False
        return value

    @field_validator("AI_PROVIDER", mode="before")
    @classmethod
    def parse_ai_provider(cls, value):
        if isinstance(value, str):
            return value.strip().lower()
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
