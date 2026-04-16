"""Network status and diagnostics module."""

from __future__ import annotations

import socket

try:
    import speedtest  # type: ignore
except Exception:  # pragma: no cover
    speedtest = None


class NetworkInfo:
    """Get IP and run optional speed tests."""

    def local_ip(self) -> str:
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            return f"Local IP address is {ip}."
        except Exception as exc:
            return f"Could not determine IP: {exc}"

    def speed_test(self) -> str:
        if speedtest is None:
            return "speedtest-cli is not installed."
        try:
            test = speedtest.Speedtest()
            down = test.download() / 1_000_000
            up = test.upload() / 1_000_000
            return f"Download speed {down:.2f} Mbps and upload speed {up:.2f} Mbps."
        except Exception as exc:
            return f"Speed test failed: {exc}"
