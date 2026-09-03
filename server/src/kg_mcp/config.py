"""
Configuration management for MCP-KG-Memory server.
Uses pydantic-settings for environment variable handling.
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(REPOSITORY_ENV, ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Neo4j Configuration
    neo4j_uri: str = Field(default="bolt://127.0.0.1:8787", description="Neo4j Bolt URI")
    neo4j_user: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: str = Field(default="", description="Neo4j password")
    neo4j_configured: str = Field(default="1", description="Is Neo4j configured (1/0)")

    # LLM Configuration (supports both direct Gemini and LiteLLM Gateway)
    # Mode: 'gemini_direct', 'litellm', or 'both'
    llm_enabled: bool = Field(default=False, description="Enable optional LLM enrichment")
    llm_mode: Literal["gemini_direct", "litellm", "both"] = Field(
        default="litellm", description="Operation mode"
    )
    llm_primary: str = Field(default="litellm", description="Primary provider if both configured")
    llm_provider: str = Field(default="litellm", description="Active provider tag")

    # Gemini Direct
    gemini_api_key: str = Field(default="", description="Gemini API Key (direct)")
    gemini_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/", description="Gemini API Base URL"
    )
    gemini_model: str = Field(default="", description="Gemini Direct Model ID")

    # LiteLLM
    litellm_api_key: str = Field(default="", description="LiteLLM Gateway API Key")
    litellm_base_url: str = Field(default="", description="LiteLLM Gateway Base URL")
    litellm_model: str = Field(default="", description="LiteLLM Model ID")

    # General / Fallback Model
    llm_model: str = Field(
        default="gemini/gemini-1.5-flash",
        description="Default model identifier (legacy fallback)",
    )

    # Task-specific Routing (optional)
    kg_model_default: str = Field(default="", description="Default model for general tasks")
    kg_model_fast: str = Field(default="", description="Fast model for high-throughput")
    kg_model_reason: str = Field(default="", description="Reasoning model for complex tasks")

    llm_temperature: float = Field(default=0.2, description="LLM temperature for extraction")
    llm_max_tokens: int = Field(default=4096, description="Maximum tokens for LLM response")

    # MCP Server Configuration
    mcp_host: str = Field(default="127.0.0.1", description="MCP server host")
    mcp_port: int = Field(default=8765, description="MCP server port")
    mcp_stateless: bool = Field(default=True, description="Run server in stateless mode")

    # Security Configuration
    kg_mcp_token: str = Field(default="", description="Bearer token for authentication")
    kg_allowed_origins: str = Field(
        default="http://localhost:*,http://127.0.0.1:*",
        description="Comma-separated list of allowed origins",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    # Ingestion limits are enforced before data reaches Neo4j or an LLM.
    max_request_bytes: int = Field(default=12_000_000, ge=1_024)
    max_text_chars: int = Field(default=16_000, ge=1)
    max_screenshot_base64_chars: int = Field(default=10_000_000, ge=1)

    # Life Memory (dedupe/sessionization)
    screenshot_dedupe_hamming: int = Field(
        default=6, description="Max dHash distance to mark duplicate"
    )
    screenshot_dedupe_window_seconds: int = Field(
        default=120, description="Time window for screenshot dedupe"
    )
    segment_gap_minutes: int = Field(default=5, description="Max gap (minutes) within a segment")
    session_gap_minutes: int = Field(default=7, description="Gap (minutes) to start a new episode")

    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse allowed origins into a list."""
        return [origin.strip() for origin in self.kg_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
