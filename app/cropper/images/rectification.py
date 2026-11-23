from __future__ import annotations
import cv2
import numpy as np
from PIL import Image
from .detection import order_corners

def rectify_square(
    rgb: np.ndarray,
    corners: np.ndarray,
    expansion_factor: float = 1.2,
) -> Image.Image:
    ordered = order_corners(corners)
    center = ordered.mean(axis=0)
    ordered = center + (ordered - center) * expansion_factor
    top_left, top_right, bottom_right, bottom_left = ordered
    width = round(
        max(
            np.linalg.norm(bottom_right - bottom_left),
            np.linalg.norm(top_right - top_left),
        )
    )
    height = round(
        max(
            np.linalg.norm(top_right - bottom_right),
            np.linalg.norm(top_left - bottom_left),
        )
    )
    side = max(32, width, height)
    destination = np.array(
        [[0, 0], [side - 1, 0], [side - 1, side - 1], [0, side - 1]],
        dtype=np.float32,
    )
    transform = cv2.getPerspectiveTransform(ordered, destination)
    cropped = cv2.warpPerspective(
        rgb,
        transform,
        (side, side),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return Image.fromarray(cropped)
