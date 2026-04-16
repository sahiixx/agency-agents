"""Cross-platform system control actions for JARVIS."""

from __future__ import annotations

import subprocess

from config import IS_LINUX, IS_WINDOWS
from utils.platform_utils import command_exists, run_command


class SystemControl:
    """Control volume, brightness, and power functions."""

    def volume_up(self) -> str:
        try:
            if IS_WINDOWS:
                return "Volume up requested. Please install pycaw integration for full control."
            if IS_LINUX and command_exists("amixer"):
                ok, out = run_command(["amixer", "-D", "pulse", "sset", "Master", "5%+"])
                return "Volume increased." if ok else out
        except Exception as exc:
            return f"Failed to raise volume: {exc}"
        return "Volume control not available on this system."

    def volume_down(self) -> str:
        try:
            if IS_WINDOWS:
                return "Volume down requested. Please install pycaw integration for full control."
            if IS_LINUX and command_exists("amixer"):
                ok, out = run_command(["amixer", "-D", "pulse", "sset", "Master", "5%-"])
                return "Volume decreased." if ok else out
        except Exception as exc:
            return f"Failed to lower volume: {exc}"
        return "Volume control not available on this system."

    def mute(self) -> str:
        try:
            if IS_WINDOWS:
                return "Mute requested. Please install pycaw integration for full control."
            if IS_LINUX and command_exists("amixer"):
                ok, out = run_command(["amixer", "-D", "pulse", "set", "Master", "1+", "toggle"])
                return "Mute toggled." if ok else out
        except Exception as exc:
            return f"Failed to toggle mute: {exc}"
        return "Mute control not available on this system."

    def brightness_up(self) -> str:
        try:
            if IS_WINDOWS:
                return "Brightness increase requested. Install screen-brightness-control for direct support."
            if IS_LINUX and command_exists("xrandr"):
                return "Brightness adjustment on Linux requires monitor-specific setup."
        except Exception as exc:
            return f"Failed to adjust brightness: {exc}"
        return "Brightness control not available on this system."

    def brightness_down(self) -> str:
        return self.brightness_up()

    def shutdown(self) -> str:
        try:
            if IS_WINDOWS:
                subprocess.Popen(["shutdown", "/s", "/t", "1"])
            elif IS_LINUX:
                subprocess.Popen(["shutdown", "-h", "now"])
            else:
                return "Shutdown unsupported on this platform."
            return "Shutting down the system."
        except Exception as exc:
            return f"Failed to shutdown: {exc}"

    def restart(self) -> str:
        try:
            if IS_WINDOWS:
                subprocess.Popen(["shutdown", "/r", "/t", "1"])
            elif IS_LINUX:
                subprocess.Popen(["shutdown", "-r", "now"])
            else:
                return "Restart unsupported on this platform."
            return "Restarting the system."
        except Exception as exc:
            return f"Failed to restart: {exc}"

    def sleep(self) -> str:
        try:
            if IS_WINDOWS:
                subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
            elif IS_LINUX and command_exists("systemctl"):
                subprocess.Popen(["systemctl", "suspend"])
            else:
                return "Sleep unsupported on this platform."
            return "Putting system to sleep."
        except Exception as exc:
            return f"Failed to sleep: {exc}"

    def lock(self) -> str:
        try:
            if IS_WINDOWS:
                subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])
            elif IS_LINUX and command_exists("loginctl"):
                subprocess.Popen(["loginctl", "lock-session"])
            else:
                return "Lock unsupported on this platform."
            return "Locking the screen."
        except Exception as exc:
            return f"Failed to lock screen: {exc}"
