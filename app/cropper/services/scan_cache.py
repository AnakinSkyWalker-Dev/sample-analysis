from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

import numpy as np

from ..images import PhotoResult, find_images
from ..images.files import PROJECT_DIR


CACHE_PATH = PROJECT_DIR / ".cache" / "scan_results.json"
CACHE_VERSION = 6


def get_cached_scan_root() -> Path | None:
    if not CACHE_PATH.is_file():
        return None
    with CACHE_PATH.open("r", encoding="utf-8") as cache_file:
        data = json.load(cache_file)
    if isinstance(data, dict) and isinstance(data.get("root"), str):
        return Path(data["root"])
    return None


def load_manual_scan_overrides(root: Path) -> dict[Path, PhotoResult]:
    if not CACHE_PATH.is_file():
        return {}

    with CACHE_PATH.open("r", encoding="utf-8") as cache_file:
        data = json.load(cache_file)
    if (
        not isinstance(data, dict)
        or data.get("root") != str(root.resolve())
        or not isinstance(data.get("photos"), list)
    ):
        return {}

    current_paths = {
        str(path.relative_to(root)): path for path in find_images(root)
    }
    overrides: dict[Path, PhotoResult] = {}
    for cached in data["photos"]:
        if not isinstance(cached, dict) or not cached.get("manual"):
            continue
        try:
            path = current_paths[cached["path"]]
            stat = path.stat()
            if (
                cached["size"] != stat.st_size
                or cached["mtime_ns"] != stat.st_mtime_ns
            ):
                continue
            corners = [
                np.asarray(points, dtype=np.float32)
                for points in cached["corners"]
            ]
            if not corners or any(corner.shape != (4, 2) for corner in corners):
                continue
            overrides[path] = PhotoResult(
                path=path,
                corners=corners,
                error=cached.get("error"),
                manual=True,
                needs_review=False,
            )
        except (KeyError, TypeError, ValueError):
            continue
    return overrides


def load_preserved_scan_results(root: Path) -> dict[Path, PhotoResult]:
    preserved = load_manual_scan_overrides(root)
    if not CACHE_PATH.is_file():
        return preserved

    with CACHE_PATH.open("r", encoding="utf-8") as cache_file:
        data = json.load(cache_file)
    if (
        not isinstance(data, dict)
        or data.get("version") != CACHE_VERSION
        or data.get("root") != str(root.resolve())
        or not isinstance(data.get("photos"), list)
    ):
        return preserved

    current_paths = {
        str(path.relative_to(root)): path for path in find_images(root)
    }
    for cached in data["photos"]:
        if not isinstance(cached, dict) or cached.get("manual"):
            continue
        try:
            path = current_paths[cached["path"]]
            stat = path.stat()
            if (
                cached["size"] != stat.st_size
                or cached["mtime_ns"] != stat.st_mtime_ns
            ):
                continue
            corners = [
                np.asarray(points, dtype=np.float32)
                for points in cached["corners"]
            ]
            if any(corner.shape != (4, 2) for corner in corners):
                continue
            result = PhotoResult(
                path=path,
                corners=corners,
                error=cached.get("error"),
                manual=False,
                needs_review=bool(cached.get("needs_review", False)),
            )
            if result.ready_for_export:
                preserved[path] = result
        except (KeyError, TypeError, ValueError):
            continue
    return preserved


def load_scan_cache(root: Path) -> list[PhotoResult] | None:
    if not CACHE_PATH.is_file():
        return None

    with CACHE_PATH.open("r", encoding="utf-8") as cache_file:
        data = json.load(cache_file)
    if (
        not isinstance(data, dict)
        or data.get("version") != CACHE_VERSION
        or data.get("root") != str(root.resolve())
        or not isinstance(data.get("photos"), list)
    ):
        return None

    current_paths = find_images(root)
    cached_photos = data["photos"]
    if len(cached_photos) != len(current_paths):
        return None

    results: list[PhotoResult] = []
    for path, cached in zip(current_paths, cached_photos):
        if not isinstance(cached, dict):
            return None
        try:
            relative = str(path.relative_to(root))
            stat = path.stat()
            if (
                cached["path"] != relative
                or cached["size"] != stat.st_size
                or cached["mtime_ns"] != stat.st_mtime_ns
            ):
                return None
            corners = [
                np.asarray(points, dtype=np.float32)
                for points in cached["corners"]
            ]
            if any(corner.shape != (4, 2) for corner in corners):
                return None
            results.append(
                PhotoResult(
                    path=path,
                    corners=corners,
                    error=cached.get("error"),
                    manual=bool(cached.get("manual", False)),
                    needs_review=bool(cached.get("needs_review", False)),
                )
            )
        except (KeyError, TypeError, ValueError):
            return None
    return results


def save_scan_cache(root: Path, results: list[PhotoResult]) -> None:
    photos = []
    for result in results:
        stat = result.path.stat()
        photos.append(
            {
                "path": str(result.path.relative_to(root)),
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "corners": [corner.tolist() for corner in result.corners],
                "error": result.error,
                "manual": result.manual,
                "needs_review": result.needs_review,
            }
        )

    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": CACHE_VERSION,
        "root": str(root.resolve()),
        "photos": photos,
    }
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=CACHE_PATH.parent,
            suffix=".tmp",
            delete=False,
        ) as cache_file:
            temporary_path = Path(cache_file.name)
            json.dump(payload, cache_file, ensure_ascii=False)
        os.replace(temporary_path, CACHE_PATH)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
