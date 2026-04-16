"""Local AI music generation interface."""

from __future__ import annotations

from pathlib import Path

from jarvis.utils.optional_deps import OptionalDependencyError, safe_import


class MusicGenerator:
    """Generate placeholder music artifact when available."""

    def generate(self, prompt: str, output_dir: str = "~/Music/JARVIS") -> Path | None:
        try:
            safe_import("audiocraft", "pip install audiocraft")
        except OptionalDependencyError:
            return None
        out_dir = Path(output_dir).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / "generated-music.txt"
        target.write_text(prompt, encoding="utf-8")
        return target
