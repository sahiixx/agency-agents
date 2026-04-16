"""Random jokes module."""

from __future__ import annotations

try:
    import pyjokes  # type: ignore
except Exception:  # pragma: no cover
    pyjokes = None


class JokesModule:
    """Provide random jokes."""

    def random_joke(self) -> str:
        if pyjokes is None:
            return "I need the pyjokes package to tell jokes."
        try:
            return pyjokes.get_joke()
        except Exception as exc:
            return f"Could not fetch a joke: {exc}"
