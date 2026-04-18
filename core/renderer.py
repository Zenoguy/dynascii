"""
core/renderer.py
----------------
Terminal renderer using raw ANSI escape codes.
No curses. No external dependencies.

Anti-flicker strategy:
  - Startup only: erase screen + hide cursor
  - Every frame:  cursor home (\033[H) — overwrite without erase
  This avoids the "white flash" from full-screen clears.
"""

import sys
import os

# ------------------------------------------------------------------
# ANSI escape sequences
# ------------------------------------------------------------------

_CURSOR_HOME      = "\033[H"       # move to (0, 0) — no erase
_ERASE_SCREEN     = "\033[2J"      # full erase (startup only)
_HIDE_CURSOR      = "\033[?25l"
_SHOW_CURSOR      = "\033[?25h"
_RESET_ALL        = "\033[0m"
_DIM              = "\033[2m"
_BOLD             = "\033[1m"

_STATS_COLOR      = "\033[38;2;80;200;120m"   # soft green stats line
_ENGINE_COLOR     = "\033[38;2;100;140;200m"  # muted blue engine label


class Renderer:
    """
    Raw-ANSI terminal renderer.

    Call render() once per frame. Manages startup erase, cursor hiding,
    and clean teardown on exit.
    """

    def __init__(self) -> None:
        self._initialized = False
        self._out = sys.stdout

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def startup(self) -> None:
        """One-time init: erase screen, hide cursor."""
        self._write(_ERASE_SCREEN + _CURSOR_HOME + _HIDE_CURSOR)
        self._initialized = True

    def shutdown(self) -> None:
        """Restore terminal to normal state."""
        self._write(_SHOW_CURSOR + _RESET_ALL + "\n")

    def __enter__(self) -> "Renderer":
        self.startup()
        return self

    def __exit__(self, *_) -> None:
        self.shutdown()

    # ------------------------------------------------------------------
    # Frame rendering
    # ------------------------------------------------------------------

    def render(
        self,
        ascii_rows: list[str],
        stats_line: str = "",
        engine_label: str = "",
    ) -> None:
        """
        Write a full ASCII frame to the terminal.

        Args:
            ascii_rows:   List of strings from ascii_map (possibly colorized).
            stats_line:   FPS / timing string appended as last visible line.
            engine_label: Short engine name shown in the stats bar.
        """
        if not self._initialized:
            self.startup()

        # Get terminal size to clamp output (avoids line wrapping artifacts)
        term_cols, term_rows = get_terminal_size()

        buf_parts: list[str] = [_CURSOR_HOME]

        # Render ASCII rows, trimmed to terminal width
        for row in ascii_rows[:term_rows - 1]:
            buf_parts.append(row[:term_cols])
            buf_parts.append("\n")

        # Stats line
        if stats_line:
            label_str = f"[{engine_label}] " if engine_label else ""
            buf_parts.append(
                f"{_STATS_COLOR}{_BOLD}{label_str}{stats_line}{_RESET_ALL}"
            )

        self._write("".join(buf_parts))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _write(self, text: str) -> None:
        self._out.write(text)
        self._out.flush()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def get_terminal_size() -> tuple[int, int]:
    """Return (cols, rows) of the current terminal."""
    try:
        size = os.get_terminal_size()
        return size.columns, size.lines
    except OSError:
        return 80, 24  # sane fallback
