from __future__ import annotations
import os
import threading
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter as tk
import numpy as np
from PIL import Image, ImageTk
from ..images import (
    DEFAULT_SOURCE_DIR,
    SKIP_DIRECTORIES,
    PhotoResult,
)
from ..images.files import IMAGE_EXTENSIONS
from ..services.exporter import crop_destinations, export_crops
from ..services.label_enlarger import LabelSquare
from ..services.scan_cache import (
    get_cached_scan_root,
    load_manual_scan_overrides,
    load_preserved_scan_results,
    load_scan_cache,
    save_scan_cache,
)
from ..services.scanner import scan_images
from ..services.user_settings import load_visual_mode, save_visual_mode
from .layout import LayoutMixin
from .grid_montage import GridMontageMixin
from .label_replacement import LabelReplacementMixin
from .montage import MontageMixin
from .preview import PreviewMixin
from .result_organizer import ResultOrganizerMixin
from .reflection_removal import ReflectionRemovalMixin
from .shortcuts import ShortcutsMixin
from .theme import COLORS, configure_styles

class CropApp(
    LayoutMixin,
    PreviewMixin,
    MontageMixin,
    GridMontageMixin,
    LabelReplacementMixin,
    ResultOrganizerMixin,
    ReflectionRemovalMixin,
    ShortcutsMixin,
):

    def __init__(self, window: tk.Tk) -> None:
        self.window = window
        self.window.title("Análise de amostras · TCC")
        self.window.geometry("1360x860")
        self.window.minsize(1080, 720)
        self.window.configure(fg_color=COLORS["background"])
        self.root_var = tk.StringVar(value=str(DEFAULT_SOURCE_DIR))
        try:
            self.visual_mode = load_visual_mode()
        except (OSError, ValueError) as error:
            self.visual_mode = "quality"
            self.status_var = tk.StringVar(
                value=f"Modo visual padrão; configuração indisponível: {error}"
            )
        self.visual_mode_var = tk.StringVar(
            value="Qualidade"
            if self.visual_mode == "quality"
            else "Desempenho"
        )
        self.material_filter = tk.StringVar(value="Todos")
        if not hasattr(self, "status_var"):
            self.status_var = tk.StringVar(
                value="Selecione uma pasta e analise as fotos."
            )
        self.count_var = tk.StringVar(value="0 fotos  ·  0 com 1 quadrado  ·  0 para revisar")
        self.results: list[PhotoResult] = []
        self.preview_images: list[ImageTk.PhotoImage] = []
        self.scan_root: Path | None = None
        self.manual_overrides: dict[Path, PhotoResult] = {}
        self.preserved_scan_count = 0
        self.current_preview_path: Path | None = None
        self.original_image: Image.Image | None = None
        self.preview_zoom = 1.0
        self.manual_clicks: list[tuple[float, float]] = []
        self.manual_active = False
        self.manual_result_index: int | None = None
        self.manual_add_mode = False
        self.manual_original_corners: list[np.ndarray] = []
        self.manual_original_state: tuple[bool, bool] = (False, False)
        self.preview_drag: tuple[str, int, int, np.ndarray] | None = None
        self.crop_index = 0
        self.preview_transform: tuple[float, float, float, float] | None = None
        self.montage_paths: list[Path] = []
        self.montage_image: Image.Image | None = None
        self.montage_photo: ImageTk.PhotoImage | None = None
        self.montage_canvas_rotation = 0
        self.montage_status_var = tk.StringVar(
            value="Atualize as imagens e escolha uma foto para cada letra."
        )
        self.montage_slot_paths: list[Path | None] = [None] * 6
        self.montage_rotations: dict[str, int] = {}
        self.montage_path_by_label: dict[str, Path] = {}
        self.montage_gallery_paths: dict[str, Path] = {}
        self.montage_gallery_images: list[ImageTk.PhotoImage] = []
        self.montage_selected_path: Path | None = None
        self.montage_selected_image: Image.Image | None = None
        self.montage_source_photo: ImageTk.PhotoImage | None = None
        self.montage_target_slot = 0
        self.montage_target_buttons = []
        self.reflection_path: Path | None = None
        self.reflection_original: np.ndarray | None = None
        self.reflection_processed: np.ndarray | None = None
        self.reflection_mask: np.ndarray | None = None
        self.reflection_strokes: list[tuple[int, int]] = []
        self.label_summary_var = tk.StringVar(value="Analise imgs_results para começar.")
        self.label_status_var = tk.StringVar(
            value="Os arquivos originais só serão substituídos após confirmação."
        )
        self.label_scan_busy = False
        self.label_processing_busy = False
        self.label_scan_root: Path | None = None
        self.label_image_paths: dict[str, Path] = {}
        self.label_squares: dict[Path, list[LabelSquare]] = {}
        self.label_change_counts: dict[Path, int] = {}
        self.label_errors: dict[Path, str] = {}
        self.label_preview_image: Image.Image | None = None
        self.label_preview_squares: list[LabelSquare] = []
        self.label_preview_photo: ImageTk.PhotoImage | None = None
        self.shortcut_status_var = tk.StringVar(
            value="Atalhos padrão ativos."
        )
        self.shortcut_vars = {}
        self.busy = False
        configure_styles(self.window)
        self._initialize_shortcuts()
        for action, shortcut in self.shortcuts.items():
            self.shortcut_vars[action] = tk.StringVar(value=shortcut)
        self._build_layout()
        self.window.after_idle(self._restore_cached_scan)

    def _set_visual_mode(self, _event: tk.Event | None = None) -> None:
        selected_mode = (
            "quality"
            if self.visual_mode_var.get() == "Qualidade"
            else "performance"
        )
        try:
            save_visual_mode(selected_mode)
        except (OSError, ValueError) as error:
            self.visual_mode_var.set(
                "Qualidade" if self.visual_mode == "quality" else "Desempenho"
            )
            messagebox.showerror("Falha ao salvar preferência visual", str(error))
            return
        self.visual_mode = selected_mode
        if self.tree.selection():
            self._show_selection()
        if hasattr(self, "montage_gallery"):
            self._filter_montage_gallery()
            self._draw_montage_source()
            self._draw_montage_preview()
        if hasattr(self, "label_image_tree") and self.label_preview_image:
            self._draw_label_preview()

    def _choose_folder(self) -> None:
        selected = filedialog.askdirectory(
            title="Pasta com as fotos",
            initialdir=self.root_var.get() or str(DEFAULT_SOURCE_DIR),
        )
        if selected:
            self.root_var.set(selected)

    def _restore_cached_scan(self) -> None:
        root = Path(self.root_var.get()).expanduser()
        try:
            previous_root = get_cached_scan_root()
            if previous_root is not None and previous_root.is_dir():
                root = previous_root
                self.root_var.set(str(root))
            cached_results = (
                load_scan_cache(root)
                if root.is_dir() and root.name.casefold() not in SKIP_DIRECTORIES
                else None
            )
        except (OSError, ValueError) as error:
            self.status_var.set(
                f"Cache indisponível; analisando as fotos novamente: {error}"
            )
            cached_results = None
        self._refresh_montage_sources()
        if not root.is_dir() or root.name.casefold() in SKIP_DIRECTORIES:
            self._start_scan()
            return
        if cached_results is not None:
            self._finish_scan(root, cached_results, cached=True)
            self.status_var.set("Análise restaurada do cache salvo.")
            return
        self._start_scan()

    def _persist_scan_cache(self) -> None:
        if self.scan_root is None:
            return
        try:
            save_scan_cache(self.scan_root, self.results)
        except (OSError, ValueError) as error:
            self.status_var.set(f"Não foi possível salvar a análise: {error}")

    def _start_scan(self) -> None:
        if self.busy:
            return
        self._cancel_manual_crop()
        root = Path(self.root_var.get()).expanduser()
        if not root.is_dir():
            messagebox.showerror("Pasta inválida", "Selecione uma pasta existente.")
            return
        if root.name.casefold() in SKIP_DIRECTORIES:
            messagebox.showerror(
                "Pasta ignorada",
                "Selecione uma pasta acima de artigos, out, imgs_results ou da pasta virtual.",
            )
            return
        try:
            if self.preserve_ready_var.get():
                self.manual_overrides = load_preserved_scan_results(root)
            else:
                self.manual_overrides = load_manual_scan_overrides(root)
        except (OSError, ValueError) as error:
            self.manual_overrides = {}
            messagebox.showwarning(
                "Anotações manuais indisponíveis",
                f"Não foi possível restaurar as marcações anteriores: {error}",
            )
        self.busy = True
        self.scan_button.configure(state="disabled")
        self.process_button.configure(state="disabled")
        self.manual_button.configure(state="disabled")
        self.manual_add_button.configure(state="disabled")
        self.grid_utility_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.manual_active = False
        self.manual_clicks.clear()
        self.preserved_scan_count = len(self.manual_overrides)
        self.manual_button.configure(
            text="Marcar quadrados", command=self._start_manual_crop
        )
        self.progress.start(10)
        self.status_var.set("Analisando imagens…")
        self.tree.delete(*self.tree.get_children())
        self.results = []
        self.preview_images = []
        self._clear_canvases()
        threading.Thread(
            target=self._scan_worker,
            args=(root, self.manual_overrides.copy()),
            daemon=True,
        ).start()

    def _scan_worker(
        self,
        root: Path,
        preserved_results: dict[Path, PhotoResult],
    ) -> None:
        try:
            results = scan_images(root, skip_paths=set(preserved_results))
        except OSError as error:
            self.window.after(0, self._fail_scan, error)
            return
        for result in results:
            override = preserved_results.get(result.path)
            if override is not None:
                result.corners = override.corners
                result.error = override.error
                result.manual = override.manual
                result.needs_review = override.needs_review
        results_by_path = {
            result.path: result for result in (*results, *preserved_results.values())
        }
        results = sorted(
            results_by_path.values(),
            key=lambda result: str(result.path.relative_to(root)).casefold(),
        )
        self.window.after(0, self._finish_scan, root, results)

    def _fail_scan(self, error: OSError) -> None:
        self.busy = False
        self.progress.stop()
        self.scan_button.configure(state="normal")
        self.status_var.set(f"Falha ao listar imagens: {error}")
        messagebox.showerror("Falha na análise", str(error))

    def _finish_scan(
        self,
        root: Path,
        results: list[PhotoResult],
        cached: bool = False,
    ) -> None:
        self.busy = False
        self.progress.stop()
        self.scan_button.configure(state="normal")
        self.results = results
        self.scan_root = root
        matches = 0
        review = 0
        errors = 0
        for result in results:
            if result.error:
                errors += 1
            elif result.ready_for_export:
                matches += 1
            elif result.needs_review:
                review += 1
        self.count_var.set(
            f"{len(results)} fotos  ·  {matches} prontas para corte  ·  "
            f"{review} para revisar"
        )
        self.status_var.set(
            f"{errors} erro(s). Confirme o contorno no preview antes de cortar."
            if errors
            else "Confirme o contorno no preview antes de cortar."
        )
        if self.preserved_scan_count:
            self.status_var.set(
                f"{self.preserved_scan_count} foto(s) pronta(s) preservada(s). "
                f"{self.status_var.get()}"
            )
        if matches:
            self.process_button.configure(state="normal")
            self.manual_button.configure(state="normal")
            self.manual_add_button.configure(state="normal")
        elif results:
            self.manual_button.configure(state="normal")
            self.manual_add_button.configure(state="normal")
        self._populate_photo_list()
        if not cached:
            self._persist_scan_cache()

    def _visible_result_indices(self) -> list[int]:
        material = self.material_filter.get()
        if material == "Todos" or self.scan_root is None:
            return list(range(len(self.results)))
        material = material.casefold()
        return [
            index
            for index, result in enumerate(self.results)
            if material
            in {
                part.casefold()
                for part in result.path.relative_to(self.scan_root).parts
            }
        ]

    def _populate_photo_list(self) -> None:
        self.tree.delete(*self.tree.get_children())
        indices = self._visible_result_indices()
        for index in indices:
            result = self.results[index]
            relative = str(result.path.relative_to(self.scan_root))
            if result.error:
                status = "erro"
            elif result.manual:
                status = "manual"
            elif result.needs_review:
                status = "revisar"
            elif len(result.corners) > 1:
                status = f"{len(result.corners)} quadrados"
            elif len(result.corners) == 1:
                status = "1 quadrado"
            else:
                status = "não detectado"
            self.tree.insert(
                "",
                "end",
                iid=str(index),
                text=relative,
                values=(len(result.corners), status),
            )

        if not indices:
            self.manual_active = False
            self.manual_clicks.clear()
            self.manual_add_button.configure(state="disabled")
            self.grid_utility_button.configure(state="disabled")
            self.selected_var.set("Nenhuma foto para este material")
            self._clear_canvases()
            return

        selected = next(
            (
                index
                for index in indices
                if self.results[index].ready_for_export
            ),
            indices[0],
        )
        item = str(selected)
        self.tree.selection_set(item)
        self.tree.focus(item)
        self.tree.see(item)
        self._show_selection()

    def _set_material_filter(self, material: str) -> None:
        self.material_filter.set(material)
        self._cancel_manual_crop()
        self.process_button.configure(
            state="normal"
            if any(
                result.ready_for_export
                for result in self.results
            )
            else "disabled"
        )
        self._update_material_buttons()
        self._populate_photo_list()

    def _update_material_buttons(self) -> None:
        for material, button in self.material_buttons.items():
            button.configure(
                style=(
                    "FilterActive.TButton"
                    if self.material_filter.get() == material
                    else "Filter.TButton"
                )
            )

    def _process_results(self) -> None:
        root = Path(self.root_var.get()).expanduser()
        if self.scan_root is None or root != self.scan_root:
            messagebox.showerror(
                "Analise novamente",
                "A pasta mudou. Analise as fotos antes de gerar os recortes.",
            )
            return
        matches = [
            result
            for result in self.results
            if result.ready_for_export
        ]
        if not matches:
            return
        output = root / "out"
        if not messagebox.askyesno(
            "Gerar recortes",
            f"{len(matches)} foto(s) serão cortadas em:\n{output}\n\n"
            "A substituição de recortes existentes será confirmada em seguida.",
        ):
            return
        existing = [
            destination
            for result in matches
            for destination in crop_destinations(root, result)
            if destination.exists()
        ]
        overwrite = bool(existing) and messagebox.askyesno(
            "Substituir recortes existentes?",
            f"{len(existing)} arquivo(s) já existem em out.\n"
            "Deseja substituí-los pelos novos recortes?",
            icon="warning",
        )
        report = export_crops(root, matches, overwrite=overwrite)
        self.open_button.configure(state="normal" if output.is_dir() else "disabled")
        summary = f"{report.saved} recorte(s) salvo(s) em out."
        if report.skipped:
            summary += f" {report.skipped} já existiam e foram mantidos."
        if report.errors:
            summary += f" {len(report.errors)} erro(s): {report.errors[0]}"
        if report.skipped:
            summary += (
                " Arquivos já existentes foram preservados; "
                "confirme a substituição para atualizá-los."
            )
        self.status_var.set(summary)
        if report.errors:
            messagebox.showwarning("Processamento concluído", summary)

    def _open_output(self) -> None:
        output = Path(self.root_var.get()).expanduser() / "out"
        if output.is_dir():
            os.startfile(output)
