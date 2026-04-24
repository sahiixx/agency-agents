"""Home Assistant REST integration."""

from __future__ import annotations

from dataclasses import dataclass

import requests  # type: ignore[import-untyped]


@dataclass
class SmartHomeController:
    base_url: str
    token: str

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def call_service(self, domain: str, service: str, payload: dict) -> bool:
        if not self.base_url or not self.token:
            return False
        url = f"{self.base_url}/api/services/{domain}/{service}"
        response = requests.post(url, headers=self._headers(), json=payload, timeout=10)
        return response.ok

    def device_states(self):
        if not self.base_url or not self.token:
            return []
        response = requests.get(f"{self.base_url}/api/states", headers=self._headers(), timeout=10)
        if not response.ok:
            return []
        return response.json()
