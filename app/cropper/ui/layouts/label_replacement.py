from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..theme import COLORS


def build_label_replacement_layout(app: object, parent: ttk.Frame) -> None:
    header = ttk.Frame(parent)
    header.pack(fill="x", pady=(0, 10))
    ttk.Label(
        header,
        text="Ampliar etiquetas A–F",
        style="Title.TLabel",
    ).pack(anchor="w")
    ttk.Label(
        header,
        text="Detecte e aumente os quadrados com letras em imgs_results.",
        style="Muted.TLabel",
    ).pack(anchor="w", pady=(2, 0))

    controls = ttk.Frame(parent)
    controls.pack(fill="x", pady=(0, 9))
    app.label_analyze_button = ttk.Button(
        controls,
        text="Analisar imgs_results",
        command=app._refresh_label_images,
    )
    app.label_analyze_button.pack(side="left")
    app.label_apply_button = ttk.Button(
        controls,
        text="Ampliar etiquetas identificadas",
        style="Primary.TButton",
        command=app._apply_label_enlargement,
        state="disabled",
    )
    app.label_apply_button.pack(side="right")

    panels = ttk.Panedwindow(parent, orient="horizontal")
    panels.pack(fill="both", expand=True)
    files_panel = ttk.Frame(panels, style="Panel.TFrame", padding=12)
    preview_panel = ttk.Frame(panels, style="Panel.TFrame", padding=12)
    panels.add(files_panel, weight=5)
    panels.add(preview_panel, weight=7)

    ttk.Label(
        files_panel,
        textvariable=app.label_summary_var,
        style="Section.TLabel",
    ).pack(anchor="w", pady=(0, 7))
    table = ttk.Frame(files_panel, style="PanelInner.TFrame")
    table.pack(fill="both", expand=True)
    app.label_image_tree = ttk.Treeview(
        table,
        columns=("squares", "status"),
        show="tree headings",
        selectmode="browse",
    )
    app.label_image_tree.heading("#0", text="Imagem")
    app.label_image_tree.heading("squares", text="Etiquetas")
    app.label_image_tree.heading("status", text="Estado")
    app.label_image_tree.column("#0", width=220, minwidth=120, stretch=True)
    app.label_image_tree.column(
        "squares", width=70, minwidth=60, stretch=False, anchor="center"
    )
    app.label_image_tree.column("status", width=105, minwidth=90, stretch=False)
    scrollbar = ttk.Scrollbar(
        table,
        orient="vertical",
        command=app.label_image_tree.yview,
    )
    app.label_image_tree.configure(yscrollcommand=scrollbar.set)
    app.label_image_tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    app.label_image_tree.bind(
        "<<TreeviewSelect>>",
        app._select_label_image,
    )
    ttk.Label(
        files_panel,
        textvariable=app.label_status_var,
        style="CardMuted.TLabel",
        wraplength=430,
    ).pack(anchor="w", fill="x", pady=(7, 0))

    preview_header = ttk.Frame(preview_panel, style="PanelInner.TFrame")
    preview_header.pack(fill="x", pady=(0, 7))
    ttk.Label(
        preview_header,
        text="Prévia · quadrados detectados",
        style="Section.TLabel",
    ).pack(side="left")
    app.label_preview_canvas = tk.Canvas(
        preview_panel,
        bg=COLORS["canvas"],
        highlightthickness=0,
    )
    app.label_preview_canvas.pack(fill="both", expand=True)
    app.label_preview_canvas.bind(
        "<Configure>",
        app._draw_label_preview,
    )
    ttk.Label(
        preview_panel,
        text=(
            "A substituição só ocorre após confirmação. Imagens sem etiquetas "
            "detectadas ou com erro permanecem intactas."
        ),
        style="CardMuted.TLabel",
        wraplength=650,
    ).pack(anchor="w", fill="x", pady=(7, 0))
