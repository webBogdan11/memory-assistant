import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    OPENAI_API_KEY: str

    MONGO_DATABASE_HOST: str = "mongodb://localhost:27017"
    MONGO_DATABASE_NAME: str = "ai-memory-assistant"

    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str
    AWS_BUCKET_NAME: str

    PASSWORD: str
settings = Settings()
