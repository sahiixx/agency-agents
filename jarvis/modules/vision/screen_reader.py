"""Screen OCR and optional LLM-enhanced description."""

from __future__ import annotations

try:
    import pytesseract  # type: ignore
except Exception:  # pragma: no cover
    pytesseract = None

try:
    from PIL import ImageGrab  # type: ignore
except Exception:  # pragma: no cover
    ImageGrab = None

from ..ai_brain import AIBrain


class ScreenReader:
    def __init__(self, brain: AIBrain | None = None):
        self.brain = brain
        self.available = pytesseract is not None and ImageGrab is not None

    def read_screen_text(self) -> str:
        if not self.available:
            return "Install pytesseract and Pillow for OCR: pip install pytesseract pillow"
        image = ImageGrab.grab()
        return pytesseract.image_to_string(image)

    def describe_screen(self) -> str:
        text = self.read_screen_text()
        if self.brain and text and not text.startswith("Install"):
            return self.brain.ask(f"Describe this screen content:\n{text}").text
        return text
