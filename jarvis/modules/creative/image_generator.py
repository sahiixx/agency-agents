"""Local image generation interface."""

from __future__ import annotations

from pathlib import Path

from jarvis.utils.optional_deps import OptionalDependencyError, safe_import


class ImageGenerator:
    """Generate placeholder image metadata if diffusers unavailable."""

    def generate(self, prompt: str, output_dir: str = "~/Pictures/JARVIS") -> Path | None:
        try:
            safe_import("diffusers", "pip install diffusers transformers torch")
        except OptionalDependencyError:
            return None
        out_dir = Path(output_dir).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / "generated-image.txt"
        target.write_text(prompt, encoding="utf-8")
        return target
