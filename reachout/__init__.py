"""Voice AI Reachout — a provider-agnostic, telephony-ready voice agent.

Package layout:
    config.py    - all runtime configuration (env-driven, one source of truth)
    services.py  - factories that build STT / LLM / TTS from config (swappable)
    prompts.py   - system prompt / persona / script construction
    pipeline.py  - transport-agnostic pipeline assembly + run loop
    campaign.py  - contact model + loader for outbound campaigns
"""

__version__ = "0.1.0"
