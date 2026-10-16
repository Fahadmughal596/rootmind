from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "RootMind"
    app_env: str = "development"
    database_url: str = "sqlite:///./rootmind.db"
    github_token: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings():
    return Settings()

settings = get_settings()
