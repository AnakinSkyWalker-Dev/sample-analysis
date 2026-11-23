from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tempfile

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ..images.detection import detect_squares, order_corners, suggest_squares


GRID_COLUMNS = 4
GRID_ROWS = 3
GRID_TILE_SIZE = 480
DEFAULT_GRID_SPACING = 24
MAX_GRID_SPACING = 48
_MIN_CANDIDATE_AREA_RATIO = 0.30


@dataclass(frozen=True)
class _Candidate:
    corners: np.ndarray
    area: float
    source_priority: int


def detect_grid_squares(rgb: np.ndarray) -> tuple[list[np.ndarray], int]:
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("A imagem precisa estar no formato RGB.")
    height, width = rgb.shape[:2]
    if min(height, width) < 400:
        raise ValueError("A imagem está pequena demais para detectar a grade.")

    raw: list[_Candidate] = []
    for priority, detector, args in (
        (0, detect_squares, ()),
        (1, suggest_squares, (False,)),
        (2, suggest_squares, (True,)),
    ):
        for points in detector(rgb, *args):
            corners = order_corners(points)
            area = float(abs(cv2.contourArea(corners)))
            if area > 0:
                raw.append(_Candidate(corners, area, priority))
    if len(raw) < GRID_COLUMNS * GRID_ROWS:
        raise ValueError(
            "Não foi possível localizar quadrados suficientes. "
            "Tente outra foto com os quatro cantos mais visíveis."
        )

    median_area = float(np.median([candidate.area for candidate in raw]))
    candidates = [
        candidate
        for candidate in raw
        if candidate.area >= median_area * _MIN_CANDIDATE_AREA_RATIO
    ]
    candidates.sort(
        key=lambda item: (
            item.source_priority,
            abs(np.log(item.area / median_area)),
        )
    )
    unique: list[_Candidate] = []
    minimum_dimension = min(height, width)
    for candidate in candidates:
        center = candidate.corners.mean(axis=0)
        duplicate = False
        for known in unique:
            known_center = known.corners.mean(axis=0)
            if np.linalg.norm(center - known_center) < minimum_dimension * 0.055:
                duplicate = True
                break
            intersection, _ = cv2.intersectConvexConvex(
                candidate.corners.astype(np.float32),
                known.corners.astype(np.float32),
            )
            smaller_area = min(candidate.area, known.area)
            if smaller_area and intersection / smaller_area >= 0.55:
                duplicate = True
                break
        if not duplicate:
            unique.append(candidate)

    if len(unique) < GRID_COLUMNS:
        raise ValueError(
            f"Foram encontrados apenas {len(unique)} candidatos. "
            "Ajuste a iluminação ou use uma foto mais nítida."
        )

    centers = [candidate.corners.mean(axis=0) for candidate in unique]
    column_centers = _axis_clusters(
        [float(center[0]) for center in centers], GRID_COLUMNS
    )
    row_centers = _axis_clusters(
        [float(center[1]) for center in centers], GRID_ROWS
    )
    selected: dict[tuple[int, int], _Candidate] = {}
    for candidate in unique:
        center = candidate.corners.mean(axis=0)
        column = int(np.argmin(np.abs(np.asarray(column_centers) - center[0])))
        row = int(np.argmin(np.abs(np.asarray(row_centers) - center[1])))
        key = (row, column)
        current = selected.get(key)
        score = abs(np.log(candidate.area / median_area))
        current_score = (
            abs(np.log(current.area / median_area))
            if current is not None
            else float("inf")
        )
        if current is None or score < current_score:
            selected[key] = candidate

    original_count = len(selected)
    if original_count < 8:
        raise ValueError(
            f"Foram identificados {original_count} dos 12 quadrados. "
            "A detecção automática não é confiável para esta imagem."
        )

    grid = [[selected.get((row, column)) for column in range(GRID_COLUMNS)]
            for row in range(GRID_ROWS)]
    for row in range(GRID_ROWS):
        for column in range(GRID_COLUMNS):
            if grid[row][column] is not None:
                continue
            grid[row][column] = _infer_missing_square(
                grid,
                row,
                column,
            )

    squares = [
        candidate.corners.copy()
        for row in grid
        for candidate in row
        if candidate is not None
    ]
    if len(squares) != GRID_COLUMNS * GRID_ROWS:
        raise ValueError("Não foi possível completar a grade 4×3.")
    return squares, original_count


def compose_grid_montage(
    rgb: np.ndarray,
    squares: list[np.ndarray],
    spacing: int = DEFAULT_GRID_SPACING,
    rotations: list[int] | None = None,
) -> Image.Image:
    if len(squares) != GRID_COLUMNS * GRID_ROWS:
        raise ValueError("A montagem precisa conter os 12 quadrados da grade.")
    if not 0 <= spacing <= MAX_GRID_SPACING:
        raise ValueError(
            f"O espaçamento deve ficar entre 0 e {MAX_GRID_SPACING} pixels."
        )
    if rotations is None:
        rotations = [0] * len(squares)
    if len(rotations) != len(squares):
        raise ValueError("A montagem precisa ter uma rotação para cada quadrado.")

    width = (
        GRID_COLUMNS * GRID_TILE_SIZE
        + (GRID_COLUMNS - 1) * MAX_GRID_SPACING
    )
    height = (
        GRID_ROWS * GRID_TILE_SIZE
        + (GRID_ROWS - 1) * MAX_GRID_SPACING
    )
    content_width = GRID_COLUMNS * GRID_TILE_SIZE + (GRID_COLUMNS - 1) * spacing
    content_height = GRID_ROWS * GRID_TILE_SIZE + (GRID_ROWS - 1) * spacing
    offset_x = (width - content_width) // 2
    offset_y = (height - content_height) // 2
    source_height, source_width = rgb.shape[:2]
    background_mask = np.zeros((source_height, source_width), dtype=np.uint8)
    for corners in squares:
        polygon = np.round(order_corners(corners)).astype(np.int32)
        cv2.fillConvexPoly(background_mask, polygon, 255)
    background_mask = cv2.dilate(
        background_mask,
        np.ones((161, 161), dtype=np.uint8),
    )
    background_pixels = rgb[background_mask == 0]
    background_color = (
        np.median(background_pixels, axis=0).astype(np.uint8)
        if background_pixels.size
        else np.array([128, 128, 128], dtype=np.uint8)
    )
    background = Image.new(
        "RGB",
        (width, height),
        tuple(int(value) for value in background_color),
    )
    draw = ImageDraw.Draw(background)
    try:
        font = ImageFont.truetype(
            str(Path(r"C:\Windows\Fonts\arial.ttf")),
            50,
        )
    except OSError:
        font = ImageFont.load_default()

    destination = np.array(
        [
            [0, 0],
            [GRID_TILE_SIZE - 1, 0],
            [GRID_TILE_SIZE - 1, GRID_TILE_SIZE - 1],
            [0, GRID_TILE_SIZE - 1],
        ],
        dtype=np.float32,
    )
    for index, corners in enumerate(squares):
        row, column = divmod(index, GRID_COLUMNS)
        transform = cv2.getPerspectiveTransform(
            order_corners(corners).astype(np.float32),
            destination,
        )
        tile = cv2.warpPerspective(
            rgb,
            transform,
            (GRID_TILE_SIZE, GRID_TILE_SIZE),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
        tile = np.rot90(tile, k=int(rotations[index]) % 4).copy()
        x = offset_x + column * (GRID_TILE_SIZE + spacing)
        y = offset_y + row * (GRID_TILE_SIZE + spacing)
        background.paste(Image.fromarray(tile), (x, y))

        if row == 0:
            label = chr(ord("A") + column)
            bounds = draw.textbbox((0, 0), label, font=font)
            text_width = bounds[2] - bounds[0]
            text_height = bounds[3] - bounds[1]
            padding = 10
            right = x + GRID_TILE_SIZE - 14
            top = y + 14
            draw.rounded_rectangle(
                (
                    right - text_width - padding * 2,
                    top,
                    right,
                    top + text_height + padding * 2,
                ),
                radius=5,
                fill=(0, 0, 0),
            )
            draw.text(
                (
                    right - text_width - padding,
                    top + padding - bounds[1],
                ),
                label,
                fill=(255, 255, 255),
                font=font,
            )
    return background


def save_grid_montage(image: Image.Image, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            suffix=".png",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
        image.save(temporary_path, format="PNG", optimize=True)
        os.replace(temporary_path, destination)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _axis_clusters(values: list[float], count: int) -> list[float]:
    ordered = sorted(values)
    if len(ordered) < count:
        raise ValueError("Não há quadrados suficientes para formar uma grade.")
    boundaries = sorted(
        range(len(ordered) - 1),
        key=lambda index: ordered[index + 1] - ordered[index],
        reverse=True,
    )[: count - 1]
    split_after = sorted(boundaries)
    groups: list[list[float]] = []
    start = 0
    for index in split_after:
        groups.append(ordered[start : index + 1])
        start = index + 1
    groups.append(ordered[start:])
    centers = [float(np.median(group)) for group in groups]
    return sorted(centers)


def _infer_missing_square(
    grid: list[list[_Candidate | None]],
    target_row: int,
    target_column: int,
) -> _Candidate:
    known_centers = [
        (row, column, item.corners.mean(axis=0))
        for row, values in enumerate(grid)
        for column, item in enumerate(values)
        if item is not None
    ]
    if not known_centers:
        raise ValueError("Não há quadrados para completar a grade.")

    horizontal_steps = [
        center_b - center_a
        for row, values in enumerate(grid)
        for column in range(GRID_COLUMNS - 1)
        if (first := values[column]) is not None
        and (second := values[column + 1]) is not None
        for center_a, center_b in [
            (first.corners.mean(axis=0), second.corners.mean(axis=0))
        ]
    ]
    vertical_steps = [
        center_b - center_a
        for row in range(GRID_ROWS - 1)
        for column in range(GRID_COLUMNS)
        if (first := grid[row][column]) is not None
        and (second := grid[row + 1][column]) is not None
        for center_a, center_b in [
            (first.corners.mean(axis=0), second.corners.mean(axis=0))
        ]
    ]
    if not horizontal_steps:
        raise ValueError("Não foi possível estimar o espaçamento horizontal.")
    horizontal = np.median(np.stack(horizontal_steps), axis=0)
    vertical = (
        np.median(np.stack(vertical_steps), axis=0)
        if vertical_steps
        else np.array([0.0, 0.0])
    )

    source_row, source_column, source = min(
        known_centers,
        key=lambda item: (
            abs(item[0] - target_row) + abs(item[1] - target_column)
        ),
    )
    source_candidate = grid[source_row][source_column]
    if source_candidate is None:
        raise ValueError("Não foi possível inferir um quadrado ausente.")
    shift = (
        horizontal * (target_column - source_column)
        + vertical * (target_row - source_row)
    )
    return _Candidate(
        corners=source_candidate.corners + shift.astype(np.float32),
        area=source_candidate.area,
        source_priority=3,
    )
