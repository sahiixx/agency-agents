"""News headlines module."""

from __future__ import annotations

import os

import requests


class NewsModule:
    """Fetch latest headlines using NewsAPI when token is provided."""

    def top_headlines(self, country: str = "us") -> list[str]:
        key = os.getenv("JARVIS_NEWS_API_KEY", "")
        if not key:
            return ["Set JARVIS_NEWS_API_KEY to enable live news headlines."]
        try:
            url = "https://newsapi.org/v2/top-headlines"
            resp = requests.get(url, params={"country": country, "apiKey": key}, timeout=10)
            data = resp.json() if resp.ok else {}
            return [a.get("title", "Untitled") for a in data.get("articles", [])[:5]]
        except Exception as exc:
            return [f"News lookup failed: {exc}"]
