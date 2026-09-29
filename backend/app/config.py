import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Indian Equity & F&O Trading Journal API"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "trading_journal.db")
    FIREBASE_SERVICE_ACCOUNT_PATH: str = os.getenv(
        "FIREBASE_SERVICE_ACCOUNT_PATH", ""
    )
    KITE_API_KEY: str = os.getenv("KITE_API_KEY", "")
    KITE_API_SECRET: str = os.getenv("KITE_API_SECRET", "")

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "qwen/qwen3.8-27b"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "openrouter/free"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
