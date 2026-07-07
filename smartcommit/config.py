"""Centralized, environment-overridable configuration for smartcommit.

All settings can be overridden with SMARTCOMMIT_<SETTING_NAME> env vars, e.g.:

    export SMARTCOMMIT_DEFAULT_MODEL="qwen2.5-coder:7b"
    export SMARTCOMMIT_AI_TIMEOUT_SECONDS=30
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SMARTCOMMIT_")

    default_model: str = "llama3.2:3b"
    """Ollama model used when --model isn't passed on the CLI."""

    max_diff_chars: int = 6000
    """Max characters of the diff sent to the AI (keeps prompts fast/cheap)."""

    ai_timeout_seconds: int = 50
    """How long to wait for Ollama before falling back to the rule-based generator."""

    max_length: int = 72
    """Max length of the commit subject line (Conventional Commits convention)."""

    use_emoji: bool = False
    """Prefix commit messages with a gitmoji matching their type."""


settings = Settings()