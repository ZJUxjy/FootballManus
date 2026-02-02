"""Configuration management for FM Manager."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "FM Manager"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False, alias="DEBUG")

    # Database
    database_url: str = Field(
        default=f"sqlite+aiosqlite:///{DATA_DIR}/fm_manager.db",
        alias="DATABASE_URL",
    )
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")

    # Server
    server_host: str = Field(default="0.0.0.0", alias="SERVER_HOST")
    server_port: int = Field(default=8000, alias="SERVER_PORT")
    server_reload: bool = Field(default=False, alias="SERVER_RELOAD")

    # LLM Configuration
    llm_provider: Literal["openai", "anthropic", "custom"] = Field(
        default="openai",
        alias="LLM_PROVIDER",
    )
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_base_url: str = Field(default="", alias="LLM_BASE_URL")
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    llm_temperature: float = Field(default=0.7, alias="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=2000, alias="LLM_MAX_TOKENS")
    llm_timeout: int = Field(default=60, alias="LLM_TIMEOUT")

    # Game Settings
    game_speed: int = Field(default=1, alias="GAME_SPEED")  # Days per second
    match_simulation_speed: float = Field(
        default=1.0,
        alias="MATCH_SIMULATION_SPEED",
    )

    # External APIs
    football_data_api_key: str = Field(default="", alias="FOOTBALL_DATA_API_KEY")
    api_football_key: str = Field(default="", alias="API_FOOTBALL_KEY")

    @property
    def database_path(self) -> Path:
        """Get the database file path from URL."""
        if self.database_url.startswith("sqlite"):
            # Extract path from sqlite+aiosqlite:///path/to/db
            path_str = self.database_url.replace("sqlite+aiosqlite://", "").replace(
                "sqlite://", ""
            )
            # Handle absolute vs relative paths
            if path_str.startswith("/"):
                return Path(path_str)
            return PROJECT_ROOT / path_str
        return DATA_DIR / "fm_manager.db"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
