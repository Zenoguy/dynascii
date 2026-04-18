"""
utils/fps.py
------------
FPS tracking with rolling-window smoothing.

Uses time.perf_counter() for sub-millisecond precision.
Designed to be called once per rendered frame.
"""

import time
from collections import deque


class FPSTracker:
    """
    Rolling-window FPS and per-frame timing tracker.

    Args:
        window_size: Number of recent frame-times to average over.
    """

    def __init__(self, window_size: int = 30) -> None:
        self._window: deque[float] = deque(maxlen=window_size)
        self._last_tick: float | None = None
        self._frame_time_ms: float = 0.0

    def tick(self) -> None:
        """
        Record the completion of one frame.
        Call this at the END of each render loop iteration.
        """
        now = time.perf_counter()
        if self._last_tick is not None:
            dt = now - self._last_tick
            self._frame_time_ms = dt * 1000.0
            self._window.append(dt)
        self._last_tick = now

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def fps(self) -> float:
        """Smoothed FPS over the rolling window. Returns 0.0 before first tick."""
        if not self._window:
            return 0.0
        avg_dt = sum(self._window) / len(self._window)
        return 1.0 / avg_dt if avg_dt > 0 else 0.0

    @property
    def frame_time_ms(self) -> float:
        """Most recent frame duration in milliseconds."""
        return self._frame_time_ms

    def stats_string(self) -> str:
        """Human-readable stats for the renderer stats line."""
        return f"FPS: {self.fps:5.1f}  |  frame: {self.frame_time_ms:6.2f}ms"
