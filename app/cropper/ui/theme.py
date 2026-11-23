from __future__ import annotations

import tkinter as tk
from tkinter import ttk


COLORS = {
    "background": "#f4f6fa",
    "surface": "#ffffff",
    "ink": "#172033",
    "muted": "#68758a",
    "navy": "#17243a",
    "navy_soft": "#263750",
    "accent": "#087f8c",
    "accent_hover": "#066b77",
    "accent_soft": "#e3f3f4",
    "line": "#e2e8f0",
    "canvas": "#eef2f6",
}


def configure_styles(window: tk.Tk) -> None:
    style = ttk.Style(window)
    style.theme_use("clam")
    style.configure("TFrame", background=COLORS["background"])
    style.configure(
        "Panel.TFrame",
        background=COLORS["surface"],
        borderwidth=1,
        relief="solid",
        bordercolor=COLORS["line"],
    )
    style.configure("PanelInner.TFrame", background=COLORS["surface"])
    style.configure(
        "Header.TFrame",
        background=COLORS["navy"],
        borderwidth=1,
        relief="solid",
        bordercolor=COLORS["navy"],
    )
    style.configure(
        "TLabel",
        background=COLORS["background"],
        foreground=COLORS["ink"],
        font=("Segoe UI", 9),
    )
    style.configure(
        "Muted.TLabel",
        background=COLORS["background"],
        foreground=COLORS["muted"],
        font=("Segoe UI", 8),
    )
    style.configure(
        "CardMuted.TLabel",
        background=COLORS["surface"],
        foreground=COLORS["muted"],
        font=("Segoe UI", 8),
    )
    style.configure(
        "HeaderTitle.TLabel",
        background=COLORS["navy"],
        foreground="#ffffff",
        font=("Segoe UI Semibold", 17),
    )
    style.configure(
        "HeaderSubtitle.TLabel",
        background=COLORS["navy"],
        foreground="#c5d1e2",
        font=("Segoe UI", 9),
    )
    style.configure(
        "Brand.TLabel",
        background=COLORS["navy_soft"],
        foreground="#ffffff",
        font=("Segoe UI Semibold", 9),
        padding=(10, 7),
    )
    style.configure(
        "Title.TLabel",
        background=COLORS["background"],
        foreground=COLORS["ink"],
        font=("Segoe UI Semibold", 16),
    )
    style.configure(
        "Section.TLabel",
        background=COLORS["surface"],
        foreground=COLORS["ink"],
        font=("Segoe UI Semibold", 9),
    )
    style.configure(
        "TButton",
        font=("Segoe UI Semibold", 9),
        padding=(11, 7),
        background="#ffffff",
        foreground=COLORS["ink"],
        bordercolor=COLORS["line"],
        lightcolor=COLORS["line"],
        darkcolor=COLORS["line"],
        focuscolor=COLORS["accent"],
        focusthickness=1,
    )
    style.map(
        "TButton",
        background=[
            ("disabled", "#f0f3f7"),
            ("pressed", "#e7edf3"),
            ("active", "#f5f8fb"),
        ],
        foreground=[
            ("disabled", "#98a3b3"),
            ("active", COLORS["ink"]),
        ],
    )
    style.configure(
        "TEntry",
        padding=(10, 8),
        fieldbackground=COLORS["surface"],
        bordercolor=COLORS["line"],
        lightcolor=COLORS["line"],
        darkcolor=COLORS["line"],
        foreground=COLORS["ink"],
        insertcolor=COLORS["accent"],
    )
    style.map(
        "TEntry",
        bordercolor=[("focus", COLORS["accent"])],
        lightcolor=[("focus", COLORS["accent"])],
        darkcolor=[("focus", COLORS["accent"])],
    )
    style.configure(
        "Header.TCombobox",
        padding=(9, 6),
        fieldbackground="#ffffff",
        background="#ffffff",
        foreground=COLORS["ink"],
        bordercolor="#d6e0ea",
        lightcolor="#d6e0ea",
        darkcolor="#d6e0ea",
        arrowcolor=COLORS["accent"],
    )
    style.map(
        "Header.TCombobox",
        fieldbackground=[("readonly", "#ffffff")],
        selectbackground=[("readonly", "#ffffff")],
        selectforeground=[("readonly", COLORS["ink"])],
    )
    style.configure(
        "HeaderAction.TButton",
        font=("Segoe UI Semibold", 8),
        padding=(10, 7),
        background=COLORS["navy_soft"],
        foreground="#ffffff",
        borderwidth=0,
    )
    style.map(
        "HeaderAction.TButton",
        background=[
            ("pressed", COLORS["accent_hover"]),
            ("active", COLORS["accent"]),
        ],
        foreground=[("disabled", "#aab7c8")],
    )
    style.configure(
        "Modern.TCheckbutton",
        background=COLORS["background"],
        foreground=COLORS["ink"],
        font=("Segoe UI", 9),
        padding=(3, 5),
        indicatorcolor=COLORS["surface"],
        indicatordiameter=15,
    )
    style.map(
        "Modern.TCheckbutton",
        background=[("active", COLORS["background"])],
        foreground=[("disabled", COLORS["muted"])],
        indicatorcolor=[
            ("selected", COLORS["accent"]),
            ("active", "#dce5ed"),
        ],
    )
    style.configure(
        "Filter.TButton",
        font=("Segoe UI", 8),
        padding=(10, 5),
        background="#e9eef5",
        foreground="#53657c",
        borderwidth=0,
    )
    style.map(
        "Filter.TButton",
        background=[("active", "#dce5ef")],
    )
    style.configure(
        "FilterActive.TButton",
        font=("Segoe UI Semibold", 8),
        padding=(10, 5),
        background=COLORS["accent"],
        foreground="#ffffff",
        borderwidth=0,
    )
    style.configure(
        "MontageTargetActive.TButton",
        font=("Segoe UI Semibold", 9),
        padding=(10, 6),
        background=COLORS["accent"],
        foreground="#ffffff",
        borderwidth=0,
    )
    style.map(
        "MontageTargetActive.TButton",
        background=[("active", COLORS["accent_hover"])],
    )
    style.configure(
        "Rotate.TButton",
        font=("Segoe UI Symbol", 17),
        padding=(5, 2),
        foreground=COLORS["accent"],
    )
    style.configure(
        "Primary.TButton",
        background=COLORS["accent"],
        foreground="#ffffff",
        padding=(14, 8),
        borderwidth=0,
    )
    style.map(
        "Primary.TButton",
        background=[
            ("disabled", "#b9d1d3"),
            ("pressed", COLORS["accent_hover"]),
            ("active", COLORS["accent_hover"]),
        ],
        foreground=[("disabled", "#f4f8f8")],
    )
    style.configure(
        "TNotebook",
        background=COLORS["background"],
        borderwidth=0,
        tabmargins=(0, 5, 0, 0),
    )
    style.configure(
        "TNotebook.Tab",
        background="#e9eef4",
        foreground="#647188",
        padding=(18, 11),
        width=20,
        font=("Segoe UI Semibold", 9),
        borderwidth=0,
    )
    style.map(
        "TNotebook.Tab",
        background=[
            ("selected", COLORS["surface"]),
            ("active", "#f8fafc"),
        ],
        foreground=[
            ("selected", COLORS["accent"]),
            ("active", COLORS["ink"]),
        ],
    )
    style.configure(
        "TPanedwindow",
        background=COLORS["background"],
        sashwidth=7,
        sashrelief="flat",
    )
    style.configure(
        "Treeview",
        background=COLORS["surface"],
        fieldbackground=COLORS["surface"],
        foreground=COLORS["ink"],
        rowheight=32,
        font=("Segoe UI", 9),
        borderwidth=0,
    )
    style.configure("Gallery.Treeview", rowheight=100)
    style.map(
        "Treeview",
        background=[("selected", COLORS["accent_soft"])],
        foreground=[("selected", COLORS["ink"])],
    )
    style.configure(
        "Treeview.Heading",
        background="#f5f7fa",
        foreground="#657287",
        font=("Segoe UI Semibold", 8),
        relief="flat",
        padding=(8, 9),
    )
    style.map("Treeview.Heading", background=[("active", "#edf2f7")])
    style.configure(
        "Vertical.TScrollbar",
        background="#e1e7ef",
        troughcolor=COLORS["surface"],
        bordercolor=COLORS["surface"],
        arrowcolor="#657287",
        width=11,
    )
    style.configure(
        "Horizontal.TProgressbar",
        background=COLORS["accent"],
        troughcolor="#e4eaf1",
        borderwidth=0,
    )
