"""Media integrations for Spotify and YouTube."""

from __future__ import annotations

try:
    import spotipy  # type: ignore
except Exception:  # pragma: no cover
    spotipy = None


class AdvancedMedia:
    def __init__(self):
        self.spotify_available = spotipy is not None

    def play_spotify(self, track: str) -> str:
        if not self.spotify_available:
            return "Install spotipy for Spotify integration: pip install spotipy"
        return f"Requested playback for: {track}"

    def stream_youtube(self, query: str) -> str:
        return f"Use yt-dlp for YouTube streaming: {query}"
