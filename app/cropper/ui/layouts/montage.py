from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..theme import COLORS


def build_montage_layout(app: object, parent: ttk.Frame) -> None:
    header = ttk.Frame(parent)
    header.pack(fill="x")
    ttk.Label(header, text="Montagem de imagem", style="Title.TLabel").pack(
        anchor="w"
    )
    ttk.Label(
        header,
        text="Visualize as fotos de out e atribua cada uma a uma posição.",
        style="Muted.TLabel",
    ).pack(anchor="w", pady=(2, 0))

    controls = ttk.Frame(parent)
    controls.pack(fill="x", pady=(10, 7))
    ttk.Button(
        controls,
        text="Atualizar imagens de out",
        command=app._refresh_montage_sources,
    ).pack(side="left")
    ttk.Button(
        controls,
        text="Montagem 4×3 · ajustar quadrados",
        command=app._start_grid_montage,
    ).pack(side="left", padx=(7, 0))
    app.montage_save_button = ttk.Button(
        controls,
        text="Salvar montagem",
        style="Primary.TButton",
        command=app._save_montage,
        state="disabled",
    )
    app.montage_save_button.pack(side="right")

    panels = ttk.Panedwindow(parent, orient="horizontal")
    panels.pack(fill="both", expand=True)
    browser = ttk.Frame(panels, style="Panel.TFrame", padding=13)
    result = ttk.Frame(panels, style="Panel.TFrame", padding=13)
    panels.add(browser, weight=5)
    panels.add(result, weight=7)

    ttk.Label(browser, text="Fotos da pasta out", style="Section.TLabel").pack(
        anchor="w", pady=(0, 6)
    )
    filters = ttk.Frame(browser, style="PanelInner.TFrame")
    filters.pack(fill="x", pady=(0, 8))
    app.montage_filter_var = tk.StringVar(value="Todos")
    app.montage_material_buttons = {}
    material_filters = ttk.Frame(browser, style="PanelInner.TFrame")
    material_filters.pack(fill="x", pady=(0, 8))
    for material in ("Todos", "Vidro", "MDF", "Cerâmica"):
        button = ttk.Button(
            material_filters,
            text=material,
            style=(
                "FilterActive.TButton"
                if app.montage_filter_var.get() == material
                else "Filter.TButton"
            ),
            command=lambda value=material: app._set_montage_material_filter(value),
        )
        button.pack(side="left", padx=(0, 4))
        app.montage_material_buttons[material] = button

    app.montage_search_var = tk.StringVar()
    search = ttk.Entry(filters, textvariable=app.montage_search_var)
    search.pack(side="left", fill="x", expand=True)
    app.montage_search_var.trace_add(
        "write", lambda *_args: app._filter_montage_gallery()
    )

    selection = ttk.Frame(browser, style="PanelInner.TFrame")
    selection.pack(fill="x", pady=(0, 10))
    source_preview = ttk.Frame(selection, style="PanelInner.TFrame")
    source_preview.pack(fill="x", pady=(0, 6))
    app.montage_source_canvas = tk.Canvas(
        source_preview,
        width=112,
        height=92,
        bg=COLORS["canvas"],
        highlightthickness=0,
    )
    app.montage_source_canvas.pack(side="left", fill="y")
    app.montage_source_canvas.bind("<Configure>", app._draw_montage_source)
    app.montage_rotate_button = ttk.Button(
        source_preview,
        text="↻",
        width=2,
        style="Rotate.TButton",
        command=app._rotate_montage_source,
        state="disabled",
    )
    app.montage_rotate_button.pack(side="left", padx=(4, 8))
    selection_controls = ttk.Frame(source_preview, style="PanelInner.TFrame")
    selection_controls.pack(side="left", fill="x", expand=True)
    app.montage_source_info_var = tk.StringVar(
        value="Selecione uma foto, escolha A–F e clique em Usar foto. ↻ gira a foto."
    )
    ttk.Label(
        selection_controls,
        textvariable=app.montage_source_info_var,
        style="CardMuted.TLabel",
        wraplength=260,
    ).pack(anchor="w", fill="x", pady=(0, 4))

    target_row = ttk.Frame(selection_controls, style="PanelInner.TFrame")
    target_row.pack(fill="x")
    ttk.Label(
        target_row, text="Posição", style="Section.TLabel"
    ).pack(side="left", padx=(0, 3))
    app.montage_target_buttons = []
    for index in range(6):
        button = ttk.Button(
            target_row,
            text=chr(ord("A") + index),
            width=2,
            command=lambda selected=index: app._set_montage_target(selected),
        )
        button.pack(side="left", padx=1)
        app.montage_target_buttons.append(button)
    app.montage_target_buttons[0].configure(style="MontageTargetActive.TButton")
    app.montage_assign_button = ttk.Button(
        target_row,
        text="Usar foto",
        command=app._assign_selected_montage_source,
        state="disabled",
    )
    app.montage_assign_button.pack(side="left", padx=(5, 0))

    gallery_frame = ttk.Frame(browser, style="PanelInner.TFrame")
    gallery_frame.pack(fill="both", expand=True)
    app.montage_gallery = ttk.Treeview(
        gallery_frame,
        columns=("path",),
        show="tree headings",
        style="Gallery.Treeview",
        selectmode="browse",
    )
    app.montage_gallery.heading("#0", text="Prévia")
    app.montage_gallery.column(
        "#0",
        width=98,
        minwidth=98,
        stretch=False,
        anchor="center",
    )
    app.montage_gallery.heading("path", text="Arquivo")
    app.montage_gallery.column(
        "path",
        width=260,
        minwidth=150,
        stretch=True,
        anchor="w",
    )
    gallery_scroll = ttk.Scrollbar(
        gallery_frame, orient="vertical", command=app.montage_gallery.yview
    )
    app.montage_gallery.configure(yscrollcommand=gallery_scroll.set)
    app.montage_gallery.pack(side="left", fill="both", expand=True)
    gallery_scroll.pack(side="right", fill="y")
    app.montage_gallery.bind("<<TreeviewSelect>>", app._select_montage_source)

    result_header = ttk.Frame(result, style="PanelInner.TFrame")
    result_header.pack(fill="x", pady=(0, 6))
    ttk.Label(
        result_header, text="Prévia da montagem", style="Section.TLabel"
    ).pack(side="left")
    app.montage_canvas_rotate_button = ttk.Button(
        result_header,
        text="↻",
        width=2,
        style="Rotate.TButton",
        command=app._rotate_whole_montage,
        state="disabled",
    )
    app.montage_canvas_rotate_button.pack(side="right")
    app.montage_canvas = tk.Canvas(
        result,
        bg=COLORS["canvas"],
        highlightthickness=0,
    )
    app.montage_canvas.pack(fill="both", expand=True)
    app.montage_canvas.bind("<Configure>", app._draw_montage_preview)
    ttk.Label(
        result,
        textvariable=app.montage_status_var,
        style="CardMuted.TLabel",
        wraplength=700,
    ).pack(anchor="w", fill="x", pady=(6, 0))
