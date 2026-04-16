"""Command parser with keyword and fuzzy intent matching."""

from __future__ import annotations

import difflib
from typing import Any

from config import COMMANDS_FILE
from utils.helpers import load_json

try:
    from fuzzywuzzy import process  # type: ignore
except Exception:  # pragma: no cover
    process = None


class CommandParser:
    """Parse free-form text into an intent payload."""

    def __init__(self) -> None:
        self.registry = load_json(COMMANDS_FILE, {"intents": []})

    def parse(self, text: str) -> dict[str, Any]:
        """Resolve user text to intent and action metadata."""
        cleaned = text.lower().strip()
        if not cleaned:
            return {"intent": "unknown", "action": "none", "command": text, "score": 0}

        intents = self.registry.get("intents", [])
        best = {"intent": "unknown", "action": "none", "command": text, "score": 0}

        for intent in intents:
            for keyword in intent.get("keywords", []):
                if keyword in cleaned:
                    return {
                        "intent": intent.get("name", "unknown"),
                        "action": intent.get("action", "none"),
                        "command": text,
                        "score": 100,
                    }

        candidates: dict[str, dict[str, Any]] = {}
        for intent in intents:
            for keyword in intent.get("keywords", []):
                candidates[keyword] = intent
        if not candidates:
            return best

        if process is not None:
            match = process.extractOne(cleaned, list(candidates.keys()))
            if match:
                matched_keyword, score = match
                intent = candidates[matched_keyword]
                if score >= 60:
                    return {
                        "intent": intent.get("name", "unknown"),
                        "action": intent.get("action", "none"),
                        "command": text,
                        "score": int(score),
                    }
        else:
            matches = difflib.get_close_matches(cleaned, list(candidates.keys()), n=1, cutoff=0.6)
            if matches:
                intent = candidates[matches[0]]
                return {
                    "intent": intent.get("name", "unknown"),
                    "action": intent.get("action", "none"),
                    "command": text,
                    "score": 60,
                }
        return best
