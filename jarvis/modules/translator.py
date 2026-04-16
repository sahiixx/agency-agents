"""Offline translation wrappers."""

from __future__ import annotations

try:
    import argostranslate.translate  # type: ignore
except Exception:  # pragma: no cover
    argos_translate = None
else:
    argos_translate = argostranslate.translate


class Translator:
    def __init__(self):
        self.available = bool(argos_translate)

    def translate(self, text: str, target_language: str) -> str:
        if not self.available:
            return "Install argostranslate for offline translation: pip install argostranslate"
        language_code = target_language.strip().lower()[:2]
        if not language_code:
            return text
        source_code = "en"
        if language_code == source_code:
            return text
        try:
            translator = argos_translate.get_translation_from_codes(source_code, language_code)
            if translator is None:
                return f"No local translation model for {source_code}->{language_code} installed."
            return translator.translate(text)
        except Exception:
            return f"No local translation model for {source_code}->{language_code} installed."
