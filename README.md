# Voice AI Reachout

A production-shaped, **provider-agnostic outbound voice agent** built on
[Pipecat](https://github.com/pipecat-ai/pipecat). It runs the full real-time
loop — speech-in → understanding → reasoning → speech-out — and is wired so you
can start **free and local** today, then scale to real phone calls by changing
environment variables, not code.


---

## Why it's built this way

Everything runs through a **single transport-agnostic pipeline** (`reachout/pipeline.py`).
The transport (local browser vs. phone) is injected at startup, so the exact
same agent code serves a localhost test and a live PSTN call. Providers for
speech-to-text, the LLM, and text-to-speech are chosen from config and built by
factories (`reachout/services.py`), so swapping Groq → Deepgram, or Kokoro →
Cartesia, is a one-line `.env` change.

```
 caller ⇄ [ transport ] → VAD → turn-detection → STT → LLM → TTS → [ transport ] ⇄ caller
            webrtc | twilio | telnyx        (Silero)  (Smart-Turn v3)
```

Default free stack: **Groq** (Whisper STT + Llama 3.3 70B) · **Kokoro** (local
TTS, Apache-2.0) · **Silero VAD + on-device Smart-Turn v3** (both ship with
Pipecat, no download or key).

---

## Prerequisites

- Python 3.10+
- A **free Groq API key** — the only thing needed to start. Get one at
  <https://console.groq.com/keys> (no credit card).
- For real phone calls only: a Twilio account + number, and a public tunnel
  (e.g. [ngrok](https://ngrok.com)).

---

## Setup

```bash
cd voice-ai-reachout
python -m venv .venv && source .venv/bin/activate      # optional but recommended
pip install -r requirements.txt

cp .env.example .env
# open .env and paste your GROQ_API_KEY
```

First run downloads a few models automatically (Silero VAD, Smart-Turn, and the
Kokoro voice) — a few hundred MB, one time.

---

## Run it — Phase 1: talk to it in your browser (free, no phone)

```bash
python server.py
```

Open <http://localhost:7860>, click **Start conversation**, allow mic access, and
talk. The agent greets you first and runs the reachout conversation. Needs
**only** `GROQ_API_KEY`.

`server.py` serves our own clean web UI (`web/index.html`): a reactive AI orb, a
live transcript, mic mute, dark mode, and tooltips — nothing else. You own this
page; edit `web/index.html` to restyle it.

Tweak the persona/campaign live via `.env` (`AGENT_NAME`, `COMPANY_NAME`,
`CAMPAIGN_GOAL`) — it's injected into the system prompt in `reachout/prompts.py`.

> **Developer playground (optional):** `python bot.py -t webrtc` opens Pipecat's
> built-in *debug* page instead (the busy one with a bot-video box, a dial-pad
> button, transport dropdown, and session/event logs). That page is a library
> tool for debugging, not our product — use `server.py` for the real UI.

---

## Run it — Phase 2: real phone calls via Twilio

1. Start the bot bound to the Twilio transport, telling it your public hostname:

   ```bash
   python bot.py -t twilio --proxy <your-id>.ngrok.app
   ```

2. In another terminal, expose it:

   ```bash
   ngrok http 7860
   ```

   Put the resulting **wss** URL to the bot's socket in `.env` as
   `PUBLIC_WSS_URL` (e.g. `wss://<your-id>.ngrok.app/ws`), and fill in your
   `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`.

3. Place calls:

   ```bash
   # one number
   python outbound_call.py --to +14155551234 --name "Jordan" --company "Globex"

   # a whole campaign from CSV (phone,contact_name,contact_company,notes)
   python outbound_call.py --csv contacts.csv
   ```

> The exact socket path the runner exposes is shown when you start it with
> `-t twilio`; match `PUBLIC_WSS_URL` to it.

---

## Swapping providers (no code changes)

Edit `.env`:

| Want to… | Set |
|---|---|
| Use a telephony-tuned STT | `STT_PROVIDER=deepgram` (+ `DEEPGRAM_API_KEY`) |
| Self-host STT (no API) | `STT_PROVIDER=whisper` |
| Add an LLM failover brain | `LLM_PROVIDER=openrouter` (+ `OPENROUTER_API_KEY`) |
| Use Gemini / Cerebras | `LLM_PROVIDER=google` / `cerebras` (+ key) |
| CPU-only TTS | `TTS_PROVIDER=piper` |
| Premium/cloned voice | `TTS_PROVIDER=cartesia` or `elevenlabs` (+ key) |

Adding a brand-new provider = one branch in `reachout/services.py` + its extra
in `requirements.txt`. Nothing else changes.

---

## Testing

```bash
pip install pytest
pytest -q
```

The suite builds the real Pipecat pipeline with dummy keys (no network), so it
catches version/API drift before you ever place a call.

---

## Cost & scaling notes

- **Phase 1 (this repo, local):** effectively **$0** — Groq free tier + local
  Kokoro/VAD/turn models.
- **Phase 2 (production):** free LLM tiers throttle under concurrency and some
  train on your data — move the brain to a cheap paid token tier (Groq/Gemini
  Flash paid, ~pennies/call) and expect telephony to dominate cost at
  ~**$0.06–0.12/min**, driven by Twilio/Telnyx minutes, not the AI.
- **Scaling out:** each call is an isolated pipeline; run the server behind a
  process manager / container and scale horizontally. Self-host Kokoro + an STT
  model on one GPU to batch many concurrent calls cheaply.

## Compliance (do not skip for outbound)

Outbound calling to real people is regulated. In the US that means TCPA:
consent, calling-hour limits, honesty about being an AI, and scrubbing against
Do-Not-Call lists. Keep `AGENT_DISCLOSE_AI=true`. This repo is the tech; the
legal/consent layer is on you.

---

## Layout

```
bot.py              # runner entry point; defines transports + bot(runner_args)
outbound_call.py    # Twilio dialer (single number or CSV campaign)
reachout/
  config.py         # env-driven settings (one source of truth)
  services.py       # STT/LLM/TTS factories (swap providers here)
  prompts.py        # persona / script / objection handling  ← product quality
  pipeline.py       # transport-agnostic assembly + run loop
  campaign.py       # contact model + CSV loader
tests/test_config.py
contacts.example.csv
```
