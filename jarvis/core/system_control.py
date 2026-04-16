"""Cross-platform system control primitives."""

from __future__ import annotations

import platform
import subprocess


class SystemControl:
    """Provide minimal safe wrappers for platform commands."""

    def os_name(self) -> str:
        return platform.system().lower()

    def lock_command(self) -> list[str]:
        os_name = self.os_name()
        if os_name == "windows":
            return ["rundll32.exe", "user32.dll,LockWorkStation"]
        return ["xdg-screensaver", "lock"]

    def lock(self) -> bool:
        try:
            subprocess.run(self.lock_command(), check=False, capture_output=True)
            return True
        except Exception:
            return False
