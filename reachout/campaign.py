"""Outbound campaign data model.

Keeps contacts as data, not code, so scaling from 1 test call to a 10k-row
campaign is a CSV change, not a rewrite. `outbound_call.py` consumes these.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Contact:
    phone: str  # E.164, e.g. +14155551234
    contact_name: str | None = None
    contact_company: str | None = None
    notes: str | None = None
    extra: dict = field(default_factory=dict)

    def as_call_data(self) -> dict:
        """Shape passed to the bot so prompts.py can personalize the call."""
        return {
            "contact_name": self.contact_name,
            "contact_company": self.contact_company,
            "notes": self.notes,
            **self.extra,
        }


def load_contacts(path: str | Path) -> list[Contact]:
    """Load contacts from a CSV with headers: phone,contact_name,contact_company,notes."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Contacts file not found: {path}")

    contacts: list[Contact] = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            phone = (row.get("phone") or "").strip()
            if not phone:
                continue
            contacts.append(
                Contact(
                    phone=phone,
                    contact_name=(row.get("contact_name") or "").strip() or None,
                    contact_company=(row.get("contact_company") or "").strip() or None,
                    notes=(row.get("notes") or "").strip() or None,
                )
            )
    return contacts
