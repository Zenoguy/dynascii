"""
utils/logger.py
---------------
CSV frame logger for research benchmarking.

Schema:
  frame_id, timestamp_ms, fps, proc_ms, changed_cells

- changed_cells is NULL for baseline engine (not applicable).
- Writes are buffered and flushed every `log_interval_frames`.
- Designed for direct pandas.read_csv() consumption.
"""

import csv
import os
import time
from pathlib import Path


class FrameLogger:
    """
    Appends one CSV row per logged frame to logs/session_<timestamp>.csv.

    Args:
        log_dir:            Directory to write CSV files into.
        log_interval_frames: Flush to disk every N frames.
    """

    _FIELDS = ["frame_id", "timestamp_ms", "fps", "proc_ms", "changed_cells"]

    def __init__(self, log_dir: str, log_interval_frames: int = 30) -> None:
        self._interval = log_interval_frames
        self._frame_count = 0
        self._session_start = time.time()

        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        ts = time.strftime("%Y%m%d_%H%M%S")
        self._filepath = log_path / f"session_{ts}.csv"

        self._file = open(self._filepath, "w", newline="", buffering=1)
        self._writer = csv.DictWriter(self._file, fieldnames=self._FIELDS)
        self._writer.writeheader()

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def log(
        self,
        frame_id: int,
        fps: float,
        proc_ms: float,
        changed_cells: int | None = None,
    ) -> None:
        """
        Write one row.

        Args:
            frame_id:      Monotonic frame counter.
            fps:           Smoothed FPS at this frame.
            proc_ms:       Frame processing time in milliseconds.
            changed_cells: Number of cells updated (delta engine only), or None.
        """
        elapsed_ms = (time.time() - self._session_start) * 1000.0
        self._writer.writerow({
            "frame_id":     frame_id,
            "timestamp_ms": round(elapsed_ms, 2),
            "fps":          round(fps, 2),
            "proc_ms":      round(proc_ms, 3),
            "changed_cells": changed_cells if changed_cells is not None else "",
        })
        self._frame_count += 1

        if self._frame_count % self._interval == 0:
            self._file.flush()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Flush and close the CSV file."""
        if not self._file.closed:
            self._file.flush()
            self._file.close()

    def __enter__(self) -> "FrameLogger":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    @property
    def filepath(self) -> Path:
        return self._filepath
