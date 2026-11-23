from __future__ import annotations
from pathlib import Path
import cv2
import numpy as np
from ..images import (
    PhotoResult,
    detect_squares,
    find_images,
    load_rgb,
    suggest_squares,
)


def needs_manual_review(
    image_shape: tuple[int, ...], corners: list[np.ndarray]
) -> bool:
    if len(corners) != 1:
        return len(corners) > 1
    height, width = image_shape[:2]
    coverage = abs(cv2.contourArea(corners[0])) / (height * width)
    aspect = max(width / height, height / width)
    return coverage < 0.16 or (aspect > 1.7 and coverage < 0.3)


def _candidate_area(corners: np.ndarray) -> float:
    return abs(cv2.contourArea(corners))


def _overlap_fraction(first: np.ndarray, second: np.ndarray) -> float:
    x, y, width, height = cv2.boundingRect(first)
    other_x, other_y, other_width, other_height = cv2.boundingRect(second)
    intersection = max(
        0, min(x + width, other_x + other_width) - max(x, other_x)
    ) * max(
        0, min(y + height, other_y + other_height) - max(y, other_y)
    )
    smaller_box = min(width * height, other_width * other_height)
    return intersection / smaller_box if smaller_box else 0.0


def _deduplicate_candidates(
    candidates: list[np.ndarray], overlap_threshold: float
) -> list[np.ndarray]:
    unique: list[np.ndarray] = []
    for candidate in sorted(candidates, key=_candidate_area, reverse=True):
        if any(
            _overlap_fraction(candidate, known) >= overlap_threshold
            for known in unique
        ):
            continue
        unique.append(candidate)
    return unique


def _combine_candidates(
    rgb: np.ndarray, candidates: list[np.ndarray]
) -> list[np.ndarray]:
    image_area = rgb.shape[0] * rgb.shape[1]
    candidates = _deduplicate_candidates(candidates, 0.92)

    composite_candidates = set()
    for parent_index, parent in enumerate(candidates):
        parent_area = _candidate_area(parent)
        if parent_area <= 0:
            continue

        children = []
        for child_index, child in enumerate(candidates):
            if parent_index == child_index:
                continue
            child_area = _candidate_area(child)
            if child_area < max(image_area * 0.01, parent_area * 0.025):
                continue
            intersection, _ = cv2.intersectConvexConvex(
                parent.astype(np.float32), child.astype(np.float32)
            )
            if child_area and intersection / child_area >= 0.88:
                children.append(child_index)

        independent_children = []
        for child_index in children:
            child = candidates[child_index]
            if all(
                _overlap_fraction(child, candidates[known_index]) < 0.2
                for known_index in independent_children
            ):
                independent_children.append(child_index)
        if len(independent_children) >= 2:
            composite_candidates.add(parent_index)

    remaining = [
        candidate
        for index, candidate in enumerate(candidates)
        if index not in composite_candidates
    ]
    remaining = [
        candidate
        for candidate in remaining
        if not (
            _candidate_area(candidate) < image_area * 0.08
            and any(
                _candidate_area(parent) > _candidate_area(candidate)
                and _overlap_fraction(candidate, parent) >= 0.88
                for parent in remaining
            )
        )
    ]
    return _deduplicate_candidates(remaining, 0.68)


def _boundary_support_scores(
    rgb: np.ndarray, corners: list[np.ndarray]
) -> list[float]:
    height, width = rgb.shape[:2]
    scale = min(1.0, 1000 / max(height, width))
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
    gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 35, 110)
    distance = cv2.distanceTransform(255 - edges, cv2.DIST_L2, 3)

    scores = []
    for corners_for_square in corners:
        polygon = corners_for_square * np.array([scale_x, scale_y])
        side_support = []
        for index in range(4):
            start = polygon[index]
            end = polygon[(index + 1) % 4]
            positions = np.linspace(0.06, 0.94, 120)
            samples = (
                start[None, :] + (end - start)[None, :] * positions[:, None]
            )
            samples = np.rint(samples).astype(np.int32)
            samples[:, 0] = np.clip(samples[:, 0], 0, small.shape[1] - 1)
            samples[:, 1] = np.clip(samples[:, 1], 0, small.shape[0] - 1)
            side_support.append(
                float(np.mean(distance[samples[:, 1], samples[:, 0]] <= 5))
            )
        scores.append(min(side_support))
    return scores


def _has_plausible_square_geometry(corners: np.ndarray) -> bool:
    sides = np.linalg.norm(corners - np.roll(corners, -1, axis=0), axis=1)
    if np.min(sides) <= 0:
        return False
    opposite_ratios = (
        min(sides[0], sides[2]) / max(sides[0], sides[2]),
        min(sides[1], sides[3]) / max(sides[1], sides[3]),
    )
    if min(opposite_ratios) < 0.58:
        return False

    for index in range(4):
        first = corners[(index - 1) % 4] - corners[index]
        second = corners[(index + 1) % 4] - corners[index]
        cosine = np.dot(first, second) / (
            np.linalg.norm(first) * np.linalg.norm(second)
        )
        angle = np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))
        if not 35 <= angle <= 145:
            return False
    return True


def has_confident_boundaries(
    rgb: np.ndarray, corners: list[np.ndarray]
) -> bool:
    count = len(corners)
    if count == 0 or count > 12:
        return False
    if any(not _has_plausible_square_geometry(polygon) for polygon in corners):
        return False

    height, width = rgb.shape[:2]
    image_area = height * width
    areas = [abs(cv2.contourArea(polygon)) / image_area for polygon in corners]
    if count == 1:
        if needs_manual_review(rgb.shape, corners):
            return False
        minimum_support = 0.45
    else:
        minimum_area = 0.04 if count > 4 else 0.08
        if min(areas) < minimum_area or min(areas) / max(areas) < 0.35:
            return False
        minimum_support = 0.5

        for index, polygon in enumerate(corners):
            for other in corners[index + 1 :]:
                intersection, _ = cv2.intersectConvexConvex(
                    polygon.astype(np.float32),
                    other.astype(np.float32),
                )
                smaller_area = min(
                    abs(cv2.contourArea(polygon)),
                    abs(cv2.contourArea(other)),
                )
                if smaller_area and intersection / smaller_area > 0.15:
                    return False

    return min(_boundary_support_scores(rgb, corners)) >= minimum_support


def _collect_candidates(rgb: np.ndarray) -> list[np.ndarray]:
    main_candidates = detect_squares(rgb)
    alternatives = suggest_squares(rgb)
    if not main_candidates and not alternatives:
        alternatives = suggest_squares(rgb, low_contrast=True)
    image_area = rgb.shape[0] * rgb.shape[1]
    selected = list(main_candidates)

    if not main_candidates:
        return _combine_candidates(
            rgb,
            [
                candidate
                for candidate in alternatives
                if _candidate_area(candidate) >= image_area * 0.008
            ],
        )

    for candidate in alternatives:
        area = _candidate_area(candidate)
        support = min(_boundary_support_scores(rgb, [candidate]))
        if (
            area < image_area * 0.015
            or not _has_plausible_square_geometry(candidate)
            or support < 0.35
        ):
            continue

        overlapping = [
            known
            for known in main_candidates
            if _overlap_fraction(candidate, known) >= 0.55
        ]
        if overlapping and any(
            area > _candidate_area(known) * 1.15 for known in overlapping
        ):
            selected.append(candidate)
        elif (
            not overlapping
            and area >= image_area * 0.04
            and support >= 0.75
        ):
            selected.append(candidate)

    return _combine_candidates(rgb, selected)


def scan_images(
    root: Path,
    skip_paths: set[Path] | None = None,
) -> list[PhotoResult]:
    results = []
    for path in find_images(root):
        if skip_paths and path in skip_paths:
            continue
        try:
            image = load_rgb(path)
            corners = _collect_candidates(image)
            if len(corners) > 1:
                needs_review = not has_confident_boundaries(image, corners)
            else:
                needs_review = bool(corners) and (
                    needs_manual_review(image.shape, corners)
                    or not has_confident_boundaries(image, corners)
                )
            results.append(
                PhotoResult(
                    path,
                    corners,
                    needs_review=needs_review,
                )
            )
        except (OSError, ValueError, cv2.error) as error:
            results.append(PhotoResult(path, [], str(error)))
    return results
