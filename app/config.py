"""
Configuration for Compass (G42 LLM platform) integration.

Reads environment variables from .env, exposes typed Config object
and helpers to construct CrewAI LLM clients pointing at Compass.

When SAMPLE_MODE is enabled (or no API key is set), get_*_llm()
returns None — the orchestrator then uses pre-computed deterministic
responses derived from the actual data. This keeps the demo working
even without a Compass key (critical for judges and local testing).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (parent of app/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Config:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "").strip()
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://compass.core42.ai/v1").strip()
    AGENT_MODEL: str = os.getenv("AGENT_MODEL", "gpt-4.1")
    REASONING_MODEL: str = os.getenv("REASONING_MODEL", "gpt-5.1")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
    SAMPLE_MODE: bool = os.getenv("SAMPLE_MODE", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    MAX_ITERATIONS: int = int(os.getenv("MAX_AGENT_ITERATIONS", "5"))

    @classmethod
    def is_live(cls) -> bool:
        """Return True if we have a working Compass config; False if mock mode."""
        return (
            not cls.SAMPLE_MODE
            and bool(cls.OPENAI_API_KEY)
            and not cls.OPENAI_API_KEY.startswith("your-")
        )


def get_agent_llm():
    """LLM for routine agent tasks (categorization, summarization)."""
    if not Config.is_live():
        return None
    from crewai import LLM
    return LLM(
        model=f"openai/{Config.AGENT_MODEL}",
        base_url=Config.OPENAI_BASE_URL,
        api_key=Config.OPENAI_API_KEY,
        temperature=0.3,
    )


def get_reasoning_llm():
    """LLM for harder reasoning (risk analysis, plan synthesis)."""
    if not Config.is_live():
        return None
    from crewai import LLM
    return LLM(
        model=f"openai/{Config.REASONING_MODEL}",
        base_url=Config.OPENAI_BASE_URL,
        api_key=Config.OPENAI_API_KEY,
        temperature=0.2,
    )
