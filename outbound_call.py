"""Originate outbound phone calls via Twilio (phase-2 telephony).

Prerequisites:
  1. `python bot.py -t twilio --proxy <your-public-host>` is running and reachable.
  2. A public HTTPS/WSS tunnel to it (e.g. `ngrok http 7860`).
  3. Twilio creds + a Twilio phone number in your .env.

Usage:
    # single number
    python outbound_call.py --to +14155551234 --name "Jordan" --company "Globex"

    # whole campaign from a CSV (phone,contact_name,contact_company,notes)
    python outbound_call.py --csv contacts.csv --max-concurrent 1

The call is connected to your running bot via Twilio Media Streams: Twilio dials
the number, then streams the call audio to your bot's WebSocket. Contact details
are passed as <Parameter>s so the bot can personalize the conversation.

NOTE: outbound dialing to real people is regulated (TCPA in the US: consent,
calling-hours, DNC scrubbing, honest AI disclosure). This script does the
plumbing only — compliance is your responsibility. Keep AGENT_DISCLOSE_AI=true.
"""

from __future__ import annotations

import argparse
import sys
import time
from urllib.parse import urlparse

from dotenv import load_dotenv
from loguru import logger

from reachout.campaign import Contact, load_contacts
from reachout.config import settings

load_dotenv()


def _twiml_for(contact: Contact) -> str:
    """TwiML that bridges the call audio to the running bot over a WebSocket."""
    wss = settings.public_wss_url
    params = "".join(
        f'<Parameter name="{k}" value="{v}" />'
        for k, v in contact.as_call_data().items()
        if v
    )
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response><Connect><Stream url=\"{wss}\">{params}</Stream></Connect></Response>"
    )


def place_call(client, contact: Contact) -> str:
    twiml = _twiml_for(contact)
    call = client.calls.create(
        to=contact.phone,
        from_=settings.twilio_from_number,
        twiml=twiml,
    )
    logger.info(f"Dialing {contact.phone} ({contact.contact_name or 'unknown'}) -> {call.sid}")
    return call.sid


def main() -> int:
    ap = argparse.ArgumentParser(description="Originate outbound reachout calls via Twilio.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--to", help="Single destination number in E.164 (e.g. +14155551234)")
    g.add_argument("--csv", help="Path to a contacts CSV")
    ap.add_argument("--name", help="Contact name (with --to)")
    ap.add_argument("--company", help="Contact company (with --to)")
    ap.add_argument("--notes", help="CRM notes (with --to)")
    ap.add_argument("--max-concurrent", type=int, default=1,
                    help="Naive pacing: seconds delay between dials for now")
    args = ap.parse_args()

    settings.require("twilio_account_sid", "twilio_auth_token",
                     "twilio_from_number", "public_wss_url")

    parsed = urlparse(settings.public_wss_url)
    if parsed.scheme != "wss":
        logger.warning(
            f"PUBLIC_WSS_URL should be a wss:// URL to your bot's /ws endpoint; "
            f"got '{settings.public_wss_url}'."
        )

    from twilio.rest import Client  # imported here so non-telephony use needs no twilio

    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

    if args.to:
        contacts = [Contact(phone=args.to, contact_name=args.name,
                            contact_company=args.company, notes=args.notes)]
    else:
        contacts = load_contacts(args.csv)
        logger.info(f"Loaded {len(contacts)} contacts from {args.csv}")

    for i, contact in enumerate(contacts):
        try:
            place_call(client, contact)
        except Exception as e:  # noqa: BLE001 - keep the campaign going
            logger.error(f"Failed to dial {contact.phone}: {e}")
        if i < len(contacts) - 1:
            time.sleep(max(0, args.max_concurrent))

    return 0


if __name__ == "__main__":
    sys.exit(main())
