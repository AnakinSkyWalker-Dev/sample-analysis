from __future__ import annotations

from pathlib import Path
import threading
from tkinter import messagebox
import tkinter as tk

import cv2
from PIL import Image, ImageDraw, ImageOps, ImageTk

from ..services.label_enlarger import (
    LabelSquare,
    count_pending_label_squares,
    detect_letter_squares,
    iter_result_images,
    overwrite_with_enlarged_squares,
)
from .image_rendering import fit_preview


class LabelReplacementMixin:
    def _refresh_label_images(self) -> None:
        if self.label_scan_busy:
            return
        root = Path(self.root_var.get()).expanduser() / "imgs_results"
        if not root.is_dir():
            messagebox.showerror(
                "Pasta imgs_results não encontrada",
                f"Não encontrei a pasta:\n{root}",
            )
            return
        self.label_scan_busy = True
        self.label_analyze_button.configure(state="disabled")
        self.label_apply_button.configure(state="disabled")
        self.label_status_var.set("Analisando as imagens de imgs_results…")
        self.label_summary_var.set("Analisando imagens…")
        self.label_image_tree.delete(*self.label_image_tree.get_children())
        threading.Thread(
            target=self._label_scan_worker,
            args=(root,),
            daemon=True,
        ).start()

    def _label_scan_worker(self, root: Path) -> None:
        try:
            paths = iter_result_images(root)
            results: list[
                tuple[Path, list[LabelSquare], int, str | None]
            ] = []
            for path in paths:
                try:
                    with Image.open(path) as source:
                        image = ImageOps.exif_transpose(source).convert("RGB")
                    squares = detect_letter_squares(image)
                    change_count = count_pending_label_squares(squares)
                    results.append((path, squares, change_count, None))
                except (OSError, ValueError, cv2.error) as error:
                    results.append((path, [], 0, str(error)))
        except OSError as error:
            self.window.after(0, self._fail_label_scan, error)
            return
        self.window.after(0, self._finish_label_scan, root, results)

    def _fail_label_scan(self, error: OSError) -> None:
        self.label_scan_busy = False
        self.label_analyze_button.configure(state="normal")
        self.label_summary_var.set("Falha ao analisar imgs_results.")
        self.label_status_var.set(str(error))
        messagebox.showerror("Falha ao analisar imagens", str(error))

    def _finish_label_scan(
        self,
        root: Path,
        results: list[
            tuple[Path, list[LabelSquare], int, str | None]
        ],
    ) -> None:
        self.label_scan_busy = False
        self.label_analyze_button.configure(state="normal")
        self.label_scan_root = root
        self.label_image_paths.clear()
        self.label_squares.clear()
        self.label_change_counts.clear()
        self.label_errors.clear()
        self.label_image_tree.delete(*self.label_image_tree.get_children())

        pending_files = 0
        pending_squares = 0
        detected_squares = 0
        errors = 0
        for index, (path, squares, change_count, error) in enumerate(results):
            item_id = str(index)
            self.label_image_paths[item_id] = path
            self.label_squares[path] = squares
            self.label_change_counts[path] = change_count
            if error is not None:
                errors += 1
                self.label_errors[path] = error
                count_text = "—"
                status = "erro"
            else:
                detected_squares += len(squares)
                pending_squares += change_count
                if change_count:
                    pending_files += 1
                    status = "ampliar"
                elif squares:
                    status = "já ampliadas"
                else:
                    status = "sem etiquetas"
                count_text = str(len(squares))
            self.label_image_tree.insert(
                "",
                "end",
                iid=item_id,
                text=str(path.relative_to(root)),
                values=(count_text, status),
            )

        self.label_summary_var.set(
            f"{len(results)} imagens · {detected_squares} etiquetas · "
            f"{pending_files} arquivos para ampliar"
        )
        self.label_status_var.set(
            f"{pending_squares} etiqueta(s) serão ampliadas. "
            f"{errors} arquivo(s) com erro não serão alterados."
        )
        self.label_apply_button.configure(
            state="normal" if pending_files else "disabled"
        )
        if results:
            self.label_image_tree.selection_set("0")
            self.label_image_tree.focus("0")
            self._select_label_image()
        else:
            self.label_preview_canvas.delete("all")
            self.label_preview_image = None

    def _select_label_image(self, _event: tk.Event | None = None) -> None:
        selection = self.label_image_tree.selection()
        if not selection:
            self.label_preview_image = None
            self.label_preview_squares = []
            self._draw_label_preview()
            return
        path = self.label_image_paths.get(selection[0])
        if path is None:
            return
        try:
            with Image.open(path) as source:
                self.label_preview_image = ImageOps.exif_transpose(source).convert(
                    "RGB"
                )
        except (OSError, ValueError) as error:
            self.label_preview_image = None
            self.label_preview_squares = []
            self.label_status_var.set(
                f"Não foi possível abrir {path.name}: {error}"
            )
            self._draw_label_preview()
            return
        self.label_preview_squares = self.label_squares.get(path, [])
        if path in self.label_errors:
            self.label_status_var.set(
                f"{path.name}: {self.label_errors[path]}"
            )
        else:
            count = self.label_change_counts.get(path, 0)
            status = (
                f"{count} etiqueta(s) aguardando ampliação."
                if count
                else "Nenhuma etiqueta precisa ser ampliada."
            )
            self.label_status_var.set(f"{path.name} · {status}")
        self._draw_label_preview()

    def _draw_label_preview(self, _event: tk.Event | None = None) -> None:
        canvas = self.label_preview_canvas
        canvas.delete("all")
        image = self.label_preview_image
        if image is None:
            return
        preview = image.copy()
        draw = ImageDraw.Draw(preview)
        for square in self.label_preview_squares:
            draw.rectangle(
                (
                    square.x,
                    square.y,
                    square.x + square.size - 1,
                    square.y + square.size - 1,
                ),
                outline="#08a5ad",
                width=max(2, round(min(image.size) / 700)),
            )
        fitted = fit_preview(
            preview,
            (max(1, canvas.winfo_width() - 16), max(1, canvas.winfo_height() - 16)),
            self.visual_mode,
        )
        self.label_preview_photo = ImageTk.PhotoImage(fitted)
        canvas.create_image(
            canvas.winfo_width() / 2,
            canvas.winfo_height() / 2,
            image=self.label_preview_photo,
            anchor="center",
        )

    def _apply_label_enlargement(self) -> None:
        if self.label_processing_busy:
            return
        current_root = Path(self.root_var.get()).expanduser() / "imgs_results"
        if self.label_scan_root != current_root:
            messagebox.showwarning(
                "Analise novamente",
                "A pasta selecionada mudou. Analise imgs_results antes de "
                "substituir os arquivos.",
            )
            return
        pending = [
            path
            for path, count in self.label_change_counts.items()
            if count > 0
        ]
        if not pending or self.label_scan_root is None:
            return
        square_count = sum(self.label_change_counts[path] for path in pending)
        if not messagebox.askyesno(
            "Substituir imagens originais?",
            f"{square_count} quadrado(s) em {len(pending)} arquivo(s) serão "
            "ampliados e os arquivos originais em imgs_results serão "
            "substituídos.\n\nDeseja continuar?",
            icon="warning",
        ):
            return
        self.label_processing_busy = True
        self.label_apply_button.configure(state="disabled")
        self.label_analyze_button.configure(state="disabled")
        self.label_status_var.set("Ampliando etiquetas e atualizando arquivos…")
        threading.Thread(
            target=self._label_apply_worker,
            args=(pending,),
            daemon=True,
        ).start()

    def _label_apply_worker(self, paths: list[Path]) -> None:
        results: list[tuple[Path, int, str | None]] = []
        for path in paths:
            try:
                count = overwrite_with_enlarged_squares(path)
                results.append((path, count, None))
            except (OSError, ValueError, cv2.error) as error:
                results.append((path, 0, str(error)))
        self.window.after(0, self._finish_label_apply, results)

    def _finish_label_apply(
        self,
        results: list[tuple[Path, int, str | None]],
    ) -> None:
        self.label_processing_busy = False
        self.label_analyze_button.configure(state="normal")
        failures = [(path, error) for path, _, error in results if error]
        changed_squares = sum(count for _, count, error in results if error is None)
        self.label_status_var.set(
            f"{changed_squares} etiqueta(s) ampliada(s) em "
            f"{sum(count > 0 for _, count, _ in results)} arquivo(s). "
            f"{len(failures)} erro(s)."
        )
        if failures:
            self.label_status_var.set(
                f"{self.label_status_var.get()} Primeiro erro: "
                f"{failures[0][0].name}: {failures[0][1]}"
            )
            messagebox.showwarning(
                "Processamento parcial",
                self.label_status_var.get(),
            )
        self._refresh_label_images()
