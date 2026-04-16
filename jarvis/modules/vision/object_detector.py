"""YOLOv8 object detection wrappers."""

from __future__ import annotations

try:
    from ultralytics import YOLO  # type: ignore
except Exception:  # pragma: no cover
    YOLO = None


class ObjectDetector:
    def __init__(self, model: str = "yolov8n.pt"):
        self.model_name = model
        self.model = YOLO(model) if YOLO else None

    def detect(self, source=0):
        if self.model is None:
            return "Install ultralytics for object detection: pip install ultralytics"
        return self.model.predict(source=source)
