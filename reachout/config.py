"""Central configuration.

Everything the agent needs is expressed here as an env-driven settings object.
Swapping STT/LLM/TTS providers, models, persona, or telephony creds is a matter
of changing environment variables — never code. This is what keeps the system
easy to scale: new providers are added in services.py, selected from here.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

STTProvider = Literal["groq", "deepgram", "whisper"]
LLMProvider = Literal["groq", "openrouter", "cerebras", "google"]
TTSProvider = Literal["kokoro", "piper", "cartesia", "elevenlabs"]


class Settings(BaseSettings):
    """Runtime configuration, loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ── Provider selection ───────────────────────────────────────────────────
    stt_provider: STTProvider = "groq"
    llm_provider: LLMProvider = "groq"
    tts_provider: TTSProvider = "kokoro"

    # ── Model / voice overrides (None -> per-provider default in services.py) ─
    stt_model: str | None = None
    llm_model: str | None = None
    tts_voice: str | None = None

    # ── API keys ─────────────────────────────────────────────────────────────
    groq_api_key: str | None = None
    openrouter_api_key: str | None = None
    cerebras_api_key: str | None = None
    google_api_key: str | None = None
    deepgram_api_key: str | None = None

    # ── Conversation tuning ──────────────────────────────────────────────────
    # Lower vad_stop_secs = snappier responses (less silence before the bot
    # decides you're done). 0.35–0.45 is a good range; too low and it interrupts.
    vad_stop_secs: float = 0.4
    call_idle_timeout_secs: float = 30.0

    # ── Persona / campaign (feeds prompts.py) ────────────────────────────────
    agent_name: str = "Ava"
    company_name: str = "Acme"
    campaign_goal: str = "book a 15-minute intro call"
    agent_disclose_ai: bool = True

    # ── Telephony (Twilio) — phase 2 only ────────────────────────────────────
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from_number: str | None = None
    public_wss_url: str | None = Field(
        default=None, description="Public wss URL of the running bot, e.g. wss://x.ngrok.app/ws"
    )

    def require(self, *keys: str) -> None:
        """Raise a clear error if a required key is unset. Used at startup."""
        missing = [k for k in keys if not getattr(self, k, None)]
        if missing:
            raise RuntimeError(
                f"Missing required configuration: {', '.join(missing)}. "
                f"Set them in your .env file (see .env.example)."
            )


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


# Convenience module-level singleton
settings = get_settings()
