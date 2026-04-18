"""
core/preprocess.py
------------------
BGR frame → normalized grayscale float32 array.

Pipeline:  BGR → grayscale → resize → normalize([0, 1])
"""

import cv2
import numpy as np


def preprocess(
    frame: np.ndarray,
    out_width: int,
    out_height: int,
) -> np.ndarray:
    """
    Convert a raw BGR webcam frame to a normalized grayscale float32 array.

    Args:
        frame:      Raw BGR uint8 frame from cv2.
        out_width:  Target columns (matches ASCII columns).
        out_height: Target rows (matches ASCII rows).

    Returns:
        float32 array of shape (out_height, out_width) with values in [0.0, 1.0].
        Luminance stability is critical for consistent ASCII mapping — normalization
        is applied *per-frame* to the full [0, 255] range, NOT per-pixel min/max,
        so relative intensities are preserved.
    """
    # Step 1: BGR → grayscale (single channel)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Step 2: Resize — INTER_AREA is best for downscaling (avoids aliasing)
    resized = cv2.resize(gray, (out_width, out_height), interpolation=cv2.INTER_AREA)

    # Step 3: Normalize to [0, 1] as float32
    normalized = resized.astype(np.float32) / 255.0

    return normalized
