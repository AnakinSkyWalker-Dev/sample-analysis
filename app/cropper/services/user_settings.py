from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from ..images.files import PROJECT_DIR


SETTINGS_PATH = PROJECT_DIR / ".cache" / "user_settings.json"


def load_user_settings() -> dict[str, str]:
    if not SETTINGS_PATH.is_file():
        return {}
    with SETTINGS_PATH.open("r", encoding="utf-8") as settings_file:
        data = json.load(settings_file)
    if not isinstance(data, dict):
        return {}
    shortcuts = data.get("shortcuts", {})
    if not isinstance(shortcuts, dict):
        return {}
    return {
        key: value
        for key, value in shortcuts.items()
        if isinstance(key, str) and isinstance(value, str)
    }


def load_montage_selection() -> list[str]:
    data = _load_settings_data()
    selection = data.get("montage_selection", [])
    if not isinstance(selection, list):
        return []
    return [path for path in selection if isinstance(path, str)]


def load_montage_rotations() -> dict[str, int]:
    data = _load_settings_data()
    rotations = data.get("montage_rotations", {})
    if not isinstance(rotations, dict):
        return {}
    return {
        path: degrees % 360
        for path, degrees in rotations.items()
        if isinstance(path, str)
        and isinstance(degrees, int)
        and not isinstance(degrees, bool)
    }


def load_montage_canvas_rotation() -> int:
    data = _load_settings_data()
    rotation = data.get("montage_canvas_rotation", 0)
    if not isinstance(rotation, int) or isinstance(rotation, bool):
        return 0
    return rotation % 360


def load_visual_mode() -> str:
    data = _load_settings_data()
    mode = data.get("visual_mode", "quality")
    return (
        mode
        if isinstance(mode, str) and mode in {"quality", "performance"}
        else "quality"
    )


def save_user_settings(shortcuts: dict[str, str]) -> None:
    data = _load_settings_data()
    data["shortcuts"] = shortcuts
    _save_settings_data(data)


def save_montage_selection(selection: list[str]) -> None:
    data = _load_settings_data()
    data["montage_selection"] = selection
    _save_settings_data(data)


def save_montage_rotations(rotations: dict[str, int]) -> None:
    data = _load_settings_data()
    data["montage_rotations"] = rotations
    _save_settings_data(data)


def save_montage_canvas_rotation(rotation: int) -> None:
    data = _load_settings_data()
    data["montage_canvas_rotation"] = rotation % 360
    _save_settings_data(data)


def save_visual_mode(mode: str) -> None:
    if mode not in {"quality", "performance"}:
        raise ValueError(f"Modo de visualização inválido: {mode}")
    data = _load_settings_data()
    data["visual_mode"] = mode
    _save_settings_data(data)


def _load_settings_data() -> dict[str, object]:
    if not SETTINGS_PATH.is_file():
        return {}
    with SETTINGS_PATH.open("r", encoding="utf-8") as settings_file:
        data = json.load(settings_file)
    if not isinstance(data, dict):
        return {}
    return data


def _save_settings_data(data: dict[str, object]) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=SETTINGS_PATH.parent,
            suffix=".tmp",
            delete=False,
        ) as settings_file:
            temporary_path = Path(settings_file.name)
            json.dump(data, settings_file, ensure_ascii=False)
        os.replace(temporary_path, SETTINGS_PATH)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
