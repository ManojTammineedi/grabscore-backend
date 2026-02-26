"""
Application configuration using pydantic-settings.
All environment variables are loaded from .env file with sensible defaults.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application
    APP_NAME: str = "GrabCredit BNPL Eligibility Engine"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"

    # Database (SQLite for prototype, swap to PostgreSQL for production)
    DATABASE_URL: str = "sqlite:///./grabcredit.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_ENABLED: bool = False  # Disable by default for easy local dev

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]

    # API Security
    API_KEY: str = "grabcredit-dev-key"

    # Anthropic Claude (for narrative generation)
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-3-haiku-20240307"  # Cheaper, faster model for free accounts
    CLAUDE_ENABLED: bool = False  # Use template-based narrative by default

    # OpenRouter
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "stepfun/step-3.5-flash:free"
    USE_OPENROUTER: bool = False

    # Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-flash-latest"
    USE_GEMINI: bool = True

    # Credit Scoring Thresholds
    APPROVAL_THRESHOLD: float = 45.0
    MAX_CREDIT_LIMIT: float = 50000.0
    MIN_CREDIT_LIMIT: float = 2000.0
    FRAUD_VELOCITY_DAYS: int = 7

    # EMI Configuration
    EMI_INTEREST_RATE_3M: float = 0.0  # 0% for 3 months
    EMI_INTEREST_RATE_6M: float = 2.5  # 2.5% for 6 months
    EMI_INTEREST_RATE_9M: float = 5.0  # 5% for 9 months

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance to avoid re-reading .env on every call."""
    return Settings()
