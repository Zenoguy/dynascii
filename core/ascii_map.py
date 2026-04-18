"""
core/ascii_map.py
-----------------
Intensity array → list of character strings.

The mapping is intentionally a pure function with no state.
Color application is handled SEPARATELY in core/color.py —
this module only deals with characters.
"""

import numpy as np

# ------------------------------------------------------------------
# Built-in charsets
# ------------------------------------------------------------------

CHARSETS: dict[str, str] = {
    # Classic 10-level gradient — research baseline
    "classic": " .:-=+*#%@",

    # Extended 70-level — more detail, heavier per-frame cost
    "extended": (
        " .'`^\",;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
    ),

    # Minimal 5-level — stress test for delta engine
    "minimal": " .+#@",

    # Blocks — striking, works well with color modes
    "blocks": " ░▒▓█",
}

# Default charset used when none is specified
DEFAULT_CHARSET = CHARSETS["classic"]


# ------------------------------------------------------------------
# Core mapping function
# ------------------------------------------------------------------

def map_to_ascii(
    norm_frame: np.ndarray,
    charset: str = DEFAULT_CHARSET,
) -> list[str]:
    """
    Map a normalized float32 grayscale array to a list of ASCII row strings.

    Args:
        norm_frame: float32 array of shape (H, W) with values in [0.0, 1.0].
        charset:    Character gradient string, darkest → brightest.

    Returns:
        List of H strings, each of length W.

    Implementation note:
        We use vectorized numpy operations to avoid Python-level per-pixel loops.
        idx = int(pixel * (len(charset) - 1))  — clamped to [0, len-1].
    """
    n = len(charset)
    # Scale [0.0, 1.0] → [0, n-1], clamp, cast to int indices
    indices = np.clip((norm_frame * (n - 1)).astype(np.int32), 0, n - 1)

    # Build a lookup array from charset
    lookup = np.array(list(charset), dtype="U1")

    # Map: shape (H, W) of unicode char → list of row strings
    char_array = lookup[indices]  # shape (H, W)
    rows = ["".join(row) for row in char_array]
    return rows
