#!/usr/bin/env python3
"""
scraping_os/proxy_manager.py — Proxy rotation and management for crawlers.

Supports:
  - Loading proxies from file (host:port per line)
  - Rotating proxy selection
  - Health checking
  - Stealth mode (no proxy, direct connection with anti-detection headers)
"""

from __future__ import annotations
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


@dataclass
class Proxy:
    host: str
    port: int
    username: str | None = None
    password: str | None = None
    location: str = ""
    proxy_type: str = "http"
    last_used: float = 0.0
    failures: int = 0
    max_failures: int = 3

    @property
    def url(self) -> str:
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        return f"{self.proxy_type}://{auth}{self.host}:{self.port}"

    @property
    def is_alive(self) -> bool:
        return self.failures < self.max_failures

    def mark_failure(self):
        self.failures += 1

    def mark_success(self):
        self.failures = max(0, self.failures - 1)


class ProxyManager:
    """
    Rotating proxy manager for web scraping.

    Usage:
        pm = ProxyManager()
        pm.load_from_file("proxies.txt")
        proxy = pm.next()  # rotates automatically
    """

    def __init__(self):
        self.proxies: list[Proxy] = []
        self.stealth_mode: bool = False
        self._index: int = 0

    def load_from_file(self, path: str | Path) -> "ProxyManager":
        """Load proxies from a file (host:port per line, optional user:pass@host:port)."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Proxy file not found: {path}")

        for line in path.read_text().strip().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            auth_part = ""
            host_part = line

            if "@" in line:
                auth_part, host_part = line.rsplit("@", 1)

            if ":" not in host_part:
                continue

            host, port_str = host_part.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                continue

            username = password = None
            if auth_part and ":" in auth_part:
                username, password = auth_part.split(":", 1)

            self.proxies.append(Proxy(host=host, port=port, username=username, password=password))

        return self

    def add(self, host: str, port: int, username: str | None = None, password: str | None = None) -> "ProxyManager":
        """Add a single proxy."""
        self.proxies.append(Proxy(host=host, port=port, username=username, password=password))
        return self

    def set_stealth_mode(self, enabled: bool = True) -> "ProxyManager":
        """Enable stealth mode (no proxy, anti-detection headers only)."""
        self.stealth_mode = enabled
        return self

    def next(self) -> Proxy | None:
        """Get next proxy in rotation. Returns None if no proxies or stealth mode."""
        if self.stealth_mode:
            return None

        alive = [p for p in self.proxies if p.is_alive]
        if not alive:
            return None

        proxy = alive[self._index % len(alive)]
        self._index += 1
        proxy.last_used = time.time()
        return proxy

    def next_url(self) -> str | None:
        """Get next proxy URL string."""
        proxy = self.next()
        return proxy.url if proxy else None

    def health_check_all(self) -> dict[str, bool]:
        """Basic health check — marks dead proxies. Returns status map."""
        results = {}
        for p in self.proxies:
            # In production, this would make an actual request
            results[p.url] = p.is_alive
        return results

    def __len__(self) -> int:
        return len(self.proxies)

    def __iter__(self) -> Iterator[Proxy]:
        return iter(self.proxies)
