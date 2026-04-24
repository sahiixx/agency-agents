"""Privacy controls and reporting."""

from __future__ import annotations

import re


class PrivacyGuard:
    def __init__(self, redact_pii: bool = True):
        self.redact_pii = redact_pii

    def redact(self, text: str) -> str:
        if not self.redact_pii:
            return text
        text = re.sub(r"[\w.-]+@[\w.-]+", "[REDACTED_EMAIL]", text)
        return re.sub(r"\b\d{10,}\b", "[REDACTED_NUMBER]", text)

    def privacy_report(self) -> dict:
        return {
            "local_processing": True,
            "audio_persisted": False,
            "pii_redaction": self.redact_pii,
        }
