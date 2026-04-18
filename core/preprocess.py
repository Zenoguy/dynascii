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
    contrast_mode: str = "none",
) -> np.ndarray:
    """
    Convert a raw BGR webcam frame to a normalized grayscale float32 array.

    Args:
        frame:          Raw BGR uint8 frame from cv2.
        out_width:      Target columns (matches ASCII columns).
        out_height:     Target rows (matches ASCII rows).
        contrast_mode:  Enhancement mode: 'none', 'normalize', or 'equalize'.

    Returns:
        float32 array of shape (out_height, out_width) with values in [0.0, 1.0].
    """
    # Step 1: BGR → grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Step 2: Contrast Enhancement (Applied on full-res grayscale)
    if contrast_mode == "normalize":
        # Min-max stretching to [0, 255]
        gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
    elif contrast_mode == "equalize":
        # Histogram equalization (aggressive feature popping)
        gray = cv2.equalizeHist(gray)

    # Step 3: Resize — INTER_AREA is best for downscaling
    resized = cv2.resize(gray, (out_width, out_height), interpolation=cv2.INTER_AREA)

    # Step 4: Normalize to [0, 1] as float32
    normalized = resized.astype(np.float32) / 255.0

    return normalized
