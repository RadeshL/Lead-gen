from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    DEBUG: bool = False
    GOOGLE_CSE_API_KEY: str = "AIzaSyBp-smFHf_rZ7xgFekZo3n1Ht-mUHU1Tbc"
    GOOGLE_CSE_ID: str = "20f03f873f34f4634"
    class Config:
        env_file = ".env"

settings = Settings()