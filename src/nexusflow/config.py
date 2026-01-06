"""
NexusFlow Configuration

Centralized configuration management using Pydantic Settings.
"""

from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Turing NexusFlow"
    app_version: str = "0.1.0"
    debug: bool = False

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, v: Any) -> bool:
        """Parse debug value, handling non-boolean strings."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return bool(v)
    log_level: str = "INFO"
    environment: str = "development"

    # API Configuration
    nexusflow_base_url: str = "http://localhost:8000"
    nexusflow_mcp_port: int = 8001

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment_name: str = "gpt-4o"
    azure_openai_chat_deployment_name: str = "gpt-4o-mini"
    azure_openai_api_version: str = "2024-08-01-preview"

    # OpenAI Direct
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"

    # Anthropic
    anthropic_api_key: str = ""

    # PostgreSQL Database
    database_url: str = "postgresql+asyncpg://nexusflow:nexusflow123@localhost:5432/nexusflow"

    # Neo4j Configuration (Community Edition uses default 'neo4j' database)
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "nexusflow123"
    neo4j_database: str = "neo4j"

    # Milvus Configuration
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_user: str = "root"
    milvus_password: str = ""
    milvus_collection: str = "nexusflow_tickets"

    # Phoenix Observability
    phoenix_host: str = "localhost"
    phoenix_port: int = 6006
    phoenix_grpc_port: int = 4317
    phoenix_project_name: str = "nexusflow"
    phoenix_enabled: bool = True

    # Authentication
    enable_auth: bool = False
    enable_test_auth_bypass: bool = True
    jwt_secret_key: str = "nexusflow-super-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    # Classification Configuration
    classification_confidence_threshold: float = 0.7
    hitl_threshold: float = 0.5
    batch_size: int = 50

    # Model Settings
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    nexusflow_default_model: str = "gpt-4o"

    @property
    def neo4j_url(self) -> str:
        """Get Neo4j connection URL."""
        return self.neo4j_uri

    @property
    def milvus_address(self) -> str:
        """Get Milvus connection address."""
        return f"{self.milvus_host}:{self.milvus_port}"

    @property
    def phoenix_endpoint(self) -> str:
        """Get Phoenix HTTP endpoint."""
        return f"http://{self.phoenix_host}:{self.phoenix_port}"

    @property
    def phoenix_grpc_endpoint(self) -> str:
        """Get Phoenix gRPC endpoint."""
        return f"{self.phoenix_host}:{self.phoenix_grpc_port}"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
