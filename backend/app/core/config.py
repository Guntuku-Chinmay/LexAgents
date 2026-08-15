import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # LLM & Embedding Settings
    OPENAI_API_KEY: str = Field(default="mock-key-for-testing")
    OPENAI_API_BASE: str = Field(default="https://api.openai.com/v1")
    LLM_MODEL: str = Field(default="gpt-4o-mini")
    EMBEDDING_MODEL: str = Field(default="text-embedding-3-small")

    # Storage Settings
    QDRANT_STORAGE_PATH: str = Field(default="data/qdrant_db")
    SQLITE_DB_PATH: str = Field(default="backend/app/database/lexagents.db")

    # API Settings
    PORT: int = Field(default=8000)
    HOST: str = Field(default="127.0.0.1")
    DEBUG: bool = Field(default=True)
    
    # Web Search Toggle
    WEB_SEARCH_ENABLED: bool = Field(default=True)

    # Config model for Pydantic v2
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure necessary directories exist
os.makedirs(os.path.dirname(settings.SQLITE_DB_PATH), exist_ok=True)
os.makedirs(settings.QDRANT_STORAGE_PATH, exist_ok=True)
os.makedirs("data/corpus/cases", exist_ok=True)
os.makedirs("data/corpus/statutes", exist_ok=True)
os.makedirs("data/benchmark", exist_ok=True)
os.makedirs("experiments/results", exist_ok=True)
