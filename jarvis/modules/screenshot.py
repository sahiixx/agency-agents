"""Screenshot and screen recording utilities."""

from __future__ import annotations

from datetime import datetime

from jarvis.config import DATA_DIR

try:
    from PIL import ImageGrab  # type: ignore
except ImportError:  # pragma: no cover
    ImageGrab = None


class ScreenshotModule:
    """Capture screenshots and placeholder recording controls."""

    def take_screenshot(self) -> str:
        try:
            if ImageGrab is None:
                return "Pillow ImageGrab is unavailable on this system."
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            file_path = DATA_DIR / f"screenshot_{datetime.now().astimezone().strftime('%Y%m%d_%H%M%S')}.png"
            shot = ImageGrab.grab()
            shot.save(file_path)
            return f"Screenshot saved to {file_path}."
        except (OSError, ValueError) as exc:
            return f"Screenshot failed: {exc}"

    def start_recording(self) -> str:
        return "Screen recording support can be wired to ffmpeg for your platform."
