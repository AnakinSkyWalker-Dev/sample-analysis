from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..theme import COLORS


def build_crop_layout(app: object, parent: ttk.Frame) -> None:
    header = ttk.Frame(parent)
    header.pack(fill="x", pady=(0, 12))
    ttk.Label(header, text="Corte de amostras", style="Title.TLabel").pack(
        anchor="w"
    )
    ttk.Label(
        header,
        text="Detecte, revise e exporte recortes quadrados para out.",
        style="Muted.TLabel",
    ).pack(anchor="w", pady=(2, 0))

    path_row = ttk.Frame(parent)
    path_row.pack(fill="x", pady=(0, 9))
    ttk.Entry(path_row, textvariable=app.root_var).pack(
        side="left", fill="x", expand=True
    )
    ttk.Button(path_row, text="Pasta…", command=app._choose_folder).pack(
        side="left", padx=(6, 0)
    )
    app.scan_button = ttk.Button(
        path_row,
        text="Analisar fotos",
        style="Primary.TButton",
        command=app._start_scan,
    )
    app.scan_button.pack(side="left", padx=(6, 0))
    app.preserve_ready_var = tk.BooleanVar(value=True)
    app.preserve_ready_checkbutton = ttk.Checkbutton(
        path_row,
        text="Preservar fotos prontas",
        variable=app.preserve_ready_var,
        style="Modern.TCheckbutton",
    )
    app.preserve_ready_checkbutton.pack(side="left", padx=(10, 0))

    stats = ttk.Frame(parent, style="Panel.TFrame", padding=(12, 8))
    stats.pack(fill="x", pady=(0, 12))
    ttk.Label(
        stats,
        textvariable=app.count_var,
        style="Section.TLabel",
    ).pack(side="left")
    app.progress = ttk.Progressbar(stats, mode="indeterminate", length=150)
    app.progress.pack(side="right")

    footer = ttk.Frame(parent)
    footer.pack(side="bottom", fill="x", pady=(9, 0))
    ttk.Label(
        footer,
        textvariable=app.status_var,
        style="Muted.TLabel",
        wraplength=460,
    ).pack(side="left", fill="x", expand=True)
    app.open_button = ttk.Button(
        footer, text="Abrir out", command=app._open_output, state="disabled"
    )
    app.open_button.pack(side="right", padx=(6, 0))
    app.manual_button = ttk.Button(
        footer,
        text="Marcar quadrados",
        command=app._start_manual_crop,
        state="disabled",
    )
    app.manual_button.pack(side="right", padx=(6, 0))
    app.manual_add_button = ttk.Button(
        footer,
        text="Adicionar quadrado",
        command=app._add_manual_square,
        state="disabled",
    )
    app.manual_add_button.pack(side="right", padx=(6, 0))
    app.grid_utility_button = ttk.Button(
        footer,
        text="Ajustar quadrados / girar original",
        command=app._open_selected_grid_editor,
        state="disabled",
    )
    app.grid_utility_button.pack(side="right", padx=(6, 0))
    app.process_button = ttk.Button(
        footer,
        text="Cortar fotos identificadas",
        style="Primary.TButton",
        command=app._process_results,
        state="disabled",
    )
    app.process_button.pack(side="right")

    body = ttk.Panedwindow(parent, orient="horizontal")
    body.pack(fill="both", expand=True)
    list_panel = ttk.Frame(body, style="Panel.TFrame", padding=12)
    preview_panel = ttk.Frame(body, style="Panel.TFrame", padding=12)
    body.add(list_panel, weight=1)
    body.add(preview_panel, weight=3)

    filters = ttk.Frame(list_panel, style="PanelInner.TFrame")
    filters.pack(fill="x", pady=(0, 9))
    app.material_buttons = {}
    for material in ("Todos", "Vidro", "MDF", "Cerâmica"):
        button = ttk.Button(
            filters,
            text=material,
            style=(
                "FilterActive.TButton"
                if app.material_filter.get() == material
                else "Filter.TButton"
            ),
            command=lambda value=material: app._set_material_filter(value),
        )
        button.pack(side="left", padx=(0, 4))
        app.material_buttons[material] = button

    app.tree = ttk.Treeview(
        list_panel,
        columns=("squares", "status"),
        show="tree headings",
        selectmode="browse",
    )
    app.tree.heading("#0", text="Foto")
    app.tree.heading("squares", text="Qtd.")
    app.tree.heading("status", text="Estado")
    app.tree.column("#0", width=250, minwidth=135, stretch=True)
    app.tree.column("squares", width=45, minwidth=42, stretch=False, anchor="center")
    app.tree.column("status", width=94, minwidth=78, stretch=False)
    scrollbar = ttk.Scrollbar(list_panel, orient="vertical", command=app.tree.yview)
    app.tree.configure(yscrollcommand=scrollbar.set)
    app.tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    app.tree.bind("<<TreeviewSelect>>", app._show_selection)

    preview_header = ttk.Frame(preview_panel, style="PanelInner.TFrame")
    preview_header.pack(fill="x", pady=(0, 7))
    app.selected_var = tk.StringVar(value="Selecione uma foto")
    ttk.Label(
        preview_header,
        textvariable=app.selected_var,
        style="Section.TLabel",
    ).pack(side="left")
    previews = ttk.Frame(preview_panel, style="PanelInner.TFrame")
    previews.pack(fill="both", expand=True)
    source_frame = ttk.Frame(previews, style="PanelInner.TFrame")
    crop_frame = ttk.Frame(previews, style="PanelInner.TFrame")
    source_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
    crop_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))
    source_toolbar = ttk.Frame(source_frame, style="PanelInner.TFrame")
    source_toolbar.pack(fill="x", pady=(0, 4))
    ttk.Label(
        source_toolbar,
        text="ORIGINAL / DETECÇÃO",
        style="CardMuted.TLabel",
        background=COLORS["surface"],
    ).pack(side="left")
    app.zoom_label_var = tk.StringVar(value="100%")
    ttk.Button(
        source_toolbar,
        text="−",
        width=2,
        command=app._zoom_out,
    ).pack(side="right")
    ttk.Label(
        source_toolbar,
        textvariable=app.zoom_label_var,
        background=COLORS["surface"],
        font=("Segoe UI", 8),
        width=5,
        anchor="center",
    ).pack(side="right", padx=3)
    ttk.Button(
        source_toolbar,
        text="+",
        width=2,
        command=app._zoom_in,
    ).pack(side="right")
    ttk.Button(
        source_toolbar,
        text="Ajustar",
        command=app._reset_zoom,
    ).pack(side="right", padx=(0, 5))
    crop_toolbar = ttk.Frame(crop_frame, style="PanelInner.TFrame")
    crop_toolbar.pack(fill="x", pady=(0, 4))
    ttk.Label(
        crop_toolbar,
        text="RECORTE RETIFICADO",
        style="CardMuted.TLabel",
        background=COLORS["surface"],
    ).pack(side="left")
    app.crop_index_var = tk.StringVar(value="")
    ttk.Label(
        crop_toolbar,
        textvariable=app.crop_index_var,
        background=COLORS["surface"],
        font=("Segoe UI", 8),
    ).pack(side="right", padx=4)
    app.crop_next_button = ttk.Button(
        crop_toolbar,
        text=">",
        width=2,
        command=app._next_crop,
        state="disabled",
    )
    app.crop_next_button.pack(side="right")
    app.crop_previous_button = ttk.Button(
        crop_toolbar,
        text="<",
        width=2,
        command=app._previous_crop,
        state="disabled",
    )
    app.crop_previous_button.pack(side="right")
    source_view = ttk.Frame(source_frame, style="PanelInner.TFrame")
    source_view.pack(fill="both", expand=True)
    app.source_canvas = tk.Canvas(source_view, bg=COLORS["canvas"], highlightthickness=0)
    source_vertical = ttk.Scrollbar(
        source_view, orient="vertical", command=app.source_canvas.yview
    )
    source_horizontal = ttk.Scrollbar(
        source_view, orient="horizontal", command=app.source_canvas.xview
    )
    app.source_canvas.configure(
        xscrollcommand=source_horizontal.set,
        yscrollcommand=source_vertical.set,
    )
    app.source_canvas.grid(row=0, column=0, sticky="nsew")
    source_vertical.grid(row=0, column=1, sticky="ns")
    source_horizontal.grid(row=1, column=0, sticky="ew")
    source_view.rowconfigure(0, weight=1)
    source_view.columnconfigure(0, weight=1)
    app.crop_canvas = tk.Canvas(
        crop_frame, bg=COLORS["canvas"], highlightthickness=0
    )
    app.crop_canvas.pack(fill="both", expand=True)
    app.source_canvas.bind("<Configure>", app._redraw_preview)
    app.source_canvas.bind("<Button-1>", app._manual_corner)
    app.source_canvas.bind("<B1-Motion>", app._drag_preview_adjustment)
    app.source_canvas.bind("<ButtonRelease-1>", app._finish_preview_adjustment)
    app.source_canvas.bind("<Control-MouseWheel>", app._zoom_mousewheel)
    app.source_canvas.bind("<Control-Button-4>", app._zoom_mousewheel)
    app.source_canvas.bind("<Control-Button-5>", app._zoom_mousewheel)
    app.crop_canvas.bind("<Configure>", app._redraw_preview)
