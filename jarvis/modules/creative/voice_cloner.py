"""Voice cloning interface."""

from __future__ import annotations

from jarvis.utils.optional_deps import OptionalDependencyError, safe_import


class VoiceCloner:
    """Create/select local voice profiles."""

    def clone(self, sample_path: str) -> dict[str, str | bool]:
        try:
            safe_import("TTS", "pip install TTS")
        except OptionalDependencyError as exc:
            return {"ok": False, "reason": str(exc), "sample": sample_path}
        return {"ok": True, "profile": "user-default", "sample": sample_path}
