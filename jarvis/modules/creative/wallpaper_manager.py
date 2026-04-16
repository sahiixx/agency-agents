"""Cross-platform wallpaper manager."""

from __future__ import annotations

from pathlib import Path


class WallpaperManager:
    """Track currently selected wallpaper."""

    def __init__(self) -> None:
        self.current: str | None = None

    def set_wallpaper(self, image_path: str) -> bool:
        path = Path(image_path).expanduser()
        if not path.exists():
            return False
        self.current = str(path)
        return True
