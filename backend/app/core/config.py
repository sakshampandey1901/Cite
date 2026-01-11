"""Application configuration using Pydantic settings."""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True
    ENVIRONMENT: str = "development"

    # Security
    SECRET_KEY: str  # Must be set in .env file
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Vector Database
    PINECONE_API_KEY: str
    PINECONE_CLOUD: str = "gcp"
    PINECONE_ENVIRONMENT: str = "us-west1-gcp"
    PINECONE_INDEX_NAME: str = "cognitive-assistant"

    # LLM Provider
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama3-8b-8192"

    # Embedding Provider
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # File Upload
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: str = "pdf,txt,md,srt,vtt"
    UPLOAD_DIR: str = "/tmp/uploads"

    # Rate Limiting
    RATE_LIMIT_UPLOAD: str = "10/hour"
    RATE_LIMIT_ASSIST: str = "30/hour"

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Monitoring
    SENTRY_DSN: str = ""
    LOG_LEVEL: str = "INFO"

    @property
    def allowed_extensions_list(self) -> List[str]:
        """Get allowed file extensions as a list."""
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(',')]

    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(',')]

    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes."""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
