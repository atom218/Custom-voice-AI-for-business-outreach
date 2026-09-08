"""Smoke tests that run WITHOUT any API keys or network.

They verify the wiring is sound: config loads, providers construct, and the
full Pipecat pipeline links end-to-end. This is the cheapest guardrail against
an API/version drift breaking the assembly.
"""

import os

import pytest


def test_settings_defaults():
    from reachout.config import Settings

    s = Settings(_env_file=None)  # ignore any real .env
    assert s.stt_provider == "groq"
    assert s.llm_provider == "groq"
    assert s.tts_provider == "kokoro"
    assert s.agent_disclose_ai is True


def test_system_prompt_builds():
    from reachout.config import Settings
    from reachout.prompts import build_system_prompt

    s = Settings(_env_file=None)
    prompt = build_system_prompt(s, call_data={"contact_name": "Jordan"})
    assert "Jordan" in prompt
    assert s.agent_name in prompt
    # AI disclosure must be present when enabled
    assert "AI" in prompt


def test_require_raises_on_missing():
    from reachout.config import Settings

    s = Settings(_env_file=None, groq_api_key=None)
    with pytest.raises(RuntimeError):
        s.require("groq_api_key")


def test_pipeline_assembles_with_dummy_keys():
    """Build the real pipeline objects (no network I/O on construction)."""
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.processors.aggregators.llm_context import LLMContext
    from pipecat.processors.aggregators.llm_response_universal import (
        LLMContextAggregatorPair,
    )
    from pipecat.processors.audio.vad_processor import VADProcessor
    from pipecat.audio.vad.silero import SileroVADAnalyzer
    from pipecat.turns.user_turn_processor import UserTurnProcessor

    from reachout.config import Settings
    from reachout.services import build_stt, build_llm

    s = Settings(_env_file=None, groq_api_key="dummy-key-for-construction")
    stt = build_stt(s)
    llm = build_llm(s)
    ctx = LLMContext([{"role": "system", "content": "hi"}])
    agg = LLMContextAggregatorPair(ctx)

    pipeline = Pipeline(
        [
            VADProcessor(vad_analyzer=SileroVADAnalyzer()),
            UserTurnProcessor(),
            stt,
            agg.user(),
            llm,
            agg.assistant(),
        ]
    )
    assert pipeline is not None
