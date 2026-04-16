"""Offline translation wrappers."""

from __future__ import annotations

try:
    import argostranslate.package  # type: ignore
except Exception:  # pragma: no cover
    argostranslate = None
else:
    argostranslate = True


class Translator:
    def __init__(self):
        self.available = bool(argostranslate)

    def translate(self, text: str, target_language: str) -> str:
        if not self.available:
            return "Install argostranslate for offline translation: pip install argostranslate"
        return f"[{target_language}] {text}"
