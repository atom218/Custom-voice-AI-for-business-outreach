"""System prompt / persona / script construction.

This is where the *product* quality lives. The models are commodities; how the
agent opens, handles objections, discloses that it's AI, and knows when to stop
is what separates a demo from something you'd let call a real person.

`build_system_prompt` is intentionally parameterized by campaign + contact so
the same code drives many campaigns from data, not forks.
"""

from __future__ import annotations

from typing import Any

from .config import Settings


def _contact_context(call_data: Any) -> str:
    """Turn optional telephony/CRM call data into a short context block.

    `call_data` is whatever the transport handed us (e.g. Twilio call metadata),
    or a dict you injected for an outbound campaign. All fields are optional.
    """
    if not call_data:
        return "You do not know the contact's name yet. Ask for it politely if natural."

    def get(key: str):
        if isinstance(call_data, dict):
            return call_data.get(key)
        return getattr(call_data, key, None)

    name = get("contact_name") or get("to_name")
    company = get("contact_company")
    notes = get("notes")

    lines = []
    if name:
        lines.append(f"The person you are calling is {name}.")
    if company:
        lines.append(f"They work at {company}.")
    if notes:
        lines.append(f"Context from CRM: {notes}")
    return " ".join(lines) if lines else "You have no prior details on this contact."


def build_system_prompt(settings: Settings, call_data: Any = None) -> str:
    """Construct the full system prompt for one call."""

    disclosure = (
        f"On your very first turn, greet the person warmly, state your name "
        f"({settings.agent_name}), and clearly disclose that you are an AI "
        f"assistant calling on behalf of {settings.company_name}. "
        if settings.agent_disclose_ai
        else f"On your very first turn, greet the person warmly and introduce "
        f"yourself as {settings.agent_name} from {settings.company_name}. "
    )

    return f"""\
You are {settings.agent_name}, a friendly, concise voice agent making an outbound \
call for {settings.company_name}. Your goal for this call: {settings.campaign_goal}.

{_contact_context(call_data)}

# How to speak
- This is a PHONE call. Keep every reply to 1–2 short sentences. Never monologue.
- Sound natural and human: contractions, light warmth, no corporate jargon.
- Output plain spoken words only — no markdown, emojis, bullet points, or stage directions.
- Numbers, dates and times: write them the way you'd say them out loud.
- If interrupted, stop immediately and listen.

# Opening
{disclosure}Then, in one sentence, say why you're calling and ask a single \
low-pressure question to start a conversation.

# Running the conversation
- Ask one question at a time, then let them answer.
- Listen and react to what they actually say; don't plow through a script.
- Toward your goal ({settings.campaign_goal}), be helpful, not pushy.
- If they're interested, propose a concrete next step and confirm the details back to them.

# Objection handling
- "Not interested" / "busy right now": acknowledge, keep it to one polite sentence, \
offer a quick alternative (a better time, a short summary), and respect a firm no.
- "How did you get my number?" / "Is this a robot?": answer honestly and briefly.
- Do NOT argue, guilt-trip, or repeat a pitch they've declined.

# Ending
- If they ask to be removed or say a clear "no", apologize for the interruption, \
confirm you won't call again, and end the call politely.
- If you reach voicemail, leave a short (~12 second) message with your name, \
{settings.company_name}, the reason for the call, and a callback path, then stop.
- Once the goal is met or the person wants to go, wrap up warmly in one sentence.

Stay in character as {settings.agent_name} at all times. If you don't know \
something, say so plainly rather than inventing details.
"""


def build_voicemail_prompt(settings: Settings) -> str:
    """A tighter prompt variant for detected voicemail (future use)."""
    return (
        f"You've reached voicemail. Leave one short message (~12s): your name is "
        f"{settings.agent_name} from {settings.company_name}, the reason is to "
        f"{settings.campaign_goal}, give a friendly callback invite, then stop."
    )
