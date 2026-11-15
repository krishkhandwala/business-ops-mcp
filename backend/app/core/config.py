import os
import base64
import hashlib
from typing import List
from pydantic import BaseModel


class Settings(BaseModel):
    APP_NAME: str = os.getenv("APP_NAME", "NEXUS")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    API_V1_PREFIX: str = os.getenv("API_V1_PREFIX", "/api/v1")

    BACKEND_HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
    CORS_ORIGINS: List[str] = [
        o.strip()
        for o in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001",
        ).split(",")
        if o.strip()
    ]

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/nexus_ops",
    )
    FALLBACK_SQLITE_URL: str = os.getenv(
        "FALLBACK_SQLITE_URL", "sqlite:///./nexus_ops.db"
    )

    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv(
        "CELERY_RESULT_BACKEND", "redis://localhost:6379/1"
    )

    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        "nexus-enterprise-jwt-signing-secret-key-production-ready-2026-v1",
    )
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120")
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    ENCRYPTION_MASTER_KEY: str = os.getenv(
        "ENCRYPTION_MASTER_KEY",
        "nexus-default-encryption-seed-for-local-dev-environment-2026",
    )

    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai_compatible")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.0"))
    MAX_TOOL_INVOCATIONS_PER_RUN: int = int(
        os.getenv("MAX_TOOL_INVOCATIONS_PER_RUN", "10")
    )
    TOOL_EXECUTION_TIMEOUT_SECONDS: int = int(
        os.getenv("TOOL_EXECUTION_TIMEOUT_SECONDS", "30")
    )

    MCP_INTERNAL_AUTH_TOKEN: str = os.getenv(
        "MCP_INTERNAL_AUTH_TOKEN", "nexus-mcp-internal-shared-secret-token-2026"
    )

    OTEL_ENABLED: bool = os.getenv("OTEL_ENABLED", "true").lower() == "true"
    OTEL_SERVICE_NAME: str = os.getenv("OTEL_SERVICE_NAME", "nexus-ops-backend")

    def get_fernet_key(self) -> bytes:
        raw = self.ENCRYPTION_MASTER_KEY.encode("utf-8")
        digest = hashlib.sha256(raw).digest()
        return base64.urlsafe_b64encode(digest)


settings = Settings()

