"""
utils/frame_saver.py
--------------------
Saves raw normalized grayscale frames as .npy arrays for:
  - Reproducibility (replay offline, evaluate multiple methods on same data)
  - Fair comparison across engines
  - Paper figures and plots

Also writes a metadata.json capturing the full session config.

File layout:
  data/frames/
    metadata.json
    frame_000000.npy
    frame_000001.npy
    ...
"""

import json
import os
import time
from pathlib import Path
from collections import deque

import numpy as np


class FrameSaver:
    """
    Saves normalized grayscale frames and session metadata.

    Args:
        frame_dir:  Directory to write .npy files into.
        metadata:   Dict of session-level metadata written to metadata.json.
        max_frames: Maximum number of frames to keep on disk (0 for infinite).
    """

    def __init__(self, frame_dir: str, metadata: dict, max_frames: int = 1000) -> None:
        self._frame_dir = Path(frame_dir)
        self._frame_dir.mkdir(parents=True, exist_ok=True)
        self._enabled = True
        self._max_frames = max_frames
        self._history: deque[Path] = deque()

        # Always stamp the session start time
        metadata = {
            "session_start": time.strftime("%Y-%m-%dT%H:%M:%S"),
            **metadata,
        }

        meta_path = self._frame_dir / "metadata.json"
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

    # ------------------------------------------------------------------
    # Saving
    # ------------------------------------------------------------------

    def save(self, frame_id: int, norm_frame: np.ndarray) -> None:
        """
        Save one float32 [H × W] normalized frame.

        Args:
            frame_id:   Monotonic frame index (used for filename).
            norm_frame: float32 array of shape (H, W) in [0, 1].
        """
        if not self._enabled:
            return

        path = self._frame_dir / f"frame_{frame_id:06d}.npy"
        np.save(str(path), norm_frame)
        self._history.append(path)

        # Enforce sliding window
        if self._max_frames > 0 and len(self._history) > self._max_frames:
            old_path = self._history.popleft()
            if old_path.exists():
                old_path.unlink()

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    @property
    def frame_dir(self) -> Path:
        return self._frame_dir
