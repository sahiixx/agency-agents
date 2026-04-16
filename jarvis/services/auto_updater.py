"""Self-update service for JARVIS."""

from __future__ import annotations

import json
from urllib.request import urlopen

from jarvis import version


class AutoUpdater:
    """Check GitHub releases and report update status."""

    def __init__(self, repo: str = "sahiixx/agency-agents") -> None:
        self.repo = repo

    def check_for_updates(self) -> dict[str, str | bool]:
        url = f"https://api.github.com/repos/{self.repo}/releases/latest"
        try:
            with urlopen(url, timeout=5) as resp:  # nosec B310
                data = json.loads(resp.read().decode("utf-8"))
            latest = data.get("tag_name", "")
        except Exception as exc:
            return {"ok": False, "reason": str(exc), "current": version.CURRENT_VERSION}

        return {
            "ok": True,
            "current": version.CURRENT_VERSION,
            "latest": latest,
            "update_available": latest not in {"", version.CURRENT_VERSION},
        }
