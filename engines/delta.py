"""
engines/delta.py
----------------
Delta (frame-differencing) engine: only update changed cells.

Algorithm:
  1. Compute |norm_t - norm_{t-1}| pixel-wise
  2. Threshold → boolean change mask
  3. Compute ASCII chars for ALL cells (cheap, vectorized)
  4. For changed cells, emit ANSI cursor-position commands to patch in-place
     \033[{row};{col}H{char}
  5. No full redraw — only cells that exceeded threshold are written

Key metric: changed_cells_count per frame
  → logged to CSV → your first experimental baseline in the paper

On the FIRST frame, falls back to a full render (no previous frame).
"""

import time

import numpy as np

from core.capture    import Capture
from core.preprocess import preprocess
from core.ascii_map  import map_to_ascii, DEFAULT_CHARSET
from core.color      import colorize_rows, PALETTE_FNS, _truecolor_escape, _256_escape, _val_to_256, _RESET
from core.renderer   import Renderer, get_terminal_size
from utils.fps       import FPSTracker
from utils.logger    import FrameLogger
from utils.frame_saver import FrameSaver


class DeltaEngine:
    """
    Frame-differencing ASCII rendering engine.

    Only patches terminal cells that changed beyond `threshold`.
    Logs `changed_cells` count — the primary research metric.

    Args:
        capture:      Opened Capture instance.
        renderer:     Renderer instance (startup already called).
        fps_tracker:  FPSTracker instance.
        logger:       FrameLogger (or None).
        frame_saver:  FrameSaver (or None).
        config:       Full parsed config dict.
    """

    ENGINE_LABEL = "delta"

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

        self._out_w      = config["capture"]["width"]
        self._out_h      = config["capture"]["height"]
        self._charset    = config["ascii"]["charset"]
        self._color_mode = config["renderer"].get("color_mode", "none")
        self._target_fps = config["capture"]["target_fps"]
        self._log_ivl    = config["logging"].get("log_interval_frames", 30)
        self._log_en     = config["logging"].get("enabled", True)
        self._save_en    = config["data"].get("save_frames", False)
        self._threshold  = config.get("delta", {}).get("threshold", 0.05)
        self._auto_size  = config["capture"].get("auto_size", False)
        self._aspect     = config["capture"].get("aspect_ratio", 0.55)
        self._contrast   = config["capture"].get("contrast_mode", "none")

        self._target_dt  = 1.0 / self._target_fps
        self._frame_id   = 0
        self._prev_norm: np.ndarray | None = None

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Start the render loop. Exits cleanly on Ctrl+C."""
        try:
            while True:
                loop_start = time.perf_counter()
                self._tick()
                elapsed = time.perf_counter() - loop_start
                sleep_t = self._target_dt - elapsed
                if sleep_t > 0:
                    time.sleep(sleep_t)
        except KeyboardInterrupt:
            pass

    # ------------------------------------------------------------------
    # Single frame
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        import sys
        t_start = time.perf_counter()

        # 0. Sync dimensions if auto-size is enabled
        if self._auto_size:
            cols, rows = get_terminal_size()
            new_w = cols
            new_h = rows - 1
            if new_w != self._out_w or new_h != self._out_h:
                # Resolution changed! Reset delta state to force full redraw
                self._out_w = new_w
                self._out_h = new_h
                self._prev_norm = None

        # 1. Capture
        frame = self._cap.read()
        if frame is None:
            return

        # 2. Preprocess
        norm = preprocess(frame, self._out_w, self._out_h, contrast_mode=self._contrast)

        # 3. ASCII mapping (full, vectorized — cheap)
        rows = map_to_ascii(norm, self._charset)

        # 4. Compute change mask
        if self._prev_norm is None:
            # First frame: full render via renderer (no diff available)
            changed_cells = self._out_w * self._out_h
            display_rows = rows
            if self._color_mode != "none":
                display_rows = colorize_rows(rows, norm, self._color_mode)
            self._fps.tick()
            stats = self._stats_str(changed_cells)
            self._renderer.render(display_rows, stats_line=stats, engine_label=self.ENGINE_LABEL)
        else:
            # Delta: only patch changed cells
            diff = np.abs(norm - self._prev_norm)
            change_mask = diff > self._threshold   # bool (H, W)
            changed_cells = int(change_mask.sum())

            if changed_cells > 0:
                patch_buf = self._build_patch(rows, norm, change_mask)
                sys.stdout.write(patch_buf)
                sys.stdout.flush()

            self._fps.tick()
            # Write stats line directly at bottom row (no cursor home — avoids flicker)
            stats = self._stats_str(changed_cells)
            self._write_stats_line(stats)

        self._prev_norm = norm
        proc_ms = (time.perf_counter() - t_start) * 1000.0

        # 5. Log
        if self._log_en and self._logger and (self._frame_id % self._log_ivl == 0):
            self._logger.log(
                frame_id=self._frame_id,
                fps=self._fps.fps,
                proc_ms=proc_ms,
                changed_cells=changed_cells,
            )

        # 6. Save frame
        if self._save_en and self._saver:
            self._saver.save(self._frame_id, norm)

        self._frame_id += 1

    # ------------------------------------------------------------------
    # Patch builder
    # ------------------------------------------------------------------

    def _build_patch(
        self,
        rows: list[str],
        norm: np.ndarray,
        change_mask: np.ndarray,
    ) -> str:
        """
        Build an ANSI string that repositions cursor to each changed cell
        and writes the new character (with optional color).

        ANSI format:  \033[{row+1};{col+1}H{char}   (1-indexed)
        """
        palette_fn = PALETTE_FNS.get(self._color_mode)
        parts: list[str] = []

        ys, xs = np.where(change_mask)  # row, col indices of changed cells

        for r, c in zip(ys.tolist(), xs.tolist()):
            char = rows[r][c]
            val  = float(norm[r, c])

            if self._color_mode == "none":
                cell = char
            elif self._color_mode == "256":
                idx  = _val_to_256(val)
                cell = f"{_256_escape(idx)}{char}{_RESET}"
            else:
                # truecolor or named palette
                fn  = palette_fn or (lambda v: (int(v*255), int(v*255), int(v*255)))
                rgb = fn(val)
                cell = f"{_truecolor_escape(*rgb)}{char}{_RESET}"

            parts.append(f"\033[{r+1};{c+1}H{cell}")

        return "".join(parts)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _write_stats_line(self, stats: str) -> None:
        """Write stats at the bottom row of the terminal without cursor home."""
        _, rows = get_terminal_size()
        _STATS_COLOR = "\033[38;2;80;200;120m"
        _BOLD        = "\033[1m"
        _RESET       = "\033[0m"
        line = f"\033[{rows};1H{_STATS_COLOR}{_BOLD}[{self.ENGINE_LABEL}] {stats}{_RESET}"
        import sys
        sys.stdout.write(line)
        sys.stdout.flush()

    def _stats_str(self, changed_cells: int) -> str:
        pct = (changed_cells / (self._out_w * self._out_h)) * 100
        return (
            f"{self._fps.stats_string()}  |  "
            f"Δcells: {changed_cells} ({pct:.1f}%)  |  "
            f"thr: {self._threshold}  |  "
            f"color: {self._color_mode}  |  "
            f"frame: {self._frame_id}"
        )
