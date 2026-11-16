"""Typed application configuration using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Centralized runtime settings loaded from environment or .env."""

    model_config = SettingsConfigDict(
        env_file=(str(_ROOT_ENV), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Gardoon Multi-Agent Quant & Compliance Studio"
    app_env: str = Field(default="production", alias="APP_ENV")

    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_fast_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_FAST_MODEL")
    gemini_reasoning_model: str = Field(default="gemini-2.5-pro", alias="GEMINI_REASONING_MODEL")
    gemini_embedding_model: str = Field(
        default="models/gemini-embedding-001", alias="GEMINI_EMBEDDING_MODEL"
    )

    qdrant_url: str = Field(default="", alias="QDRANT_URL")
    qdrant_collection: str = Field(
        default="tradingtackle_enterprise_kb", alias="QDRANT_COLLECTION"
    )

    postgres_dsn: str = Field(default="", alias="POSTGRES_DSN")

    k8s_namespace: str = Field(default="gardoon-ai-prod", alias="K8S_NAMESPACE")
    k8s_pod_name: str = Field(default="agent-orchestrator-01", alias="K8S_POD_NAME")
    k8s_node_name: str = Field(default="eu-central-worker-01", alias="K8S_NODE_NAME")
    cluster_topology: str = Field(default="docker-shared-net", alias="CLUSTER_TOPOLOGY")

    rate_limit_max_requests_per_hour: int = Field(
        default=15, alias="RATE_LIMIT_MAX_REQUESTS_PER_HOUR"
    )
    max_input_chars: int = Field(default=2400, alias="MAX_INPUT_CHARS")
    max_correction_loops: int = Field(default=2, alias="MAX_CORRECTION_LOOPS")
    cors_allowed_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000,https://agents.gardoon.ltd,https://gardoon.ltd",
        alias="CORS_ALLOWED_ORIGINS",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached singleton settings instance."""
    return Settings()
