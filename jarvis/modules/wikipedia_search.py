"""Wikipedia search helpers."""

from __future__ import annotations

try:
    import wikipedia  # type: ignore
except Exception:  # pragma: no cover
    wikipedia = None


class WikipediaSearch:
    """Return Wikipedia summaries for topics."""

    def summary(self, topic: str) -> str:
        if wikipedia is None:
            return "Wikipedia package is not installed."
        try:
            return wikipedia.summary(topic, sentences=2)
        except Exception as exc:
            return f"Wikipedia lookup failed: {exc}"
