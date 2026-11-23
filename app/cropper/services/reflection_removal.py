from __future__ import annotations

from pathlib import Path
import os
import tempfile

import cv2
import numpy as np
from PIL import Image


def detect_reflection_mask(rgb: np.ndarray, sensitivity: int = 60) -> np.ndarray:
    """Estimate bright, low-saturation glare regions on glass."""
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("A imagem precisa estar no formato RGB.")
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    value = hsv[:, :, 2]
    saturation = hsv[:, :, 1]
    threshold = int(
        np.clip(max(185, float(np.percentile(value, 97)) - sensitivity * 0.45), 175, 250)
    )
    mask = np.where(
        (value >= threshold) & (saturation <= 115 - sensitivity // 4),
        255,
        0,
    ).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    minimum_area = max(24, int(rgb.shape[0] * rgb.shape[1] * 0.00008))
    components, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    cleaned = np.zeros_like(mask)
    for component in range(1, components):
        if stats[component, cv2.CC_STAT_AREA] >= minimum_area:
            cleaned[labels == component] = 255
    return cv2.dilate(cleaned, np.ones((3, 3), np.uint8))


def remove_reflections(
    rgb: np.ndarray,
    sensitivity: int = 60,
    mask: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    # Never guess from brightness: tape, the glass and highlights are valid
    # image content. Only an explicit, user-painted mask is processed.
    mask = np.zeros(rgb.shape[:2], dtype=np.uint8) if mask is None else mask
    if mask.shape != rgb.shape[:2]:
        raise ValueError("A marcação do reflexo não corresponde à imagem.")
    if np.count_nonzero(mask) > mask.size * 0.28:
        raise ValueError(
            "A área marcada é grande demais. Marque apenas o objeto, a mão ou a luz refletida."
        )
    if not np.any(mask):
        return rgb.copy(), mask
    return cv2.inpaint(rgb, mask, 5, cv2.INPAINT_NS), mask


def backup_path(path: Path) -> Path:
    return Path(f"{path}.original")


def replace_with_backup(path: Path, rgb: np.ndarray) -> Path:
    backup = backup_path(path)
    if not backup.exists():
        with Image.open(path) as original:
            original.save(backup, format="PNG")
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix=path.suffix, delete=False) as temporary:
            temporary_name = temporary.name
        image = Image.fromarray(rgb.astype(np.uint8), mode="RGB")
        save_kwargs = {"quality": 95} if path.suffix.lower() in {".jpg", ".jpeg"} else {}
        image.save(temporary_name, **save_kwargs)
        os.replace(temporary_name, path)
    finally:
        if temporary_name and Path(temporary_name).exists():
            Path(temporary_name).unlink()
    return backup


def restore_original(path: Path) -> None:
    backup = backup_path(path)
    if not backup.exists():
        raise FileNotFoundError(f"Backup original não encontrado: {backup}")
    with Image.open(backup) as original:
        original.save(path)
