from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter as tk

from PIL import Image, ImageOps, ImageTk

from ..images.files import IMAGE_EXTENSIONS
from ..services.montage import compose_montage
from ..services.user_settings import (
    load_montage_canvas_rotation,
    load_montage_rotations,
    load_montage_selection,
    save_montage_canvas_rotation,
    save_montage_rotations,
    save_montage_selection,
)
from .image_rendering import fit_preview


class MontageMixin:
    def _set_montage_material_filter(self, material: str) -> None:
        self.montage_filter_var.set(material)
        for name, button in self.montage_material_buttons.items():
            button.configure(
                style=(
                    "FilterActive.TButton"
                    if name == material
                    else "Filter.TButton"
                )
            )
        self._filter_montage_gallery()

    def _refresh_montage_sources(self) -> None:
        output = Path(self.root_var.get()).expanduser() / "out"
        if not output.is_dir():
            self.montage_gallery.delete(*self.montage_gallery.get_children())
            self.montage_gallery_paths.clear()
            self.montage_gallery_images.clear()
            self.montage_path_by_label.clear()
            self.montage_slot_paths = [None] * 6
            self.montage_paths = []
            self.montage_selected_path = None
            self.montage_selected_image = None
            self.montage_source_photo = None
            self.montage_source_canvas.delete("all")
            self.montage_source_info_var.set(
                "Selecione uma foto, escolha A–F e clique em Usar foto. ↻ gira a foto."
            )
            self.montage_assign_button.configure(state="disabled")
            self.montage_rotate_button.configure(state="disabled")
            self._invalidate_montage("A pasta out não existe neste local.")
            return
        try:
            paths = sorted(
                (
                    path
                    for path in output.rglob("*")
                    if path.is_file()
                    and path.suffix.casefold() in IMAGE_EXTENSIONS
                ),
                key=lambda path: str(path.relative_to(output)).casefold(),
            )
            saved_selection = load_montage_selection()
            saved_rotations = load_montage_rotations()
            saved_canvas_rotation = load_montage_canvas_rotation()
        except (OSError, ValueError) as error:
            self._invalidate_montage(f"Falha ao carregar imagens de out: {error}")
            messagebox.showerror("Falha ao carregar imagens", str(error))
            return

        previous_source = self.montage_selected_path
        self.montage_path_by_label = {
            str(path.relative_to(output)): path for path in paths
        }
        self.montage_rotations = {
            str(output / relative_path): degrees
            for relative_path, degrees in saved_rotations.items()
            if relative_path in self.montage_path_by_label
        }
        self.montage_canvas_rotation = saved_canvas_rotation
        self.montage_slot_paths = [
            self.montage_path_by_label.get(relative_path)
            for relative_path in saved_selection[:6]
        ]
        self.montage_slot_paths.extend(
            [None] * (6 - len(self.montage_slot_paths))
        )
        self.montage_paths = [
            path for path in self.montage_slot_paths if path is not None
        ]
        self.montage_selected_path = (
            previous_source if previous_source in paths else None
        )
        self._filter_montage_gallery()
        self._update_montage_preview()
        if not paths:
            self._invalidate_montage("Nenhuma imagem encontrada em out.")

    def _filter_montage_gallery(self) -> None:
        if not hasattr(self, "montage_gallery"):
            return
        previous = self.montage_selected_path
        self.montage_gallery.delete(*self.montage_gallery.get_children())
        self.montage_gallery_paths.clear()
        self.montage_gallery_images.clear()
        query = self.montage_search_var.get().strip().casefold()
        material = self.montage_filter_var.get()
        for index, (relative_path, path) in enumerate(
            self.montage_path_by_label.items()
        ):
            if material != "Todos" and material.casefold() not in {
                part.casefold() for part in Path(relative_path).parts
            }:
                continue
            if query and query not in relative_path.casefold():
                continue
            thumbnail = self._montage_thumbnail(path)
            image = None
            if thumbnail is not None:
                image = ImageTk.PhotoImage(thumbnail)
                self.montage_gallery_images.append(image)
            self.montage_gallery.insert(
                "",
                "end",
                iid=str(index),
                text="",
                image=image,
                values=(relative_path,),
            )
            self.montage_gallery_paths[str(index)] = path
            if path == previous:
                self.montage_gallery.selection_set(str(index))
                self.montage_gallery.focus(str(index))

        if not self.montage_gallery.selection():
            self.montage_selected_path = None
            self.montage_selected_image = None
            self.montage_source_canvas.delete("all")
            self.montage_source_info_var.set(
                "Selecione uma foto, escolha A–F e clique em Usar foto. ↻ gira a foto."
            )
            self.montage_assign_button.configure(state="disabled")
            self.montage_rotate_button.configure(state="disabled")

    def _montage_thumbnail(self, path: Path) -> Image.Image | None:
        try:
            with Image.open(path) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
            thumbnail_size = 88 if self.visual_mode == "quality" else 68
            return fit_preview(
                image,
                (thumbnail_size, thumbnail_size),
                self.visual_mode,
            )
        except (OSError, ValueError):
            return None

    def _select_montage_source(self, _event: tk.Event | None = None) -> None:
        selection = self.montage_gallery.selection()
        if not selection:
            return
        path = self.montage_gallery_paths.get(selection[0])
        if path is None:
            return
        try:
            with Image.open(path) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
        except (OSError, ValueError) as error:
            self.montage_selected_path = None
            self.montage_selected_image = None
            self.montage_source_info_var.set(f"Não foi possível abrir a foto: {error}")
            self.montage_source_canvas.delete("all")
            self.montage_assign_button.configure(state="disabled")
            self.montage_rotate_button.configure(state="disabled")
            return
        self.montage_selected_path = path
        self.montage_selected_image = image
        relative = path.relative_to(Path(self.root_var.get()).expanduser() / "out")
        self.montage_source_info_var.set(
            f"{relative}  ·  {image.width} × {image.height} px  ·  posição "
            f"{chr(ord('A') + self.montage_target_slot)}"
        )
        self.montage_assign_button.configure(state="normal")
        self.montage_rotate_button.configure(state="normal")
        self._draw_montage_source()

    def _draw_montage_source(self, _event: tk.Event | None = None) -> None:
        canvas = self.montage_source_canvas
        canvas.delete("all")
        if self.montage_selected_image is None:
            return
        display_image = self._rotated_montage_source()
        width = max(1, canvas.winfo_width() - 12)
        height = max(1, canvas.winfo_height() - 12)
        preview = fit_preview(
            display_image,
            (width, height),
            self.visual_mode,
        )
        self.montage_source_photo = ImageTk.PhotoImage(preview)
        canvas.create_image(
            canvas.winfo_width() / 2,
            canvas.winfo_height() / 2,
            image=self.montage_source_photo,
            anchor="center",
        )

    def _rotated_montage_source(self) -> Image.Image:
        image = self.montage_selected_image
        if image is None or self.montage_selected_path is None:
            raise ValueError("Nenhuma foto está selecionada.")
        rotation = self.montage_rotations.get(
            str(self.montage_selected_path), 0
        ) % 360
        return image.rotate(-rotation, expand=True) if rotation else image

    def _rotate_montage_source(self) -> None:
        path = self.montage_selected_path
        if path is None:
            return
        output = Path(self.root_var.get()).expanduser() / "out"
        relative_path = str(path.relative_to(output))
        rotations = {
            key: value
            for key, value in self.montage_rotations.items()
            if Path(key).is_relative_to(output)
        }
        rotation = (rotations.get(str(path), 0) + 90) % 360
        if rotation:
            rotations[str(path)] = rotation
        else:
            rotations.pop(str(path), None)
        saved_rotations = {
            str(Path(key).relative_to(output)): value
            for key, value in rotations.items()
        }
        try:
            save_montage_rotations(saved_rotations)
        except (OSError, ValueError) as error:
            messagebox.showerror("Falha ao salvar rotação", str(error))
            return
        self.montage_rotations = rotations
        self.montage_source_info_var.set(
            f"{relative_path}  ·  rotação {rotation}°  ·  posição "
            f"{chr(ord('A') + self.montage_target_slot)}"
        )
        self._draw_montage_source()
        self._update_montage_preview()

    def _rotate_whole_montage(self) -> None:
        if self.montage_image is None:
            return
        rotation = (self.montage_canvas_rotation + 90) % 360
        try:
            save_montage_canvas_rotation(rotation)
        except (OSError, ValueError) as error:
            messagebox.showerror("Falha ao salvar rotação", str(error))
            return
        self.montage_canvas_rotation = rotation
        self._update_montage_preview()

    def _set_montage_target(self, index: int) -> None:
        self.montage_target_slot = index
        for button_index, button in enumerate(self.montage_target_buttons):
            button.configure(
                style=(
                    "MontageTargetActive.TButton"
                    if button_index == index
                    else "TButton"
                )
            )
        if self.montage_selected_path is not None:
            self._select_montage_source()

    def _assign_selected_montage_source(self) -> None:
        path = self.montage_selected_path
        if path is None:
            return
        output = Path(self.root_var.get()).expanduser() / "out"
        updated_selection = self.montage_slot_paths.copy()
        updated_selection[self.montage_target_slot] = path
        try:
            save_montage_selection(
                [
                    str(item.relative_to(output)) if item is not None else ""
                    for item in updated_selection
                ]
            )
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Falha ao salvar seleção da montagem", str(error)
            )
            return
        self.montage_slot_paths = updated_selection
        self._update_montage_preview()
        self.montage_status_var.set(
            f"Foto atribuída à posição "
            f"{chr(ord('A') + self.montage_target_slot)}. Seleções salvas."
        )

    def _update_montage_preview(self) -> None:
        if any(path is None for path in self.montage_slot_paths):
            assigned = sum(path is not None for path in self.montage_slot_paths)
            self._invalidate_montage(
                f"{assigned}/6 posições preenchidas. Escolha uma foto e atribua-a a A–F."
            )
            return
        self.montage_paths = [
            path for path in self.montage_slot_paths if path is not None
        ]
        try:
            image = compose_montage(
                self.montage_paths,
                self.montage_rotations,
            )
            if self.montage_canvas_rotation:
                image = image.rotate(-self.montage_canvas_rotation, expand=True)
            self.montage_image = image
        except (OSError, ValueError) as error:
            self._invalidate_montage(f"Falha ao montar: {error}")
            messagebox.showerror("Falha na montagem", str(error))
            return
        self.montage_save_button.configure(state="normal")
        self.montage_canvas_rotate_button.configure(state="normal")
        self.montage_status_var.set(
            "  ·  ".join(
                f"{chr(ord('A') + index)}: {path.name}"
                for index, path in enumerate(self.montage_paths)
            )
        )
        self._draw_montage_preview()

    def _invalidate_montage(self, message: str) -> None:
        self.montage_image = None
        self.montage_save_button.configure(state="disabled")
        self.montage_canvas_rotate_button.configure(state="disabled")
        self.montage_status_var.set(message)
        self._draw_montage_preview()

    def _draw_montage_preview(self, _event: tk.Event | None = None) -> None:
        canvas = self.montage_canvas
        canvas.delete("all")
        if self.montage_image is None:
            return
        available_width = max(1, canvas.winfo_width() - 16)
        available_height = max(1, canvas.winfo_height() - 16)
        preview = fit_preview(
            self.montage_image,
            (available_width, available_height),
            self.visual_mode,
        )
        self.montage_photo = ImageTk.PhotoImage(preview)
        canvas.create_image(
            canvas.winfo_width() / 2,
            canvas.winfo_height() / 2,
            image=self.montage_photo,
            anchor="center",
        )

    def _save_montage(self) -> None:
        if self.montage_image is None:
            return
        destination = filedialog.asksaveasfilename(
            title="Salvar montagem",
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg *.jpeg")],
            initialfile="montagem.png",
        )
        if not destination:
            return
        try:
            image = self.montage_image
            if Path(destination).suffix.casefold() in {".jpg", ".jpeg"}:
                image.save(destination, quality=95)
            else:
                image.save(destination, format="PNG")
        except (OSError, ValueError) as error:
            messagebox.showerror("Falha ao salvar montagem", str(error))
            return
        self.montage_status_var.set(f"Montagem salva: {destination}")
