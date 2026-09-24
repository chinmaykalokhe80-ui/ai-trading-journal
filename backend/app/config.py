import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Indian Equity & F&O Trading Journal API"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "trading_journal.db")
    FIREBASE_SERVICE_ACCOUNT_PATH: str = os.getenv(
        "FIREBASE_SERVICE_ACCOUNT_PATH", ""
    )
    KITE_API_KEY: str = os.getenv("KITE_API_KEY", "")
    KITE_API_SECRET: str = os.getenv("KITE_API_SECRET", "")

    class Config:
        env_file = ".env"


settings = Settings()
