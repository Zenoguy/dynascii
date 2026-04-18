"""
core/color.py
-------------
Color palette engine — COMPLETELY SEPARATE from ascii_map.py.

Design contract:
  - All palette functions: float val ∈ [0.0, 1.0] → (R, G, B) tuple
  - ANSI wrapping happens here, NOT in the renderer
  - color_mode="none" → zero overhead, raw chars untouched

Supported modes:
  none        — no color wrapping (research baseline)
  256         — xterm 256-color approximation
  truecolor   — 24-bit ANSI per char
  matrix      — truecolor preset: deep green glow
  cyberpunk   — truecolor preset: purple → cyan → neon pink
  blood       — truecolor preset: black → deep red
  amber       — truecolor preset: retro amber terminal
  heatmap     — truecolor preset: blue→green→yellow→red
"""

from __future__ import annotations
import numpy as np

# ------------------------------------------------------------------
# ANSI escape primitives
# ------------------------------------------------------------------

_RESET = "\033[0m"


def _truecolor_escape(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"


def _256_escape(index: int) -> str:
    return f"\033[38;5;{index}m"


# ------------------------------------------------------------------
# Palette functions  (val ∈ [0.0, 1.0] → (R, G, B))
# ------------------------------------------------------------------

def _matrix(val: float) -> tuple[int, int, int]:
    """Deep green glow — classic Matrix terminal."""
    v = int(255 * val)
    return (0, max(30, v), max(10, int(70 * val)))


def _cyberpunk(val: float) -> tuple[int, int, int]:
    """
    Piecewise:
      low   (0.00–0.33) → purple   (180,   0, 255)
      mid   (0.33–0.66) → cyan     (  0, 255, 255)
      high  (0.66–1.00) → neon pink(255,   0, 180)
    Looks insane in motion.
    """
    if val < 0.33:
        t = val / 0.33
        return (int(180), int(t * 0), int(255))
    elif val < 0.66:
        t = (val - 0.33) / 0.33
        return (int(180 * (1 - t)), 255, 255)
    else:
        t = (val - 0.66) / 0.34
        return (int(255 * t + 0 * (1 - t)), int(255 * (1 - t)), int(255 * (1 - t) + 180 * t))


def _blood(val: float) -> tuple[int, int, int]:
    """Black → deep crimson glow."""
    return (int(255 * val), 0, 0)


def _amber(val: float) -> tuple[int, int, int]:
    """Retro hacker amber terminal."""
    v = int(255 * val)
    return (v, int(180 * val), 0)


def _heatmap(val: float) -> tuple[int, int, int]:
    """
    4-segment linear interpolation:
      0.00 → blue   (  0,   0, 255)
      0.25 → cyan   (  0, 255, 255)
      0.50 → green  (  0, 255,   0)
      0.75 → yellow (255, 255,   0)
      1.00 → red    (255,   0,   0)
    """
    stops = [
        (0.00, (0,   0, 255)),
        (0.25, (0, 255, 255)),
        (0.50, (0, 255,   0)),
        (0.75, (255, 255, 0)),
        (1.00, (255,  0,  0)),
    ]
    for i in range(len(stops) - 1):
        lo_v, lo_c = stops[i]
        hi_v, hi_c = stops[i + 1]
        if val <= hi_v:
            t = (val - lo_v) / (hi_v - lo_v)
            return tuple(int(lo_c[j] + t * (hi_c[j] - lo_c[j])) for j in range(3))
    return stops[-1][1]


def _neon(val: float) -> tuple[int, int, int]:
    """Electric Cyan → Lime → Bright Yellow."""
    stops = [
        (0.00, (0, 150, 255)),  # Deep Cyan
        (0.50, (0, 255, 0)),    # Pure Lime
        (1.00, (255, 255, 0)),  # Electric Yellow
    ]
    for i in range(len(stops) - 1):
        lo_v, lo_c = stops[i]
        hi_v, hi_c = stops[i + 1]
        if val <= hi_v:
            t = (val - lo_v) / (hi_v - lo_v)
            return tuple(int(lo_c[j] + t * (hi_c[j] - lo_c[j])) for j in range(3))
    return stops[-1][1]


# Named-mode → truecolor palette mapping
PALETTE_FNS: dict[str, callable] = {
    "matrix":    _matrix,
    "cyberpunk": _cyberpunk,
    "blood":     _blood,
    "amber":     _amber,
    "heatmap":   _heatmap,
    "neon":      _neon,
}

# All named modes are just truecolor presets
TRUECOLOR_ALIASES = set(PALETTE_FNS.keys())


# ------------------------------------------------------------------
# xterm-256 approximation
# ------------------------------------------------------------------

def _val_to_256(val: float) -> int:
    """
    Maps intensity → xterm 256 color index.
    Uses the 24-step greyscale ramp (indices 232–255) for best fidelity.
    Named palettes override this with truecolor anyway.
    """
    grey_index = int(val * 23)  # 0–23
    return 232 + grey_index     # 232–255


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def colorize_rows(
    rows: list[str],
    norm_frame: np.ndarray,
    color_mode: str,
) -> list[str]:
    """
    Apply ANSI color wrapping to precomputed ASCII rows.

    Args:
        rows:       List of H strings (from ascii_map.map_to_ascii).
        norm_frame: float32 (H, W) array — same frame used for char mapping.
        color_mode: One of "none", "256", "truecolor", or a palette name.

    Returns:
        List of H strings with embedded ANSI color codes.
        If color_mode="none", returns `rows` unchanged (zero overhead).
    """
    if color_mode == "none":
        return rows  # research baseline — zero cost

    H, W = norm_frame.shape
    palette_fn = PALETTE_FNS.get(color_mode)  # None if not a named palette

    colored_rows: list[str] = []

    for r_idx, row in enumerate(rows):
        vals = norm_frame[r_idx]  # shape (W,) float32

        if color_mode in TRUECOLOR_ALIASES or color_mode == "truecolor":
            # 24-bit truecolor
            fn = palette_fn or (lambda v: (int(v * 255), int(v * 255), int(v * 255)))
            parts = []
            for c_idx, char in enumerate(row):
                rgb = fn(float(vals[c_idx]))
                parts.append(f"{_truecolor_escape(*rgb)}{char}{_RESET}")
            colored_rows.append("".join(parts))

        elif color_mode == "256":
            parts = []
            for c_idx, char in enumerate(row):
                idx = _val_to_256(float(vals[c_idx]))
                parts.append(f"{_256_escape(idx)}{char}{_RESET}")
            colored_rows.append("".join(parts))

        else:
            # Unknown mode — fall back to no color
            colored_rows.append(row)

    return colored_rows
