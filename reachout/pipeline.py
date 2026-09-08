"""Transport-agnostic pipeline assembly and run loop.

The SAME `run_bot` powers:
  - local browser testing over WebRTC (no phone, no telephony creds), and
  - real phone calls over Twilio / Telnyx,
because the transport is created upstream (in bot.py) and injected here. Nothing
in this file knows or cares which transport it's talking to.

Pipeline order (Pipecat 1.7 turn-taking model):
    transport.input()
      -> VADProcessor            (Silero: is anyone speaking?)
      -> UserTurnProcessor       (VAD + on-device Smart-Turn v3: are they DONE?)
      -> STT                     (speech -> text)
      -> user aggregator         (adds user text to LLM context)
      -> LLM                     (the brain)
      -> TTS                     (text -> speech)
      -> transport.output()      (audio back to the caller)
      -> assistant aggregator    (adds bot text to LLM context)
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import EndFrame, LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
)
from pipecat.processors.audio.vad_processor import VADProcessor
from pipecat.turns.user_turn_processor import UserTurnProcessor

from .config import Settings
from .prompts import build_system_prompt
from .services import build_llm, build_stt, build_tts


async def run_bot(transport, runner_args: Any, settings: Settings) -> None:
    """Assemble and run the voice agent over the given transport."""

    # 1) Build the three swappable brains-of-the-operation from config.
    stt = build_stt(settings)
    llm = build_llm(settings)
    tts = build_tts(settings)

    # 2) Personalize the system prompt from any call/CRM data the transport
    #    surfaced (Twilio sets runner_args.call_data; None for local webrtc).
    call_data = getattr(runner_args, "call_data", None)
    system_prompt = build_system_prompt(settings, call_data=call_data)

    context = LLMContext([{"role": "system", "content": system_prompt}])
    aggregators = LLMContextAggregatorPair(context)

    # 3) Turn-taking. UserTurnProcessor() ships Silero VAD + on-device
    #    Smart-Turn v3 by default — it fires the LLM only when the user is
    #    semantically done, not just when audio goes quiet.
    vad = SileroVADAnalyzer(params=VADParams(stop_secs=settings.vad_stop_secs))

    pipeline = Pipeline(
        [
            transport.input(),
            VADProcessor(vad_analyzer=vad),
            UserTurnProcessor(),
            stt,
            aggregators.user(),
            llm,
            tts,
            transport.output(),
            aggregators.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
        idle_timeout_secs=settings.call_idle_timeout_secs,
    )

    @transport.event_handler("on_client_connected")
    async def _on_client_connected(transport, client):
        logger.info("Caller connected — kicking off the opening line.")
        # Run the LLM once against the system-only context so the agent speaks first.
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def _on_client_disconnected(transport, client):
        logger.info("Caller disconnected — ending the call.")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=getattr(runner_args, "handle_sigint", False))
    await runner.run(task)
