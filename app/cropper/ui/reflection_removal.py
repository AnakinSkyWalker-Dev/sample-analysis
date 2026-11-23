from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

import cv2
import numpy as np
from PIL import Image, ImageTk

from ..images.files import IMAGE_EXTENSIONS, load_rgb
from ..services.reflection_removal import remove_reflections, replace_with_backup, restore_original
from .image_rendering import fit_preview


class ReflectionRemovalMixin:
    def _choose_reflection_image(self) -> None:
        selected = filedialog.askopenfilename(
            title="Escolher imagem de vidro",
            initialdir=self.root_var.get(),
            filetypes=[("Imagens", " ".join(f"*{suffix}" for suffix in IMAGE_EXTENSIONS)), ("Todos os arquivos", "*.*")],
        )
        if not selected:
            return
        try:
            self.reflection_path = Path(selected)
            self.reflection_original = load_rgb(self.reflection_path)
            self.reflection_mask = np.zeros(self.reflection_original.shape[:2], dtype=np.uint8)
            self.reflection_strokes = []
            self._process_reflection_preview()
            self.reflection_status_var.set(
                f"{self.reflection_path.name}: pinte somente sobre mãos, objetos ou luzes refletidos."
            )
        except (OSError, ValueError) as error:
            messagebox.showerror("Falha ao abrir imagem", str(error))

    def _process_reflection_preview(self, _value: str | None = None) -> None:
        if self.reflection_original is None:
            return
        try:
            self.reflection_processed, self.reflection_mask = remove_reflections(
                self.reflection_original,
                60,
                self.reflection_mask,
            )
            self._draw_reflection_previews()
        except (OSError, ValueError) as error:
            self.reflection_status_var.set(f"Falha ao processar: {error}")

    def _draw_reflection_previews(self, _event: tk.Event | None = None) -> None:
        if self.reflection_original is None:
            return
        self.window.update_idletasks()
        marked = self.reflection_original.copy()
        if self.reflection_mask is not None and np.any(self.reflection_mask):
            marked[self.reflection_mask > 0] = (
                marked[self.reflection_mask > 0] * 0.45
                + np.array([235, 80, 70]) * 0.55
            ).astype(np.uint8)
        images = (
            Image.fromarray(marked),
            Image.fromarray(
                self.reflection_processed
                if self.reflection_processed is not None
                else self.reflection_original
            ),
        )
        for index, (canvas, image) in enumerate(zip(self.reflection_canvases, images)):
            canvas.delete("all")
            preview = fit_preview(image, (max(1, canvas.winfo_width() - 16), max(1, canvas.winfo_height() - 16)), self.visual_mode)
            photo = ImageTk.PhotoImage(preview)
            self.reflection_photos[index] = photo
            canvas.create_image(canvas.winfo_width() / 2, canvas.winfo_height() / 2, image=photo, anchor="center")

    def _paint_reflection(self, event: tk.Event) -> None:
        if self.reflection_original is None:
            return
        canvas = self.reflection_canvases[0]
        width = max(1, canvas.winfo_width() - 16)
        height = max(1, canvas.winfo_height() - 16)
        image_height, image_width = self.reflection_original.shape[:2]
        scale = min(width / image_width, height / image_height)
        preview_width = image_width * scale
        preview_height = image_height * scale
        offset_x = (canvas.winfo_width() - preview_width) / 2
        offset_y = (canvas.winfo_height() - preview_height) / 2
        x = int((event.x - offset_x) / max(scale, 1e-6))
        y = int((event.y - offset_y) / max(scale, 1e-6))
        if not (0 <= x < image_width and 0 <= y < image_height):
            return
        radius = max(3, int(8 / max(scale, 0.05)))
        cv2.circle(self.reflection_mask, (x, y), radius, 255, -1)
        self.reflection_strokes.append((x, y))
        self._process_reflection_preview()

    def _clear_reflection_marks(self) -> None:
        if self.reflection_original is None:
            return
        self.reflection_mask = np.zeros(self.reflection_original.shape[:2], dtype=np.uint8)
        self.reflection_strokes = []
        self._process_reflection_preview()
        self.reflection_status_var.set("Marcações limpas. Pinte somente os reflexos.")

    def _replace_reflection_image(self) -> None:
        if self.reflection_path is None or self.reflection_processed is None:
            messagebox.showwarning("Nenhuma prévia", "Escolha uma imagem primeiro.")
            return
        if not messagebox.askyesno(
            "Substituir imagem original?",
            "A imagem será substituída. Uma cópia original será mantida ao lado do arquivo. Continuar?",
        ):
            return
        try:
            backup = replace_with_backup(self.reflection_path, self.reflection_processed)
            self.reflection_original = load_rgb(self.reflection_path)
            self.reflection_status_var.set(f"Substituída. Backup preservado em: {backup.name}")
            self._draw_reflection_previews()
        except (OSError, ValueError) as error:
            messagebox.showerror("Falha ao substituir imagem", str(error))

    def _restore_reflection_original(self) -> None:
        if self.reflection_path is None:
            return
        try:
            restore_original(self.reflection_path)
            self.reflection_original = load_rgb(self.reflection_path)
            self._process_reflection_preview()
            self.reflection_status_var.set("Imagem original restaurada.")
        except (OSError, ValueError) as error:
            messagebox.showerror("Falha ao restaurar original", str(error))


def build_reflection_removal_layout(app: object, parent: ttk.Frame) -> None:
    header = ttk.Frame(parent)
    header.pack(fill="x")
    ttk.Label(header, text="Remover reflexos de vidro", style="Title.TLabel").pack(anchor="w")
    ttk.Label(header, text="Gere uma prévia e substitua a imagem somente após confirmar.", style="Muted.TLabel").pack(anchor="w", pady=(2, 0))

    controls = ttk.Frame(parent)
    controls.pack(fill="x", pady=(10, 8))
    ttk.Button(controls, text="Escolher imagem", command=app._choose_reflection_image).pack(side="left")
    ttk.Button(controls, text="Limpar marcações", command=app._clear_reflection_marks).pack(side="left", padx=(8, 0))
    ttk.Button(controls, text="Restaurar original", command=app._restore_reflection_original).pack(side="right", padx=(0, 8))
    ttk.Button(controls, text="Substituir imagem", style="Primary.TButton", command=app._replace_reflection_image).pack(side="right")

    panels = ttk.Panedwindow(parent, orient="horizontal")
    panels.pack(fill="both", expand=True)
    canvases = []
    for title in ("Original", "Prévia sem reflexo"):
        panel = ttk.Frame(panels, style="Panel.TFrame", padding=8)
        panels.add(panel, weight=1)
        ttk.Label(panel, text=title, style="Section.TLabel").pack(anchor="w", pady=(0, 6))
        canvas = tk.Canvas(panel, bg="#202833", highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        canvas.bind("<Configure>", app._draw_reflection_previews)
        if title == "Original":
            canvas.bind("<B1-Motion>", app._paint_reflection)
            canvas.bind("<Button-1>", app._paint_reflection)
        canvases.append(canvas)
    app.reflection_canvases = canvases
    app.reflection_photos = [None, None]
    app.reflection_status_var = tk.StringVar(value="Escolha uma imagem e pinte os reflexos em vermelho na imagem original.")
    ttk.Label(parent, textvariable=app.reflection_status_var, style="CardMuted.TLabel", wraplength=900).pack(fill="x", pady=(7, 0))
