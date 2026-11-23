from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import cv2
from ..images import PhotoResult, load_rgb, rectify_square

@dataclass
class ExportReport:
    saved: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

def crop_destinations(root: Path, result: PhotoResult) -> list[Path]:
    relative = result.path.relative_to(root)
    if len(result.corners) <= 1:
        return [root / "out" / relative]

    stem = relative.stem
    suffix = relative.suffix
    destinations = [root / "out" / relative]
    destinations.extend(
        root
        / "out"
        / relative.with_name(f"{stem}_quadrado_{index:02d}{suffix}")
        for index in range(2, len(result.corners) + 1)
    )
    return destinations


def export_crops(
    root: Path, results: list[PhotoResult], overwrite: bool = False
) -> ExportReport:
    report = ExportReport()
    for result in results:
        if not result.ready_for_export:
            continue
        for index, destination in enumerate(crop_destinations(root, result)):
            if destination.exists() and not overwrite:
                report.skipped += 1
                continue
            try:
                cropped = rectify_square(
                    load_rgb(result.path),
                    result.corners[index],
                    expansion_factor=1.0 if result.manual else 1.2,
                )
                destination.parent.mkdir(parents=True, exist_ok=True)
                options = (
                    {"quality": 95, "optimize": True}
                    if destination.suffix.casefold() in {".jpg", ".jpeg"}
                    else {}
                )
                cropped.save(destination, **options)
                report.saved += 1
            except (OSError, ValueError, cv2.error) as error:
                report.errors.append(f"{destination.name}: {error}")
    return report
