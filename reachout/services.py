"""Provider factories.

Each factory maps a provider name from config to a concrete Pipecat service.
Imports are done lazily *inside* each branch so that installing only the
providers you use is enough — you never pay the import cost (or dependency
weight) of a provider you didn't select.

Adding a new provider = add a branch here + add its extra to requirements.txt.
Nothing else in the codebase needs to change.
"""

from __future__ import annotations

from loguru import logger

from .config import Settings


# ─── Speech-to-Text ──────────────────────────────────────────────────────────
def build_stt(settings: Settings):
    provider = settings.stt_provider
    logger.info(f"STT provider: {provider}")

    if provider == "groq":
        # Free tier, zero local infra. Whisper Large v3 Turbo on Groq's LPU.
        from pipecat.services.groq.stt import GroqSTTService

        settings.require("groq_api_key")
        return GroqSTTService(
            api_key=settings.groq_api_key,
            settings=GroqSTTService.Settings(
                model=settings.stt_model or "whisper-large-v3-turbo"
            ),
        )

    if provider == "deepgram":
        # Telephony-tuned streaming STT. Paid, but has free credits to start.
        from pipecat.services.deepgram.stt import DeepgramSTTService

        settings.require("deepgram_api_key")
        return DeepgramSTTService(api_key=settings.deepgram_api_key)

    if provider == "whisper":
        # Fully local / self-hosted (faster-whisper). No API key, needs CPU/GPU.
        from pipecat.services.whisper.stt import WhisperSTTService

        return WhisperSTTService(model=settings.stt_model or "large-v3-turbo")

    raise ValueError(f"Unknown STT provider: {provider}")


# ─── Large Language Model (the brain) ────────────────────────────────────────
def build_llm(settings: Settings):
    provider = settings.llm_provider
    logger.info(f"LLM provider: {provider}")

    if provider == "groq":
        from pipecat.services.groq.llm import GroqLLMService

        settings.require("groq_api_key")
        return GroqLLMService(
            api_key=settings.groq_api_key,
            settings=GroqLLMService.Settings(
                model=settings.llm_model or "llama-3.3-70b-versatile"
            ),
        )

    if provider == "openrouter":
        # Great as a failover brain — routes to many models behind one key.
        from pipecat.services.openrouter.llm import OpenRouterLLMService

        settings.require("openrouter_api_key")
        return OpenRouterLLMService(
            api_key=settings.openrouter_api_key,
            model=settings.llm_model or "meta-llama/llama-3.3-70b-instruct",
        )

    if provider == "cerebras":
        from pipecat.services.cerebras.llm import CerebrasLLMService

        settings.require("cerebras_api_key")
        return CerebrasLLMService(
            api_key=settings.cerebras_api_key,
            model=settings.llm_model or "llama-3.3-70b",
        )

    if provider == "google":
        from pipecat.services.google.llm import GoogleLLMService

        settings.require("google_api_key")
        return GoogleLLMService(
            api_key=settings.google_api_key,
            model=settings.llm_model or "gemini-2.0-flash",
        )

    raise ValueError(f"Unknown LLM provider: {provider}")


# ─── Text-to-Speech ──────────────────────────────────────────────────────────
def build_tts(settings: Settings):
    provider = settings.tts_provider
    logger.info(f"TTS provider: {provider}")

    if provider == "kokoro":
        # Local, Apache-2.0, low latency. Model auto-downloads on first run.
        from pipecat.services.kokoro.tts import KokoroTTSService

        return KokoroTTSService(
            settings=KokoroTTSService.Settings(voice=settings.tts_voice or "af_heart"),
        )

    if provider == "piper":
        # CPU-only fallback. Voice auto-downloads on first run.
        from pipecat.services.piper.tts import PiperTTSService

        return PiperTTSService(
            settings=PiperTTSService.Settings(voice=settings.tts_voice or "en_US-lessac-medium"),
        )

    if provider == "cartesia":
        # Paid, premium quality. Read key from env directly (not a core field).
        import os

        from pipecat.services.cartesia.tts import CartesiaTTSService

        key = os.getenv("CARTESIA_API_KEY")
        if not key:
            raise RuntimeError("TTS_PROVIDER=cartesia requires CARTESIA_API_KEY in env.")
        return CartesiaTTSService(api_key=key, voice_id=settings.tts_voice or "")

    if provider == "elevenlabs":
        import os

        from pipecat.services.elevenlabs.tts import ElevenLabsTTSService

        key = os.getenv("ELEVENLABS_API_KEY")
        if not key:
            raise RuntimeError("TTS_PROVIDER=elevenlabs requires ELEVENLABS_API_KEY in env.")
        return ElevenLabsTTSService(api_key=key, voice_id=settings.tts_voice or "")

    raise ValueError(f"Unknown TTS provider: {provider}")
