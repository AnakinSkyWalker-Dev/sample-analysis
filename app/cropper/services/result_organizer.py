from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re

from .label_enlarger import iter_result_images


_MATERIALS = {
    "m": "MDF",
    "v": "Vidro",
    "c": "Ceramica",
}
_CLEANERS = {
    "a": "Agua",
    "al": "Alcool",
    "d": "Detergente",
    "h": "Hipoclorito",
}
_FILENAME_PATTERN = re.compile(r"(?P<prefix>[a-z]+)(?P<duration>\d+)(?P<unit>m?)")


@dataclass(frozen=True)
class RenameEntry:
    source: Path
    destination: Path


@dataclass(frozen=True)
class SkippedEntry:
    path: Path
    reason: str


@dataclass(frozen=True)
class RenamePlan:
    root: Path
    renames: tuple[RenameEntry, ...]
    skipped: tuple[SkippedEntry, ...]
    conflicts: tuple[RenameEntry, ...]


def build_result_rename_plan(root: Path) -> RenamePlan:
    paths = iter_result_images(root)
    renames: list[RenameEntry] = []
    skipped: list[SkippedEntry] = []
    for path in paths:
        match = _FILENAME_PATTERN.fullmatch(path.stem.casefold())
        if match is None:
            skipped.append(SkippedEntry(path, "nome sem código reconhecido"))
            continue

        prefix = match.group("prefix")
        material_code = prefix[:1]
        cleaner_code = prefix[1:]
        if material_code not in _MATERIALS or cleaner_code not in _CLEANERS:
            skipped.append(SkippedEntry(path, "prefixo sem expansão definida"))
            continue

        duration_value = int(match.group("duration"))
        unit = match.group("unit")
        if unit == "m":
            duration = f"{duration_value}minutos"
        elif duration_value == 1440:
            duration = "24horas"
        else:
            skipped.append(SkippedEntry(path, "unidade de duração não definida"))
            continue

        new_stem = (
            f"{_MATERIALS[material_code]}"
            f"{_CLEANERS[cleaner_code]}"
            f"{duration}"
        )
        destination = path.with_name(f"{new_stem}{path.suffix}")
        if destination != path:
            renames.append(RenameEntry(path, destination))

    source_keys = {_path_key(entry.source) for entry in renames}
    destinations: dict[str, list[RenameEntry]] = {}
    for entry in renames:
        destination_key = _path_key(entry.destination)
        destinations.setdefault(destination_key, []).append(entry)

    conflicts = [
        entry
        for entries in destinations.values()
        if len(entries) > 1
        for entry in entries
    ]
    conflicts.extend(
        entry
        for entry in renames
        if entry.destination.exists()
        and _path_key(entry.destination) not in source_keys
    )

    return RenamePlan(
        root=root,
        renames=tuple(renames),
        skipped=tuple(skipped),
        conflicts=tuple(dict.fromkeys(conflicts)),
    )


def apply_result_renames(plan: RenamePlan) -> int:
    if plan.conflicts:
        raise FileExistsError("Há conflitos de nomes; nenhum arquivo foi alterado.")
    for entry in plan.renames:
        if not entry.source.is_file():
            raise FileNotFoundError(entry.source)
        if entry.destination.exists():
            raise FileExistsError(entry.destination)

    completed: list[RenameEntry] = []
    try:
        for entry in plan.renames:
            entry.source.rename(entry.destination)
            completed.append(entry)
    except OSError as error:
        rollback_errors: list[OSError] = []
        for entry in reversed(completed):
            try:
                entry.destination.rename(entry.source)
            except OSError as rollback_error:
                rollback_errors.append(rollback_error)
        if rollback_errors:
            details = "; ".join(str(item) for item in rollback_errors)
            raise OSError(
                f"Falha ao renomear e ao restaurar arquivos: {details}"
            ) from error
        raise
    return len(completed)


def _path_key(path: Path) -> str:
    return os.path.normcase(str(path.resolve()))
