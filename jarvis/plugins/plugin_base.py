"""Base plugin interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class PluginBase(ABC):
    name = "base"

    @abstractmethod
    def execute(self, command: str) -> str:
        raise NotImplementedError
