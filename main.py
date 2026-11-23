from __future__ import annotations

from pathlib import Path
import sys

import customtkinter as ctk

PROJECT_DIR = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)
sys.pycache_prefix = str(PROJECT_DIR / ".cache" / "python")

# Configure the cache root before importing application modules.
from app.cropper.ui import CropApp


def main() -> None:
    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")
    window = ctk.CTk()
    CropApp(window)
    window.mainloop()


if __name__ == "__main__":
    main()
