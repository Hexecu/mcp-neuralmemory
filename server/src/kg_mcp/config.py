"""
Configuration management for MCP-KG-Memory server.
Uses pydantic-settings for environment variable handling.
"""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Neo4j Configuration
    neo4j_uri: str = Field(default="bolt://localhost:7687", description="Neo4j Bolt URI")
    neo4j_user: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: str = Field(default="password123", description="Neo4j password")

    # LLM Configuration (supports both direct Gemini and LiteLLM Gateway)
    gemini_api_key: str = Field(default="", description="Gemini API Key (direct)")
    litellm_api_key: str = Field(default="", description="LiteLLM Gateway API Key")
    litellm_base_url: str = Field(default="", description="LiteLLM Gateway Base URL")
    llm_model: str = Field(
        default="gemini/gemini-2.5-pro-preview-05-06",
        description="LiteLLM model identifier",
    )
    llm_temperature: float = Field(default=0.2, description="LLM temperature for extraction")
    llm_max_tokens: int = Field(default=4096, description="Maximum tokens for LLM response")

    # MCP Server Configuration
    mcp_host: str = Field(default="127.0.0.1", description="MCP server host")
    mcp_port: int = Field(default=8000, description="MCP server port")
    mcp_stateless: bool = Field(default=True, description="Run server in stateless mode")

    # Security Configuration
    kg_mcp_token: str = Field(default="", description="Bearer token for authentication")
    kg_allowed_origins: str = Field(
        default="http://localhost:*,http://127.0.0.1:*",
        description="Comma-separated list of allowed origins",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse allowed origins into a list."""
        return [origin.strip() for origin in self.kg_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
