from __future__ import annotations

from dataclasses import dataclass
import math
import os
from pathlib import Path
import tempfile

import cv2
import numpy as np
from PIL import Image, ImageOps

from ..images.files import IMAGE_EXTENSIONS


_DARK_THRESHOLD = 45
_MIN_SQUARE_SIZE = 18
_MAX_SQUARE_SIZE = 64
_TARGET_SCALE = 1.65
_ALREADY_ENLARGED_SIZE = 53


@dataclass(frozen=True)
class LabelSquare:
    x: int
    y: int
    size: int


def detect_letter_squares(image: Image.Image) -> list[LabelSquare]:
    gray = cv2.cvtColor(
        np.asarray(image.convert("RGB")),
        cv2.COLOR_RGB2GRAY,
    )
    foreground = (gray < _DARK_THRESHOLD).astype(np.uint8)
    _, _, stats, _ = cv2.connectedComponentsWithStats(foreground, 8)

    candidates: list[LabelSquare] = []
    for x, y, width, height, area in stats[1:]:
        size = max(width, height)
        fill = area / (width * height)
        if (
            not _MIN_SQUARE_SIZE <= size <= _MAX_SQUARE_SIZE
            or min(width, height) / size < 0.82
            or area < 300
            or fill < 0.58
        ):
            continue

        square_x = int(x + width - size if width > size else x)
        square_y = int(y)
        patch = gray[square_y : square_y + size, square_x : square_x + size]
        if patch.shape != (size, size):
            continue
        if np.count_nonzero(patch > 120) / patch.size < 0.08:
            continue
        candidates.append(LabelSquare(square_x, square_y, int(size)))

    if len(candidates) < 4:
        return []

    y_clusters = _cluster_coordinates([square.y for square in candidates])
    y_positions = [
        position
        for position in y_clusters
        if sum(abs(square.y - position) <= 12 for square in candidates) >= 2
        and any(
            450 <= abs(other - position) <= 510
            for other in y_clusters
            if other != position
        )
    ]
    row_candidates = [
        square
        for square in candidates
        if min(abs(square.y - position) for position in y_positions) <= 12
    ]
    x_clusters = _cluster_coordinates([square.x for square in row_candidates])
    supported_x = [
        position
        for position in x_clusters
        if any(
            450 <= abs(other - position) <= 510
            for other in x_clusters
            if other != position
        )
    ]
    x_positions = supported_x
    if len(x_positions) < 2 or len(y_positions) < 2:
        return []
    candidates = [
        square
        for square in row_candidates
        if min(abs(square.x - position) for position in x_positions) <= 70
    ]
    if len(candidates) < 4:
        return []

    size = int(round(float(np.median([square.size for square in candidates]))))
    confirmed: dict[tuple[int, int], LabelSquare] = {}
    for square in candidates:
        x_index = _nearest_cluster(square.x, x_positions)
        y_index = _nearest_cluster(square.y, y_positions)
        if (
            abs(square.x - x_positions[x_index]) > 70
            or abs(square.y - y_positions[y_index]) > 12
        ):
            continue
        key = (x_index, y_index)
        previous = confirmed.get(key)
        if previous is None or abs(square.x - x_positions[x_index]) < abs(
            previous.x - x_positions[x_index]
        ):
            confirmed[key] = LabelSquare(
                x_positions[x_index],
                y_positions[y_index],
                square.size,
            )

    if len(confirmed) / (len(x_positions) * len(y_positions)) < 0.5:
        return []

    for x_index, x in enumerate(x_positions):
        for y_index, y in enumerate(y_positions):
            key = (x_index, y_index)
            if key in confirmed:
                continue
            if _looks_like_letter_square(gray, x, y, size):
                confirmed[key] = LabelSquare(x, y, size)

    return sorted(
        confirmed.values(),
        key=lambda square: (square.y, square.x),
    )


def enlarge_letter_squares(
    image: Image.Image,
) -> tuple[Image.Image, int]:
    result = image.copy()
    changed = 0
    for square in detect_letter_squares(image):
        if square.size >= _ALREADY_ENLARGED_SIZE:
            continue
        target_size = math.ceil(square.size * _TARGET_SCALE)
        left = max(0, square.x + square.size - target_size)
        top = max(0, square.y)
        right = min(image.width, square.x + square.size)
        bottom = min(image.height, square.y + square.size)
        patch = image.crop((square.x, square.y, right, bottom))
        enlarged = patch.resize(
            (target_size, target_size),
            Image.Resampling.LANCZOS,
        )
        result.paste(enlarged, (left, top))
        changed += 1
    return result, changed


def count_pending_label_squares(squares: list[LabelSquare]) -> int:
    return sum(square.size < _ALREADY_ENLARGED_SIZE for square in squares)


def iter_result_images(root: Path) -> list[Path]:
    if not root.is_dir():
        raise NotADirectoryError(root)

    paths: list[Path] = []
    ignored_directories = {
        "artigos",
        "out",
        "montagem_12_quadrados",
        ".cache",
        ".git",
        ".venv",
        "__pycache__",
    }
    for current, directories, filenames in os.walk(root, onerror=_raise_walk_error):
        directories[:] = sorted(
            (
                name
                for name in directories
                if name.casefold() not in ignored_directories
            ),
            key=str.casefold,
        )
        paths.extend(
            Path(current, filename)
            for filename in filenames
            if Path(filename).suffix.casefold() in IMAGE_EXTENSIONS
        )
    return sorted(paths, key=lambda path: str(path.relative_to(root)).casefold())


def overwrite_with_enlarged_squares(path: Path) -> int:
    temporary_path: Path | None = None
    try:
        with Image.open(path) as source:
            if getattr(source, "n_frames", 1) != 1:
                raise ValueError("Imagens com várias páginas não são suportadas.")
            image = ImageOps.exif_transpose(source).copy()
            image_format = source.format
            exif = source.getexif()
            info = source.info.copy()

        if image_format is None:
            raise ValueError("Não foi possível identificar o formato da imagem.")

        if image.mode not in {"1", "L", "RGB", "RGBA"}:
            image = image.convert("RGBA" if "A" in image.getbands() else "RGB")

        updated, changed = enlarge_letter_squares(image)
        if not changed:
            return 0

        if 274 in exif:
            exif[274] = 1
        save_options: dict[str, object] = {}
        if "icc_profile" in info:
            save_options["icc_profile"] = info["icc_profile"]
        if "dpi" in info:
            save_options["dpi"] = info["dpi"]
        if exif:
            save_options["exif"] = exif.tobytes()
        if image_format.upper() in {"JPEG", "JPG"}:
            save_options.update(quality=100, subsampling=0)

        with tempfile.NamedTemporaryFile(
            dir=path.parent,
            suffix=path.suffix,
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
        updated.save(temporary_path, format=image_format, **save_options)
        os.replace(temporary_path, path)
        return changed
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _cluster_coordinates(values: list[int], tolerance: int = 12) -> list[int]:
    clusters: list[list[int]] = []
    for value in sorted(values):
        if not clusters or value - int(round(float(np.median(clusters[-1])))) > tolerance:
            clusters.append([value])
        else:
            clusters[-1].append(value)
    return [
        int(round(float(np.median(cluster))))
        for cluster in clusters
    ]


def _nearest_cluster(value: int, clusters: list[int]) -> int:
    return min(range(len(clusters)), key=lambda index: abs(value - clusters[index]))


def _looks_like_letter_square(
    gray: np.ndarray,
    x: int,
    y: int,
    size: int,
) -> bool:
    patch = gray[y : y + size, x : x + size]
    return (
        patch.shape == (size, size)
        and np.count_nonzero(patch < _DARK_THRESHOLD) / patch.size >= 0.55
        and np.count_nonzero(patch > 120) / patch.size >= 0.08
    )


def _raise_walk_error(error: OSError) -> None:
    raise error
