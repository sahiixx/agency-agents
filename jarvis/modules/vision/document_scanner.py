"""Document scanner placeholder."""

from __future__ import annotations

from pathlib import Path


class DocumentScanner:
    """Pretend-scan documents into a target PDF path."""

    def scan(self, output_pdf: str) -> Path:
        target = Path(output_pdf).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"%PDF-1.4\n% JARVIS placeholder scan\n")
        return target
