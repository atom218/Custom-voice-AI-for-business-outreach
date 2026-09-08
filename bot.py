"""Entry point discovered by the Pipecat dev runner.

Run it directly and the runner starts a FastAPI server that can serve MANY
transports at once. Pick one with `-t`:

    # Local browser test (recommended first run — only needs GROQ_API_KEY):
    python bot.py -t webrtc

    # Real phone calls via Twilio (needs a public tunnel; see README):
    python bot.py -t twilio --proxy your-id.ngrok.app

The runner calls `bot(runner_args)` below for each new session/call.
"""

from __future__ import annotations

from dotenv import load_dotenv

# Load .env before Settings is constructed (module import caches settings).
load_dotenv()

from loguru import logger

from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams

from reachout.config import settings
from reachout.pipeline import run_bot

# One factory per transport. The runner picks the right one per session and
# auto-wires the telephony serializer (Twilio/Telnyx) from the call handshake.
TRANSPORT_PARAMS = {
    "webrtc": lambda: TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
    ),
    "twilio": lambda: FastAPIWebsocketParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
    ),
    "telnyx": lambda: FastAPIWebsocketParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
    ),
}


async def bot(runner_args: RunnerArguments) -> None:
    """Per-session entry point invoked by the Pipecat runner."""
    transport = await create_transport(runner_args, TRANSPORT_PARAMS)
    logger.info(
        f"New session | stt={settings.stt_provider} "
        f"llm={settings.llm_provider} tts={settings.tts_provider}"
    )
    await run_bot(transport, runner_args, settings)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
