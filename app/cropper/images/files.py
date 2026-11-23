from __future__ import annotations
import os
from pathlib import Path
import sys
from PIL import Image, ImageOps
import numpy as np
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
SKIP_DIRECTORIES = {
    "artigos",
    "out",
    "imgs_results",
    ".venv",
    ".git",
    ".cache",
    "__pycache__",
}
PROJECT_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parents[2]
)
if getattr(sys, "frozen", False):
    DEFAULT_SOURCE_DIR = next(
        (
            candidate
            for candidate in (PROJECT_DIR, *PROJECT_DIR.parents)
            if all(
                (candidate / material).is_dir()
                for material in ("MDF", "Vidro")
            )
        ),
        PROJECT_DIR,
    )
else:
    DEFAULT_SOURCE_DIR = (
        PROJECT_DIR.parent
        if PROJECT_DIR.name.casefold() == "main"
        else PROJECT_DIR
    )

def load_rgb(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        return np.asarray(image)

def _raise_walk_error(error: OSError) -> None:
    raise error

def find_images(root: Path) -> list[Path]:
    if root.name.casefold() in SKIP_DIRECTORIES:
        return []
    images = []
    for current, directories, filenames in os.walk(root, onerror=_raise_walk_error):
        directories[:] = sorted(
            (name for name in directories if name.casefold() not in SKIP_DIRECTORIES),
            key=str.casefold,
        )
        for filename in filenames:
            path = Path(current, filename)
            if path.suffix.casefold() in IMAGE_EXTENSIONS:
                images.append(path)
    return sorted(images, key=lambda path: str(path.relative_to(root)).casefold())
