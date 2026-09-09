from pydantic_settings import BaseSettings
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"

class Settings(BaseSettings):
    DATABASE_URL: str
    DEBUG: bool = False
    GOOGLE_CSE_API_KEY: str | None = None
    GOOGLE_CSE_ID: str | None = None
    GEMINI_API_KEY: str | None = None

    class Config:
        env_file = ENV_FILE

settings = Settings()