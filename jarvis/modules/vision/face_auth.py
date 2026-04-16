"""Face authentication using face_recognition and OpenCV."""

from __future__ import annotations

import threading

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None

try:
    import face_recognition  # type: ignore
except Exception:  # pragma: no cover
    face_recognition = None


class FaceAuth:
    def __init__(self):
        self.enabled = cv2 is not None and face_recognition is not None
        self.users = {}
        self._thread = None
        self._stop = threading.Event()

    def register_face(self, user_id: str, encoding) -> bool:
        if not self.enabled:
            return False
        self.users[user_id] = encoding
        return True

    def recognize(self, encoding) -> str | None:
        if not self.enabled:
            return None
        for user_id, known in self.users.items():
            if known == encoding:
                return user_id
        return None

    def start_background_auth(self):
        if self._thread and self._thread.is_alive():
            return

        def run():
            while not self._stop.is_set():
                self._stop.wait(1)

        self._stop.clear()
        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def stop_background_auth(self):
        self._stop.set()
