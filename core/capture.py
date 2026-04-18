"""
core/capture.py
---------------
Webcam capture abstraction.
Owns the cv2.VideoCapture lifecycle and nothing else.
"""

import cv2
import numpy as np


class Capture:
    """
    Context-manager-safe webcam wrapper.

    Usage:
        with Capture(device_index=0, width=160, height=120) as cam:
            frame = cam.read()
    """

    def __init__(self, device_index: int = 0, width: int = 160, height: int = 120):
        self._device_index = device_index
        self._width = width
        self._height = height
        self._cap: cv2.VideoCapture | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def open(self) -> None:
        """Open the capture device and apply resolution/FPS hints."""
        self._cap = cv2.VideoCapture(self._device_index)
        if not self._cap.isOpened():
            raise RuntimeError(
                f"Could not open webcam at device index {self._device_index}. "
                "Check your device_index in configs/default.yaml."
            )
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
        # We manage our own FPS timing; this hint just reduces driver buffering.
        self._cap.set(cv2.CAP_PROP_FPS, 60)
        # Minimize internal buffer to get freshest frame.
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def release(self) -> None:
        """Release the underlying VideoCapture."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __enter__(self) -> "Capture":
        self.open()
        return self

    def __exit__(self, *_) -> None:
        self.release()

    # ------------------------------------------------------------------
    # Frame access
    # ------------------------------------------------------------------

    def read(self) -> np.ndarray | None:
        """
        Grab the next frame.

        Returns:
            BGR uint8 ndarray of shape (H, W, 3), or None on failure.
        """
        if self._cap is None:
            raise RuntimeError("Capture not opened — call open() first.")
        ok, frame = self._cap.read()
        return frame if ok else None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height
