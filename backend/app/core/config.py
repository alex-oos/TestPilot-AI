import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # LLM Settings
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.openai.com/v1"  # Default to OpenAI URL format
    LLM_MODEL: str = "gpt-3.5-turbo" # Default model
    SQLITE_DB_PATH: str = "./data/app.db"
    JWT_SECRET_KEY: str = "please-change-this-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 15

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()
