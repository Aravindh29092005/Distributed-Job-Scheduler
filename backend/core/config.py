"""Application configuration loaded from environment variables."""

import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # Application
    PROJECT_NAME: str = "Distributed Job Scheduling Platform"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=False)
    LOG_LEVEL: str = "INFO"
    JSON_LOGS: bool = Field(default=True)

    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/codity"
    )
    SYNC_DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/codity"
    )
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_PRE_PING: bool = True
    DB_ECHO: bool = False

    # Security & Authentication
    SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production-use-env-var"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: list = Field(default=["http://localhost:5173", "http://localhost:3000"])
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = Field(default=["*"])
    CORS_ALLOW_HEADERS: list = Field(default=["*"])

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_TOKENS_PER_MINUTE: int = 1000

    # Worker Settings
    WORKER_NAME: str = Field(default=f"worker-{os.getenv('HOSTNAME', 'local')}")
    WORKER_HOST: str = Field(default="localhost")
    WORKER_PORT: int = 8001
    WORKER_TAGS: dict = Field(default_factory=dict)
    WORKER_MAX_CONCURRENT: int = 10
    WORKER_POLL_INTERVAL_SECONDS: float = 1.0
    WORKER_HEARTBEAT_INTERVAL_SECONDS: float = 5.0
    WORKER_HEARTBEAT_TIMEOUT_SECONDS: float = 20.0
    WORKER_GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS: float = 30.0
    WORKER_REAPER_INTERVAL_SECONDS: float = 10.0
    WORKER_REAPER_STALE_THRESHOLD_SECONDS: float = 30.0

    # Job Settings
    JOB_DEFAULT_TIMEOUT_SECONDS: int = 300
    JOB_MAX_TIMEOUT_SECONDS: int = 3600
    JOB_DEFAULT_MAX_RETRIES: int = 3
    JOB_DEFAULT_RETRY_STRATEGY: str = "exponential_jitter"

    # Scheduled Jobs (cron)
    SCHEDULED_JOBS_POLL_INTERVAL_SECONDS: float = 10.0

    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = Field(default=False)
    API_WORKERS: int = Field(default=4)

    # Observability
    METRICS_ENABLED: bool = True
    METRICS_PORT: int = 8002
    TRACING_ENABLED: bool = False
    TRACING_JAEGER_HOST: str = "localhost"
    TRACING_JAEGER_PORT: int = 6831

    # Pagination
    DEFAULT_PAGE_SIZE: int = 100
    MAX_PAGE_SIZE: int = 1000

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


settings = Settings()
