"""Shared capture (F13): one grab thread per camera, every consumer reads the same frame.

The policy and the inspector never open a camera themselves, so each USB stream is read once.
"""

import threading
import time
from typing import Protocol

import cv2
import numpy as np


class Camera(Protocol):
    def read(self) -> np.ndarray | None: ...


class OpenCVCamera:
    def __init__(self, path: str | int, fourcc: str | None = None):
        self._cap = cv2.VideoCapture(path)
        if not self._cap.isOpened():
            raise RuntimeError(f"cannot open camera {path}")
        if fourcc:
            # Some cameras (the Sonix wrist cam) send nothing in their default YUYV and only stream in MJPG.
            self._cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))

    def read(self) -> np.ndarray | None:
        ok, frame = self._cap.read()
        return frame if ok else None

    def release(self) -> None:
        self._cap.release()


class SharedCapture:
    def __init__(self, cameras: dict[str, Camera]):
        self._cameras = cameras
        self._latest: dict[str, tuple[float, np.ndarray]] = {}
        self._fresh = threading.Condition()
        self._running = False
        self._threads: list[threading.Thread] = []
        self.grabs = dict.fromkeys(cameras, 0)

    def start(self) -> "SharedCapture":
        self._running = True
        for role, cam in self._cameras.items():
            t = threading.Thread(target=self._grab_loop, args=(role, cam), name=f"capture-{role}", daemon=True)
            t.start()
            self._threads.append(t)
        return self

    def stop(self) -> None:
        self._running = False
        for t in self._threads:
            t.join(timeout=1.0)
        for cam in self._cameras.values():
            if hasattr(cam, "release"):
                cam.release()

    def frame(self, role: str, newer_than: float = 0.0, timeout_s: float = 1.0) -> np.ndarray:
        """Latest frame from `role` grabbed after `newer_than` (a time.monotonic() stamp).

        Pass the moment the arm stopped, so the inspector never scores a frame taken mid-motion.
        """
        deadline = time.monotonic() + timeout_s
        with self._fresh:
            while role not in self._latest or self._latest[role][0] <= newer_than:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(f"no fresh frame from {role} camera within {timeout_s}s")
                self._fresh.wait(remaining)
            return self._latest[role][1]

    def _grab_loop(self, role: str, cam: Camera) -> None:
        while self._running:
            frame = cam.read()
            if frame is None:
                time.sleep(0.01)  # an unplugged camera fails instantly; don't spin a core
                continue
            with self._fresh:
                self._latest[role] = (time.monotonic(), frame)
                self.grabs[role] += 1
                self._fresh.notify_all()
