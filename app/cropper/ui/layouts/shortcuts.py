from __future__ import annotations

from tkinter import ttk

from ..shortcuts import SHORTCUT_LABELS


def build_shortcuts_layout(app: object, parent: ttk.Frame) -> None:
    header = ttk.Frame(parent)
    header.pack(fill="x", pady=(0, 10))
    ttk.Label(header, text="Atalhos do teclado", style="Title.TLabel").pack(
        anchor="w"
    )
    ttk.Label(
        header,
        text="Clique em “Alterar” e pressione a combinação desejada.",
        style="Muted.TLabel",
    ).pack(anchor="w", pady=(2, 0))

    panel = ttk.Frame(parent, style="Panel.TFrame", padding=18)
    panel.pack(fill="x")
    for row, (action, label) in enumerate(SHORTCUT_LABELS.items()):
        ttk.Label(panel, text=label, style="Section.TLabel").grid(
            row=row, column=0, sticky="w", padx=(0, 24), pady=9
        )
        variable = app.shortcut_vars[action]
        ttk.Label(
            panel,
            textvariable=variable,
            style="CardMuted.TLabel",
            width=18,
        ).grid(row=row, column=1, sticky="w", pady=9)
        ttk.Button(
            panel,
            text="Alterar",
            command=lambda selected=action: app._begin_shortcut_capture(selected),
        ).grid(row=row, column=2, sticky="e", pady=5)
    panel.columnconfigure(0, weight=1)

    footer = ttk.Frame(parent)
    footer.pack(fill="x", pady=(10, 0))
    ttk.Button(
        footer,
        text="Restaurar padrões",
        command=app._reset_shortcuts,
    ).pack(side="right")
    ttk.Label(
        parent,
        textvariable=app.shortcut_status_var,
        style="Muted.TLabel",
        wraplength=900,
    ).pack(anchor="w", pady=(8, 0))
    ttk.Label(
        parent,
        text=(
            "Zoom na foto original: Ctrl + roda do mouse, ou os botões + / −. "
            "Ajustar retorna à visualização completa."
        ),
        style="Muted.TLabel",
        wraplength=900,
    ).pack(anchor="w", pady=(6, 0))
