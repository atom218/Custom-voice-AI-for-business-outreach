"""Custom web server + UI for local testing.

This replaces the Pipecat *developer playground* (the busy debug page you saw at
/client/) with our OWN clean web client that we fully control. It:

  1. serves web/index.html at "/"  (our UI), and
  2. exposes POST/PATCH /api/offer  (the WebRTC signaling the browser needs),
     which spins up the SAME `run_bot` pipeline used everywhere else.

Run it:
    python server.py                 # then open http://localhost:7860

Only needs GROQ_API_KEY in .env (same as before). For real phone calls you
still use `python bot.py -t twilio` — this server is purely the nice local UI.
"""

from __future__ import annotations

import argparse
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

import uvicorn
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI
from fastapi.staticfiles import StaticFiles
from loguru import logger

from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from pipecat.transports.smallwebrtc.request_handler import (
    SmallWebRTCPatchRequest,
    SmallWebRTCRequest,
    SmallWebRTCRequestHandler,
)
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport

from reachout.config import settings
from reachout.pipeline import run_bot

load_dotenv()

WEB_DIR = Path(__file__).parent / "web"

# Fail fast with a friendly message if the one required key is missing.
try:
    settings.require("groq_api_key")
except RuntimeError as e:
    logger.warning(str(e))

_handler = SmallWebRTCRequestHandler()


@asynccontextmanager
async def _lifespan(app: FastAPI):
    yield
    await _handler.close()


app = FastAPI(lifespan=_lifespan)


@app.post("/api/offer")
async def offer(request: SmallWebRTCRequest, background_tasks: BackgroundTasks):
    """Accept the browser's WebRTC offer and launch a bot for this session."""

    async def _on_connection(connection: SmallWebRTCConnection):
        transport = SmallWebRTCTransport(
            params=TransportParams(audio_in_enabled=True, audio_out_enabled=True),
            webrtc_connection=connection,
        )
        # run_bot only reads .call_data and .handle_sigint off runner_args.
        runner_args = SimpleNamespace(call_data=None, handle_sigint=False)
        logger.info("Browser connected — starting a voice session.")
        background_tasks.add_task(run_bot, transport, runner_args, settings)

    return await _handler.handle_web_request(
        request=request, webrtc_connection_callback=_on_connection
    )


@app.patch("/api/offer")
async def ice_candidate(request: SmallWebRTCPatchRequest):
    """Trickle-ICE candidate updates from the browser."""
    await _handler.handle_patch_request(request)
    return {"status": "success"}


# Serve our custom UI at "/". Registered LAST so /api/* routes win.
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Voice AI Reachout — local web UI server")
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=7860)
    args = ap.parse_args()

    logger.info(f"Open http://{args.host}:{args.port} in your browser and click Start.")
    uvicorn.run(app, host=args.host, port=args.port)
