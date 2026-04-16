"""Web browsing and search helpers."""

from __future__ import annotations

import urllib.parse
import webbrowser


class WebBrowser:
    """Open websites and perform web searches."""

    shortcuts = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "wikipedia": "https://www.wikipedia.org",
        "github": "https://github.com",
    }

    def open_website(self, site: str) -> str:
        try:
            target = self.shortcuts.get(site.lower(), site)
            if not target.startswith("http"):
                target = f"https://{target}"
            webbrowser.open(target)
            return f"Opening {target}."
        except Exception as exc:
            return f"Failed to open website: {exc}"

    def google_search(self, query: str) -> str:
        url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
        webbrowser.open(url)
        return f"Searching Google for {query}."

    def youtube_search(self, query: str) -> str:
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
        webbrowser.open(url)
        return f"Searching YouTube for {query}."
