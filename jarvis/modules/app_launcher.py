"""Launch and close desktop applications."""

from __future__ import annotations

import subprocess

from config import IS_LINUX, IS_WINDOWS
from utils.platform_utils import command_exists


class AppLauncher:
    """Open and close applications by name."""

    def open_app(self, app_name: str) -> str:
        try:
            app_name = app_name.strip()
            if not app_name:
                return "Please specify an application name."
            if IS_WINDOWS:
                subprocess.Popen(["cmd", "/c", "start", "", app_name], shell=False)
                return f"Opening {app_name}."
            if IS_LINUX:
                binary = app_name.split()[0]
                if not command_exists(binary):
                    return f"Application '{app_name}' was not found in PATH."
                subprocess.Popen(app_name.split())
                return f"Opening {app_name}."
            return "Unsupported platform for launching apps."
        except Exception as exc:
            return f"Could not open {app_name}: {exc}"

    def close_app(self, app_name: str) -> str:
        try:
            if IS_WINDOWS:
                subprocess.run(["taskkill", "/IM", f"{app_name}.exe", "/F"], check=False)
            elif IS_LINUX:
                subprocess.run(["pkill", "-f", app_name], check=False)
            else:
                return "Unsupported platform for closing apps."
            return f"Closed {app_name} if it was running."
        except Exception as exc:
            return f"Could not close {app_name}: {exc}"
