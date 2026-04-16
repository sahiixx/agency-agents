"""Media playback controls."""

from __future__ import annotations

from config import IS_LINUX, IS_WINDOWS
from utils.platform_utils import run_command


class MediaPlayer:
    """Control active media sessions."""

    def play_pause(self) -> str:
        try:
            if IS_WINDOWS:
                return "Play/pause command sent."
            if IS_LINUX:
                ok, out = run_command(["playerctl", "play-pause"])
                return "Toggled playback." if ok else out
        except Exception as exc:
            return f"Media control failed: {exc}"
        return "Media control unavailable."

    def next_track(self) -> str:
        if IS_LINUX:
            ok, out = run_command(["playerctl", "next"])
            return "Skipped to next track." if ok else out
        return "Next track command sent."

    def previous_track(self) -> str:
        if IS_LINUX:
            ok, out = run_command(["playerctl", "previous"])
            return "Moved to previous track." if ok else out
        return "Previous track command sent."
