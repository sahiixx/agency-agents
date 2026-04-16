"""Helpers for graceful handling of optional dependencies."""

from __future__ import annotations

from importlib import import_module
from typing import Any


class OptionalDependencyError(RuntimeError):
    """Raised when optional dependency is missing."""


def safe_import(module_name: str, install_hint: str) -> Any:
    """Import a module and raise a user-friendly error if unavailable."""
    try:
        return import_module(module_name)
    except Exception as exc:  # pragma: no cover - intentionally broad
        raise OptionalDependencyError(
            f"Optional dependency '{module_name}' is not installed. Install with: {install_hint}"
        ) from exc
