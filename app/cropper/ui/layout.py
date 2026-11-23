from __future__ import annotations

from tkinter import ttk

from .layouts import (
    build_crop_layout,
    build_help_layout,
    build_label_replacement_layout,
    build_montage_layout,
    build_reflection_removal_layout,
    build_shortcuts_layout,
)
from .theme import COLORS


class LayoutMixin:
    def _build_layout(self) -> None:
        container = ttk.Frame(self.window, padding=20)
        container.pack(fill="both", expand=True)

        header = ttk.Frame(container, style="Header.TFrame", padding=(20, 15))
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(header, text="TCC", style="Brand.TLabel").pack(
            side="left", padx=(0, 14)
        )
        title_group = ttk.Frame(header, style="Header.TFrame")
        title_group.pack(side="left", fill="x", expand=True)
        ttk.Label(
            title_group,
            text="Análise de amostras",
            style="HeaderTitle.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            title_group,
            text="Laboratório visual  ·  Corte, revisão e montagem de imagens",
            style="HeaderSubtitle.TLabel",
        ).pack(anchor="w", pady=(1, 0))
        visual_group = ttk.Frame(header, style="Header.TFrame")
        visual_group.pack(side="right", padx=(16, 0))
        ttk.Label(
            visual_group,
            text="PRÉVIA",
            style="HeaderSubtitle.TLabel",
        ).pack(anchor="w", pady=(0, 3))
        self.visual_mode_combo = ttk.Combobox(
            visual_group,
            textvariable=self.visual_mode_var,
            values=("Qualidade", "Desempenho"),
            state="readonly",
            width=14,
            style="Header.TCombobox",
        )
        self.visual_mode_combo.pack(anchor="e")
        self.visual_mode_combo.bind(
            "<<ComboboxSelected>>", self._set_visual_mode
        )
        ttk.Button(
            header,
            text="Organizar nomes",
            style="HeaderAction.TButton",
            command=self._open_result_organizer,
        ).pack(side="right", padx=(0, 14))

        pages = ttk.Notebook(container)
        pages.pack(fill="both", expand=True)
        crop_page = ttk.Frame(pages, padding=(16, 14, 16, 16))
        montage_page = ttk.Frame(pages, padding=(16, 14, 16, 16))
        reflection_page = ttk.Frame(pages, padding=(16, 14, 16, 16))
        labels_page = ttk.Frame(pages, padding=(16, 14, 16, 16))
        shortcuts_page = ttk.Frame(pages, padding=(16, 14, 16, 16))
        help_page = ttk.Frame(pages, padding=(16, 14, 16, 16))
        pages.add(crop_page, text="  Corte de amostras  ")
        pages.add(montage_page, text="  Montagem de imagem  ")
        pages.add(reflection_page, text="  Remover reflexos  ")
        pages.add(labels_page, text="  Etiquetas A–F  ")
        pages.add(shortcuts_page, text="  Atalhos  ")
        pages.add(help_page, text="  Ajuda  ")
        build_crop_layout(self, crop_page)
        build_montage_layout(self, montage_page)
        build_reflection_removal_layout(self, reflection_page)
        build_label_replacement_layout(self, labels_page)
        build_shortcuts_layout(self, shortcuts_page)
        build_help_layout(self, help_page)

        self.window.configure(fg_color=COLORS["background"])
