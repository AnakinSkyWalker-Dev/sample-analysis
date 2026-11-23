from __future__ import annotations

import colorsys
from pathlib import Path
import tkinter as tk
import cv2
import numpy as np
from PIL import Image, ImageTk
from ..images import load_rgb, order_corners, rectify_square
from .image_rendering import fit_preview, resize_preview

class PreviewMixin:

    def _show_selection(self, _event: tk.Event | None = None) -> None:
        selection = self.tree.selection()
        if not selection or not self.results:
            if hasattr(self, "grid_utility_button"):
                self.grid_utility_button.configure(state="disabled")
            return
        if hasattr(self, "grid_utility_button"):
            self.grid_utility_button.configure(state="normal")
        selected_index = int(selection[0])
        if (
            self.manual_active
            and self.manual_result_index is not None
            and selected_index != self.manual_result_index
        ):
            self._cancel_manual_crop()
        result = self.results[int(selection[0])]
        root = self.scan_root or Path(self.root_var.get()).expanduser()
        try:
            if self.current_preview_path != result.path:
                self.current_preview_path = result.path
                self.preview_zoom = 1.0
            relative = result.path.relative_to(root)
            self.selected_var.set(str(relative))
            rgb = load_rgb(result.path)
            preview = Image.fromarray(rgb)
            self.original_image = preview
            if not result.corners:
                self.crop_index = 0
            else:
                self.crop_index = min(self.crop_index, len(result.corners) - 1)
            crop = (
                rectify_square(
                    rgb,
                    result.corners[self.crop_index],
                    expansion_factor=1.0 if result.manual else 1.2,
                )
                if result.corners
                else None
            )
        except (OSError, ValueError, cv2.error) as error:
            self.status_var.set(f"Não foi possível abrir a foto: {error}")
            return
        self._update_crop_navigation(len(result.corners))
        self._draw_images(preview, crop, result.corners)

    def _draw_images(
        self,
        original: Image.Image,
        crop: Image.Image | None,
        corners: list[np.ndarray],
    ) -> None:
        self._clear_canvases()
        self.window.update_idletasks()
        self.original_image = original
        canvas_width = max(1, self.source_canvas.winfo_width())
        canvas_height = max(1, self.source_canvas.winfo_height())
        fit_scale = min(
            max(1, canvas_width - 16) / original.width,
            max(1, canvas_height - 16) / original.height,
        )
        display_scale = fit_scale * self.preview_zoom
        display_size = (
            max(1, round(original.width * display_scale)),
            max(1, round(original.height * display_scale)),
        )
        original_preview = resize_preview(
            original, display_size, self.visual_mode
        )
        source_photo = ImageTk.PhotoImage(original_preview)
        self.preview_images.append(source_photo)
        sx = display_size[0] / original.width
        sy = display_size[1] / original.height
        offset_x = max(0, (canvas_width - display_size[0]) / 2)
        offset_y = max(0, (canvas_height - display_size[1]) / 2)
        self.source_canvas.create_image(
            offset_x,
            offset_y,
            image=source_photo,
            anchor="nw",
        )
        self.source_canvas.configure(
            scrollregion=(
                0,
                0,
                max(canvas_width, offset_x + display_size[0]),
                max(canvas_height, offset_y + display_size[1]),
            )
        )
        self.preview_transform = (offset_x, offset_y, sx, sy)
        for index, polygon in enumerate(corners):
            points = []
            for x, y in polygon:
                points.extend((offset_x + x * sx, offset_y + y * sy))
            hue = index / max(len(corners), 1)
            red, green, blue = colorsys.hsv_to_rgb(hue, 0.82, 0.85)
            color = f"#{round(red * 255):02x}{round(green * 255):02x}{round(blue * 255):02x}"
            self.source_canvas.create_polygon(
                *points, outline=color, fill="", width=2
            )
            center_x = sum(points[::2]) / 4
            center_y = sum(points[1::2]) / 4
            self.source_canvas.create_text(
                center_x,
                center_y,
                text=str(index + 1),
                fill="#ffffff",
                font=("Segoe UI Semibold", 10),
            )
        self._draw_manual_clicks(offset_x, offset_y, sx, sy)
        if crop is not None:
            crop_preview = fit_preview(
                crop,
                self._fit_size(self.crop_canvas, crop.size),
                self.visual_mode,
            )
            crop_photo = ImageTk.PhotoImage(crop_preview)
            self.preview_images.append(crop_photo)
            self.crop_canvas.create_image(
                self.crop_canvas.winfo_width() / 2,
                self.crop_canvas.winfo_height() / 2,
                image=crop_photo,
                anchor="center",
            )
        else:
            self.crop_canvas.create_text(
                self.crop_canvas.winfo_width() / 2,
                self.crop_canvas.winfo_height() / 2,
                text="Marque os 4 cantos para ver os recortes.",
                fill="#718096",
                width=max(100, self.crop_canvas.winfo_width() - 28),
                font=("Segoe UI", 8),
            )
        if hasattr(self, "zoom_label_var"):
            self.zoom_label_var.set(f"{round(self.preview_zoom * 100)}%")

    def _draw_manual_clicks(
        self,
        offset_x: float,
        offset_y: float,
        scale_x: float,
        scale_y: float,
    ) -> None:
        if not self.manual_active or not self.manual_clicks:
            return
        points = [
            (offset_x + x * scale_x, offset_y + y * scale_y)
            for x, y in self.manual_clicks
        ]
        if len(points) > 1:
            self.source_canvas.create_line(
                *[coordinate for point in points for coordinate in point],
                fill="#2459a6",
                width=2,
            )
        for index, (x, y) in enumerate(points):
            radius = 5
            self.source_canvas.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill="#2459a6",
                outline="#ffffff",
                width=2,
            )
            self.source_canvas.create_text(
                x + 10,
                y - 10,
                text=str(index + 1),
                fill="#ffffff",
                font=("Segoe UI Semibold", 9),
            )

    def _change_zoom(self, factor: float) -> None:
        if self.original_image is None:
            return
        self.preview_zoom = min(4.0, max(0.25, self.preview_zoom * factor))
        self._show_selection()

    def _zoom_in(self) -> None:
        self._change_zoom(1.25)

    def _zoom_out(self) -> None:
        self._change_zoom(0.8)

    def _reset_zoom(self) -> None:
        if self.original_image is None:
            return
        self.preview_zoom = 1.0
        self._show_selection()

    def _zoom_mousewheel(self, event: tk.Event) -> str:
        if getattr(event, "num", None) == 4 or getattr(event, "delta", 0) > 0:
            self._zoom_in()
        else:
            self._zoom_out()
        return "break"

    def _update_crop_navigation(self, count: int) -> None:
        self.crop_index_var.set(
            f"{self.crop_index + 1}/{count}" if count else "0/0"
        )
        state = "normal" if count > 1 else "disabled"
        self.crop_previous_button.configure(state=state)
        self.crop_next_button.configure(state=state)

    def _previous_crop(self) -> None:
        self._change_crop(-1)

    def _next_crop(self) -> None:
        self._change_crop(1)

    def _change_crop(self, direction: int) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        result = self.results[int(selection[0])]
        if len(result.corners) < 2:
            return
        self.crop_index = (self.crop_index + direction) % len(result.corners)
        self._show_selection()

    @staticmethod
    def _fit_size(canvas: tk.Canvas, _image_size: tuple[int, int]) -> tuple[int, int]:
        return max(1, canvas.winfo_width() - 16), max(1, canvas.winfo_height() - 16)

    def _start_manual_crop(self) -> None:
        self._begin_manual_crop(add=False)

    def _add_manual_square(self) -> None:
        self._begin_manual_crop(add=True)

    def _begin_manual_crop(self, add: bool) -> None:
        selection = self.tree.selection()
        if not selection:
            self.status_var.set("Selecione uma foto para marcar os cantos.")
            return
        result = self.results[int(selection[0])]
        if result.error:
            self.status_var.set("Esta foto não pôde ser aberta.")
            return
        self.manual_active = True
        self.manual_result_index = int(selection[0])
        self.manual_add_mode = add
        self.manual_original_corners = [
            corners.copy() for corners in result.corners
        ]
        self.manual_original_state = (result.manual, result.needs_review)
        self.manual_clicks.clear()
        if not add:
            result.corners.clear()
        self.crop_index = 0
        self._update_result_row(int(selection[0]))
        self.process_button.configure(state="disabled")
        self.manual_button.configure(
            text="Concluir marcação", command=self._finish_manual_crop
        )
        self.manual_add_button.configure(state="disabled")
        self._show_selection()
        self.status_var.set(
            "Marque os 4 cantos do quadrado que falta."
            if add
            else "Marque os 4 cantos por quadrado; repita para adicionar outros."
        )

    def _cancel_manual_crop(self) -> None:
        if not self.manual_active:
            return
        if self.manual_result_index is not None:
            result = self.results[self.manual_result_index]
            result.corners = [
                corners.copy() for corners in self.manual_original_corners
            ]
            result.manual, result.needs_review = self.manual_original_state
            if self.tree.exists(str(self.manual_result_index)):
                self._update_result_row(self.manual_result_index)
        self.manual_active = False
        self.manual_result_index = None
        self.manual_add_mode = False
        self.manual_clicks.clear()
        self.manual_original_corners.clear()
        self.manual_button.configure(
            text="Marcar quadrados", command=self._start_manual_crop
        )
        self.manual_add_button.configure(state="normal")
        self.process_button.configure(
            state="normal"
            if any(
                item.ready_for_export
                for item in self.results
            )
            else "disabled"
        )

    def _finish_manual_crop(self) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        result_index = int(selection[0])
        result = self.results[result_index]
        if self.manual_add_mode:
            if len(result.corners) > len(self.manual_original_corners):
                result.manual = True
                result.needs_review = False
            else:
                result.manual, result.needs_review = self.manual_original_state
        else:
            result.manual = bool(result.corners)
            result.needs_review = False
        self.manual_active = False
        self.manual_result_index = None
        self.manual_add_mode = False
        self.manual_clicks.clear()
        self.manual_original_corners.clear()
        self._update_result_row(result_index)
        self.manual_button.configure(
            text="Marcar quadrados", command=self._start_manual_crop
        )
        self.manual_add_button.configure(state="normal")
        self.process_button.configure(
            state="normal"
            if any(
                item.ready_for_export
                for item in self.results
            )
            else "disabled"
        )
        self.count_var.set(self._count_summary())
        self._persist_scan_cache()
        self._show_selection()
        self.status_var.set(
            f"{len(result.corners)} quadrado(s) marcado(s) nesta foto. "
            "A prévia foi atualizada; clique em Cortar fotos identificadas para salvar."
            if result.corners
            else "Nenhum quadrado marcado."
        )

    def _update_result_row(self, result_index: int) -> None:
        if not self.tree.exists(str(result_index)):
            return
        result = self.results[result_index]
        if self.manual_active and result_index == self.manual_result_index:
            status = "marcando"
        elif result.error:
            status = "erro"
        elif result.manual:
            status = "manual"
        elif result.needs_review:
            status = "revisar"
        elif len(result.corners) > 1:
            status = f"{len(result.corners)} quadrados"
        elif result.corners:
            status = "1 quadrado"
        else:
            status = "não detectado"
        self.tree.set(str(result_index), "squares", len(result.corners))
        self.tree.set(str(result_index), "status", status)

    def _manual_corner(self, event: tk.Event) -> None:
        if not self.manual_active:
            self._begin_preview_adjustment(event)
            return
        if not self.manual_active or not self.preview_transform:
            return
        selection = self.tree.selection()
        if not selection:
            return
        result = self.results[int(selection[0])]
        try:
            rgb = load_rgb(result.path)
        except (OSError, ValueError) as error:
            self._cancel_manual_crop()
            self.status_var.set(f"Não foi possível abrir a foto: {error}")
            return
        offset_x, offset_y, scale_x, scale_y = self.preview_transform
        canvas_x = self.source_canvas.canvasx(event.x)
        canvas_y = self.source_canvas.canvasy(event.y)
        x = (canvas_x - offset_x) / scale_x
        y = (canvas_y - offset_y) / scale_y
        height, width = rgb.shape[:2]
        if not 0 <= x < width or not 0 <= y < height:
            return
        self.manual_clicks.append((x, y))
        if len(self.manual_clicks) < 4:
            self._show_selection()
            self.status_var.set(
                f"Canto {len(self.manual_clicks)} de 4 marcado."
            )
            return
        corners = order_corners(np.asarray(self.manual_clicks, dtype=np.float32))
        polygon_area = abs(cv2.contourArea(corners))
        contour = corners.astype(np.int32).reshape(-1, 1, 2)
        if (
            polygon_area < width * height * 0.008
            or not cv2.isContourConvex(contour)
            or np.min(
                np.linalg.norm(corners - np.roll(corners, -1, axis=0), axis=1)
            )
            < min(width, height) * 0.04
        ):
            self.manual_clicks.clear()
            self._show_selection()
            self.status_var.set(
                "Os cantos não formam um quadrado válido. Marque os 4 novamente."
            )
            return
        result.corners.append(corners)
        self.crop_index = len(result.corners) - 1
        self.manual_clicks.clear()
        self.tree.set(selection[0], "squares", len(result.corners))
        self.tree.set(selection[0], "status", f"marcando ({len(result.corners)})")
        self.count_var.set(self._count_summary())
        self._show_selection()
        self.status_var.set(
            f"Quadrado {len(result.corners)} marcado. "
            "Continue com outros ou conclua a marcação."
        )

    def _begin_preview_adjustment(self, event: tk.Event) -> None:
        if not self.preview_transform:
            return
        selection = self.tree.selection()
        if not selection:
            return
        result = self.results[int(selection[0])]
        if not result.corners:
            return
        offset_x, offset_y, scale_x, scale_y = self.preview_transform
        canvas_x = self.source_canvas.canvasx(event.x)
        canvas_y = self.source_canvas.canvasy(event.y)
        hit: tuple[float, int, str, int] | None = None
        for square_index, corners in enumerate(result.corners):
            points = [
                (offset_x + float(x) * scale_x, offset_y + float(y) * scale_y)
                for x, y in corners
            ]
            corner_distances = [
                (point[0] - canvas_x) ** 2 + (point[1] - canvas_y) ** 2
                for point in points
            ]
            corner = min(range(4), key=corner_distances.__getitem__)
            if corner_distances[corner] <= 18**2:
                candidate = (corner_distances[corner], square_index, "corner", corner)
                if hit is None or candidate[0] < hit[0]:
                    hit = candidate
                continue
            for edge in range(4):
                distance = self._preview_segment_distance(
                    canvas_x,
                    canvas_y,
                    points[edge],
                    points[(edge + 1) % 4],
                )
                if distance <= 14 and (hit is None or distance < hit[0]):
                    hit = (distance, square_index, "edge", edge)
        if hit is None:
            return
        _, square_index, mode, handle = hit
        point = self._preview_image_point(event)
        if point is None:
            return
        self.preview_drag = (mode, square_index, handle, point)
        result.manual = True
        result.needs_review = False
        self.status_var.set(
            f"Quadrado {square_index + 1} selecionado; arraste a linha ou o canto."
        )

    def _drag_preview_adjustment(self, event: tk.Event) -> None:
        if self.manual_active or self.preview_drag is None:
            return
        selection = self.tree.selection()
        point = self._preview_image_point(event)
        if not selection or point is None:
            return
        mode, square_index, handle, previous = self.preview_drag
        result = self.results[int(selection[0])]
        if square_index >= len(result.corners):
            return
        corners = result.corners[square_index]
        height, width = load_rgb(result.path).shape[:2]
        if mode == "corner":
            corners[handle] = point
        else:
            delta = point - previous
            first = handle
            second = (handle + 1) % 4
            minimum = np.asarray([0, 0], dtype=np.float32)
            maximum = np.asarray([width - 1, height - 1], dtype=np.float32)
            corners[first] = np.clip(corners[first] + delta, minimum, maximum)
            corners[second] = np.clip(corners[second] + delta, minimum, maximum)
        self.preview_drag = (mode, square_index, handle, point)
        self._update_result_row(int(selection[0]))
        self._show_selection()

    def _finish_preview_adjustment(self, _event: tk.Event) -> None:
        self.preview_drag = None

    def _preview_image_point(self, event: tk.Event) -> np.ndarray | None:
        if not self.preview_transform:
            return None
        offset_x, offset_y, scale_x, scale_y = self.preview_transform
        x = (self.source_canvas.canvasx(event.x) - offset_x) / scale_x
        y = (self.source_canvas.canvasy(event.y) - offset_y) / scale_y
        selection = self.tree.selection()
        if not selection:
            return None
        height, width = load_rgb(self.results[int(selection[0])].path).shape[:2]
        if not 0 <= x < width or not 0 <= y < height:
            return None
        return np.asarray([x, y], dtype=np.float32)

    @staticmethod
    def _preview_segment_distance(
        point_x: float,
        point_y: float,
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> float:
        point = np.asarray([point_x, point_y], dtype=np.float32)
        first = np.asarray(start, dtype=np.float32)
        vector = np.asarray(end, dtype=np.float32) - first
        length = float(np.dot(vector, vector))
        if length <= 0:
            return float(np.linalg.norm(point - first))
        factor = float(np.dot(point - first, vector) / length)
        factor = max(0.0, min(1.0, factor))
        return float(np.linalg.norm(point - (first + factor * vector)))

    def _count_summary(self) -> str:
        matches = sum(result.ready_for_export for result in self.results)
        review = sum(
            result.needs_review and not result.manual
            for result in self.results
        )
        return f"{len(self.results)} fotos  ·  {matches} prontas para corte  ·  {review} para revisar"

    def _redraw_preview(self, _event: tk.Event | None = None) -> None:
        selection = self.tree.selection()
        if selection:
            self._show_selection()

    def _clear_canvases(self) -> None:
        self.source_canvas.delete("all")
        self.crop_canvas.delete("all")
        self.preview_images.clear()
