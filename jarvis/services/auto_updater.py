"""Self-update service for JARVIS."""

from __future__ import annotations

import json
import re
from urllib.request import urlopen

from jarvis import version


class AutoUpdater:
    """Check GitHub releases and report update status."""

    def __init__(self, repo: str = "sahiixx/agency-agents") -> None:
        self.repo = repo

    def check_for_updates(self) -> dict[str, str | bool]:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", self.repo):
            return {"ok": False, "reason": "Invalid repository format", "current": version.CURRENT_VERSION}
        url = f"https://api.github.com/repos/{self.repo}/releases/latest"
        try:
            with urlopen(url, timeout=5) as resp:
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
