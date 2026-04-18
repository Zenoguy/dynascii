"""
engines/baseline.py
-------------------
Baseline engine: full recompute every frame.

Pipeline per tick:
  capture() → preprocess() → map_to_ascii() → [colorize()] → render()

This is the research baseline. Every cell is recomputed unconditionally.
The delta engine will compare against this.
"""

import time
import sys

import numpy as np

from core.capture    import Capture
from core.preprocess import preprocess
from core.ascii_map  import map_to_ascii
from core.color      import colorize_rows
from core.renderer   import Renderer, get_terminal_size
from utils.fps       import FPSTracker
from utils.logger    import FrameLogger
from utils.frame_saver import FrameSaver


class BaselineEngine:
    """
    Full-recompute ASCII rendering engine.

    Args:
        capture:      Opened Capture instance.
        renderer:     Renderer instance (startup already called).
        fps_tracker:  FPSTracker instance.
        logger:       FrameLogger (or None to disable logging).
        frame_saver:  FrameSaver (or None to disable frame saving).
        config:       Full parsed config dict.
    """

    ENGINE_LABEL = "baseline"

    def __init__(
        self,
        capture: Capture,
        renderer: Renderer,
        fps_tracker: FPSTracker,
        logger: FrameLogger | None,
        frame_saver: FrameSaver | None,
        config: dict,
    ) -> None:
        self._cap         = capture
        self._renderer    = renderer
        self._fps         = fps_tracker
        self._logger      = logger
        self._saver       = frame_saver
        self._cfg         = config

        # Pre-extract hot-path config values
        self._out_w      = config["capture"]["width"]
        self._out_h      = config["capture"]["height"]
        self._charset    = config["ascii"]["charset"]
        self._color_mode = config["renderer"].get("color_mode", "none")
        self._target_fps = config["capture"]["target_fps"]
        self._log_ivl    = config["logging"].get("log_interval_frames", 30)
        self._log_en     = config["logging"].get("enabled", True)
        self._save_en    = config["data"].get("save_frames", False)
        self._auto_size  = config["capture"].get("auto_size", False)
        self._aspect     = config["capture"].get("aspect_ratio", 0.5)

        self._frame_id   = 0
        self._target_dt  = 1.0 / self._target_fps

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        """
        Start the render loop.
        Exits cleanly on KeyboardInterrupt (Ctrl+C).
        """
        try:
            while True:
                loop_start = time.perf_counter()
                self._tick()
                # Sleep to hit target FPS — avoids burning CPU
                elapsed = time.perf_counter() - loop_start
                sleep_t = self._target_dt - elapsed
                if sleep_t > 0:
                    time.sleep(sleep_t)

        except KeyboardInterrupt:
            # Clean exit: renderer shutdown is handled by context manager in main.py
            pass

    # ------------------------------------------------------------------
    # Single frame
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        t_start = time.perf_counter()

        # 0. Sync dimensions if auto-size is enabled
        if self._auto_size:
            cols, rows = get_terminal_size()
            # aspect ratio correction: usually terminal chars are 2:1 height:width
            # so we scale the number of ASCII rows accordingly.
            self._out_w = cols
            self._out_h = int((rows - 1) / self._aspect) # simple scaling
            # wait, actually we want the number of ASCII characters to match the terminal
            # If the terminal has 'rows' rows, we want max 'rows-1' ASCII rows (1 for stats)
            self._out_w = cols
            self._out_h = rows - 1

        # 1. Capture
        frame = self._cap.read()
        if frame is None:
            return  # dropped frame — skip silently

        # 2. Preprocess
        norm = preprocess(frame, self._out_w, self._out_h)

        # 3. ASCII mapping
        rows = map_to_ascii(norm, self._charset)

        # 4. Color (no-op if color_mode="none")
        if self._color_mode != "none":
            rows = colorize_rows(rows, norm, self._color_mode)

        # 5. Render
        self._fps.tick()
        stats = (
            f"{self._fps.stats_string()}  |  "
            f"res: {self._out_w}×{self._out_h}  |  "
            f"color: {self._color_mode}  |  "
            f"frame: {self._frame_id}"
        )
        self._renderer.render(rows, stats_line=stats, engine_label=self.ENGINE_LABEL)

        proc_ms = (time.perf_counter() - t_start) * 1000.0

        # 6. Log
        if self._log_en and self._logger and (self._frame_id % self._log_ivl == 0):
            self._logger.log(
                frame_id=self._frame_id,
                fps=self._fps.fps,
                proc_ms=proc_ms,
            )

        # 7. Save frame
        if self._save_en and self._saver:
            self._saver.save(self._frame_id, norm)

        self._frame_id += 1
