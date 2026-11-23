from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import numpy as np

@dataclass
class PhotoResult:
    path: Path
    corners: list[np.ndarray]
    error: str | None = None
    manual: bool = False
    needs_review: bool = False

    @property
    def ready_for_export(self) -> bool:
        return (
            not self.error
            and bool(self.corners)
            and (self.manual or not self.needs_review)
        )
