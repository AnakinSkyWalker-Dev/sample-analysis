from __future__ import annotations
import cv2
import numpy as np

def order_corners(points: np.ndarray) -> np.ndarray:
    points = np.asarray(points, dtype=np.float32)
    center = points.mean(axis=0)
    angles = np.arctan2(points[:, 1] - center[1], points[:, 0] - center[0])
    ordered = points[np.argsort(angles)]
    start = np.argmin(ordered.sum(axis=1))
    return np.roll(ordered, -start, axis=0).astype(np.float32)

def detect_squares(rgb: np.ndarray) -> list[np.ndarray]:
    height, width = rgb.shape[:2]
    scale = min(1.0, 1600 / max(height, width))
    if scale < 1:
        small = cv2.resize(
            rgb,
            (round(width * scale), round(height * scale)),
            interpolation=cv2.INTER_AREA,
        )
    else:
        small = rgb
    scale_x = small.shape[1] / width
    scale_y = small.shape[0] / height
    image_height, image_width = small.shape[:2]
    image_area = image_height * image_width
    bgr = cv2.cvtColor(small, cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2Lab)
    channels = [
        cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY),
        hsv[:, :, 2],
        lab[:, :, 0],
    ]
    kernel = np.ones((5, 5), dtype=np.uint8)
    candidates: list[tuple[float, np.ndarray]] = []
    for channel in channels:
        blurred = cv2.GaussianBlur(channel, (5, 5), 0)
        median = float(np.median(blurred))
        thresholds = {
            (max(10, int(median * 0.55)), min(255, int(median * 1.35))),
            (35, 110),
        }
        for low, high in thresholds:
            if high <= low:
                high = min(255, low + 40)
            edges = cv2.Canny(blurred, low, high)
            edges = cv2.morphologyEx(
                edges, cv2.MORPH_CLOSE, kernel, iterations=2
            )
            contours, _ = cv2.findContours(
                edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
            )
            for contour in contours:
                area = cv2.contourArea(contour)
                if not image_area * 0.008 <= area <= image_area * 0.96:
                    continue
                perimeter = cv2.arcLength(contour, True)
                for epsilon in (0.018, 0.028):
                    polygon = cv2.approxPolyDP(
                        contour, epsilon * perimeter, True
                    )
                    if len(polygon) != 4 or not cv2.isContourConvex(polygon):
                        continue
                    corners = order_corners(polygon.reshape(4, 2))
                    sides = np.linalg.norm(
                        corners - np.roll(corners, -1, axis=0), axis=1
                    )
                    horizontal = (sides[0] + sides[2]) / 2
                    vertical = (sides[1] + sides[3]) / 2
                    if min(horizontal, vertical) < min(image_height, image_width) * 0.08:
                        continue
                    aspect = horizontal / max(vertical, 1)
                    if not 0.5 <= aspect <= 2:
                        continue
                    polygon_area = abs(cv2.contourArea(corners))
                    margin = min(image_height, image_width) * 0.015
                    touches_border = sum(
                        x <= margin
                        or x >= image_width - 1 - margin
                        or y <= margin
                        or y >= image_height - 1 - margin
                        for x, y in corners
                    )
                    if polygon_area > image_area * 0.2 and touches_border:
                        continue
                    candidates.append((polygon_area, corners))
    candidates.sort(key=lambda item: item[0], reverse=True)
    unique: list[tuple[float, np.ndarray]] = []
    for area, corners in candidates:
        x, y, box_width, box_height = cv2.boundingRect(corners)
        duplicate = False
        for _known_area, known in unique:
            kx, ky, kw, kh = cv2.boundingRect(known)
            intersection = max(0, min(x + box_width, kx + kw) - max(x, kx))
            intersection *= max(0, min(y + box_height, ky + kh) - max(y, ky))
            smaller_box = min(box_width * box_height, kw * kh)
            if smaller_box and intersection / smaller_box >= 0.68:
                duplicate = True
                break
        if not duplicate:
            unique.append((area, corners))
    return [
        np.clip(
            corners / np.array([scale_x, scale_y]),
            [0, 0],
            [width - 1, height - 1],
        ).astype(np.float32)
        for _, corners in unique
    ]


def suggest_squares(
    rgb: np.ndarray, low_contrast: bool = False
) -> list[np.ndarray]:
    """Find lower-confidence quadrilaterals for the manual-review workflow."""
    height, width = rgb.shape[:2]
    scale = min(1.0, 1100 / max(height, width))
    small = (
        cv2.resize(
            rgb,
            (round(width * scale), round(height * scale)),
            interpolation=cv2.INTER_AREA,
        )
        if scale < 1
        else rgb
    )
    scale_x = small.shape[1] / width
    scale_y = small.shape[0] / height
    image_height, image_width = small.shape[:2]
    image_area = image_height * image_width
    min_dimension = min(image_height, image_width)
    bgr = cv2.cvtColor(small, cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2Lab)
    channels = [
        cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY),
        lab[:, :, 0],
        hsv[:, :, 2],
    ]
    if not low_contrast:
        channels.append(hsv[:, :, 1])
    thresholds = (
        ((8, 24), (14, 42))
        if low_contrast
        else ((20, 60), (35, 110), (60, 180))
    )
    kernel_fractions = (
        (0.003, 0.008, 0.016)
        if low_contrast
        else (0.008, 0.016, 0.028)
    )
    minimum_area = 0.008 if low_contrast else 0.025
    candidates: list[tuple[float, np.ndarray]] = []
    for channel in channels:
        blurred = cv2.GaussianBlur(channel, (5, 5), 0)
        for low, high in thresholds:
            edges = cv2.Canny(blurred, low, high)
            for fraction in kernel_fractions:
                kernel_size = max(5, int(min_dimension * fraction))
                if kernel_size % 2 == 0:
                    kernel_size += 1
                kernel = np.ones((kernel_size, kernel_size), dtype=np.uint8)
                closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
                contours, _ = cv2.findContours(
                    closed, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
                )
                for contour in contours:
                    area = cv2.contourArea(contour)
                    if not image_area * minimum_area <= area <= image_area * 0.95:
                        continue
                    perimeter = cv2.arcLength(contour, True)
                    for epsilon in (0.012, 0.022, 0.04, 0.07):
                        polygon = cv2.approxPolyDP(
                            contour, epsilon * perimeter, True
                        )
                        if len(polygon) != 4 or not cv2.isContourConvex(polygon):
                            continue
                        corners = order_corners(polygon.reshape(4, 2))
                        sides = np.linalg.norm(
                            corners - np.roll(corners, -1, axis=0), axis=1
                        )
                        horizontal = (sides[0] + sides[2]) / 2
                        vertical = (sides[1] + sides[3]) / 2
                        if min(horizontal, vertical) < min_dimension * 0.08:
                            continue
                        aspect = horizontal / max(vertical, 1)
                        if not 0.5 <= aspect <= 2:
                            continue
                        polygon_area = abs(cv2.contourArea(corners))
                        margin = min_dimension * 0.015
                        touches_border = sum(
                            x <= margin
                            or x >= image_width - 1 - margin
                            or y <= margin
                            or y >= image_height - 1 - margin
                            for x, y in corners
                        )
                        if polygon_area > image_area * 0.2 and touches_border:
                            continue
                        candidates.append((polygon_area, corners))

    candidates.sort(key=lambda item: item[0], reverse=True)
    unique: list[tuple[float, np.ndarray]] = []
    for area, corners in candidates:
        x, y, box_width, box_height = cv2.boundingRect(corners)
        duplicate = False
        for _, known in unique:
            kx, ky, known_width, known_height = cv2.boundingRect(known)
            intersection = max(
                0, min(x + box_width, kx + known_width) - max(x, kx)
            )
            intersection *= max(
                0, min(y + box_height, ky + known_height) - max(y, ky)
            )
            smaller_box = min(
                box_width * box_height, known_width * known_height
            )
            if smaller_box and intersection / smaller_box >= 0.68:
                duplicate = True
                break
        if not duplicate:
            unique.append((area, corners))
    return [
        np.clip(
            corners / np.array([scale_x, scale_y]),
            [0, 0],
            [width - 1, height - 1],
        ).astype(np.float32)
        for _, corners in unique
    ]
