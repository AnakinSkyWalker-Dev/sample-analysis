from __future__ import annotations

from pathlib import Path
import ctypes
import sys
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

import cv2
import numpy as np
from PIL import Image, ImageOps, ImageTk

from ..images.detection import order_corners
from ..images.files import IMAGE_EXTENSIONS, load_rgb
from ..services.grid_montage import (
    DEFAULT_GRID_SPACING,
    GRID_COLUMNS,
    GRID_ROWS,
    MAX_GRID_SPACING,
    compose_grid_montage,
    detect_grid_squares,
    save_grid_montage,
)
from .image_rendering import fit_preview


class GridMontageMixin:
    def _open_selected_grid_editor(self) -> None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning(
                "Selecione uma foto",
                "Selecione uma imagem na lista de Corte de amostras.",
            )
            return
        result = self.results[int(selection[0])]
        try:
            rgb = load_rgb(result.path)
            squares, detected_count = detect_grid_squares(rgb)
        except (OSError, ValueError, cv2.error) as error:
            messagebox.showerror(
                "Não foi possível preparar os quadrados",
                str(error),
            )
            return
        self._open_grid_montage_editor(result.path, rgb, squares, detected_count)

    def _start_grid_montage(self) -> None:
        source = filedialog.askopenfilename(
            title="Escolher foto com grade 4×3",
            initialdir=self.root_var.get(),
            filetypes=[
                ("Imagens", " ".join(f"*{suffix}" for suffix in IMAGE_EXTENSIONS)),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not source:
            return
        path = Path(source)
        try:
            rgb = load_rgb(path)
            squares, detected_count = detect_grid_squares(rgb)
        except (OSError, ValueError, cv2.error) as error:
            messagebox.showerror(
                "Não foi possível preparar a grade",
                str(error),
            )
            return
        self._open_grid_montage_editor(path, rgb, squares, detected_count)

    def _open_grid_montage_editor(
        self,
        path: Path,
        rgb: np.ndarray,
        squares: list[np.ndarray],
        detected_count: int,
    ) -> None:
        dialog = tk.Toplevel(self.window)
        dialog.title(f"Montagem 4×3 · {path.name}")
        dialog.geometry("1240x820")
        dialog.minsize(1000, 680)
        dialog.transient(self.window)
        dialog.grab_set()

        state: dict[str, object] = {
            "squares": [square.copy() for square in squares],
            "original_squares": [square.copy() for square in squares],
            "selected": 0,
            "rotations": [0] * (GRID_COLUMNS * GRID_ROWS),
            "spacing": DEFAULT_GRID_SPACING,
            "scale": 1.0,
            "offset_x": 0.0,
            "offset_y": 0.0,
            "drag_mode": None,
            "drag_last": None,
            "placing": False,
            "manual_points": [],
            "render_job": None,
            "source_photo": None,
            "result_photo": None,
            "result_image": None,
        }

        def rotate_source(direction: int) -> None:
            nonlocal rgb
            if not messagebox.askyesno(
                "Girar foto e refazer detecção?",
                "A foto será girada 90° e os quadrados serão identificados novamente. "
                "Os ajustes manuais atuais serão descartados. Continuar?",
                parent=dialog,
            ):
                return
            rotated = np.rot90(rgb, k=direction).copy()
            try:
                redetected, redetected_count = detect_grid_squares(rotated)
            except (ValueError, cv2.error) as error:
                messagebox.showerror(
                    "Não foi possível redetectar os quadrados",
                    str(error),
                    parent=dialog,
                )
                return
            rgb = rotated
            state["squares"] = [square.copy() for square in redetected]
            state["original_squares"] = [square.copy() for square in redetected]
            state["rotations"] = [0] * (GRID_COLUMNS * GRID_ROWS)
            state["selected"] = 0
            state["placing"] = False
            state["manual_points"] = []
            selection_var.set(self._grid_square_name(0))
            status_var.set(self._grid_detection_summary(redetected_count))
            draw_source()
            schedule_result()

        def redetect_current_source() -> None:
            try:
                redetected, redetected_count = detect_grid_squares(rgb)
            except (ValueError, cv2.error) as error:
                messagebox.showerror(
                    "Não foi possível identificar os quadrados",
                    str(error),
                    parent=dialog,
                )
                return
            state["squares"] = [square.copy() for square in redetected]
            state["original_squares"] = [square.copy() for square in redetected]
            state["rotations"] = [0] * (GRID_COLUMNS * GRID_ROWS)
            state["selected"] = 0
            state["placing"] = False
            state["manual_points"] = []
            selection_var.set(self._grid_square_name(0))
            status_var.set(self._grid_detection_summary(redetected_count))
            draw_source()
            schedule_result()

        container = ttk.Frame(dialog, padding=14)
        container.pack(fill="both", expand=True)
        toolbar = ttk.Frame(container)
        toolbar.pack(fill="x", pady=(0, 9))
        ttk.Label(
            toolbar,
            text="Grade 4×3 · arraste os cantos para corrigir a detecção",
            style="Section.TLabel",
        ).pack(side="left", fill="x", expand=True)

        selector_row = ttk.Frame(container)
        selector_row.pack(fill="x", pady=(0, 8))
        ttk.Label(selector_row, text="Quadrado").pack(side="left", padx=(0, 5))
        selection_var = tk.StringVar(value=self._grid_square_name(0))
        choices = [
            self._grid_square_name(row * GRID_COLUMNS + column)
            for row in range(GRID_ROWS)
            for column in range(GRID_COLUMNS)
        ]
        selector = ttk.Combobox(
            selector_row,
            textvariable=selection_var,
            values=choices,
            state="readonly",
            width=7,
        )
        selector.pack(side="left", padx=(0, 8))
        ttk.Label(
            selector_row,
            text="Clique em qualquer linha para selecionar e ajustar sem refazer os 4 cantos.",
            style="Muted.TLabel",
        ).pack(side="left", padx=(8, 8))
        ttk.Button(
            selector_row,
            text="Marcar 4 cantos",
            command=lambda: self._begin_grid_manual_corners(
                state,
                selection_var,
                status_var,
            ),
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            selector_row,
            text="Reidentificar quadrados",
            command=redetect_current_source,
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            selector_row,
            text="Restaurar quadrado",
            command=lambda: self._reset_grid_square(
                state,
                selection_var,
                draw_source,
                schedule_result,
                status_var,
            ),
        ).pack(side="left")
        ttk.Button(
            selector_row,
            text="↺ Quadrado",
            command=lambda: self._rotate_grid_tiles(
                state, selection_var, -1, draw_source, schedule_result, status_var
            ),
        ).pack(side="left", padx=(12, 2))
        ttk.Button(
            selector_row,
            text="↻ Quadrado",
            command=lambda: self._rotate_grid_tiles(
                state, selection_var, 1, draw_source, schedule_result, status_var
            ),
        ).pack(side="left", padx=2)
        ttk.Button(
            selector_row,
            text="↻ Todos",
            command=lambda: self._rotate_grid_tiles(
                state, selection_var, 1, draw_source, schedule_result, status_var, True
            ),
        ).pack(side="left", padx=2)
        ttk.Button(
            selector_row,
            text="↺ Foto",
            command=lambda: rotate_source(-1),
        ).pack(side="left", padx=(12, 2))
        ttk.Button(
            selector_row,
            text="↻ Foto",
            command=lambda: rotate_source(1),
        ).pack(side="left", padx=2)

        panels = ttk.Panedwindow(container, orient="horizontal")
        panels.pack(fill="both", expand=True)
        source_panel = ttk.Frame(panels, style="Panel.TFrame", padding=8)
        result_panel = ttk.Frame(panels, style="Panel.TFrame", padding=8)
        panels.add(source_panel, weight=1)
        panels.add(result_panel, weight=1)
        ttk.Label(
            source_panel,
            text="Foto original · selecione e corrija os cantos",
            style="Section.TLabel",
        ).pack(anchor="w", pady=(0, 6))
        source_canvas = tk.Canvas(
            source_panel,
            bg="#202833",
            highlightthickness=0,
        )
        source_canvas.pack(fill="both", expand=True)
        source_canvas.bind(
            "<Configure>",
            lambda _event: draw_source(),
        )
        source_canvas.bind(
            "<Button-1>",
            lambda event: self._grid_canvas_press(
                event,
                state,
                rgb,
                source_canvas,
                draw_source,
                schedule_result,
                selection_var,
                status_var,
            ),
        )
        source_canvas.bind(
            "<B1-Motion>",
            lambda event: self._grid_canvas_drag(
                event,
                state,
                rgb,
                source_canvas,
                draw_source,
                schedule_result,
            ),
        )
        source_canvas.bind(
            "<ButtonRelease-1>",
            lambda _event: (
                state.__setitem__("drag_mode", None),
                state.__setitem__("drag_last", None),
            ),
        )

        ttk.Label(
            result_panel,
            text="Prancha · etiquetas A–D identificam as colunas",
            style="Section.TLabel",
        ).pack(anchor="w", pady=(0, 6))
        result_canvas = tk.Canvas(
            result_panel,
            bg="#202833",
            highlightthickness=0,
        )
        result_canvas.pack(fill="both", expand=True)
        result_canvas.bind(
            "<Configure>",
            lambda _event: draw_result(),
        )

        footer = ttk.Frame(container)
        footer.pack(fill="x", pady=(9, 0))
        spacing_var = tk.IntVar(value=DEFAULT_GRID_SPACING)
        ttk.Label(footer, text="Espaçamento").pack(side="left", padx=(0, 6))
        spacing_scale = tk.Scale(
            footer,
            from_=0,
            to=MAX_GRID_SPACING,
            orient="horizontal",
            showvalue=True,
            resolution=2,
            variable=spacing_var,
            length=220,
            command=lambda value: self._set_grid_spacing(
                value,
                state,
                schedule_result,
            ),
        )
        spacing_scale.pack(side="left")
        status_var = tk.StringVar(
            value=self._grid_detection_summary(detected_count)
        )
        ttk.Label(
            footer,
            textvariable=status_var,
            style="Muted.TLabel",
            wraplength=500,
        ).pack(side="left", fill="x", expand=True, padx=10)
        ttk.Button(
            footer,
            text="Fechar",
            command=dialog.destroy,
        ).pack(side="right", padx=(8, 0))
        ttk.Button(
            footer,
            text="Salvar em imgs_results",
            style="Primary.TButton",
            command=lambda: self._save_grid_montage(
                path,
                rgb,
                state,
                dialog,
            ),
        ).pack(side="right")

        def draw_source() -> None:
            canvas = source_canvas
            canvas.delete("all")
            available = (
                max(1, canvas.winfo_width() - 16),
                max(1, canvas.winfo_height() - 16),
            )
            preview = ImageOps.contain(
                Image.fromarray(rgb),
                available,
                method=Image.Resampling.LANCZOS,
            )
            photo = ImageTk.PhotoImage(preview)
            state["source_photo"] = photo
            offset_x = (canvas.winfo_width() - preview.width) / 2
            offset_y = (canvas.winfo_height() - preview.height) / 2
            scale = preview.width / rgb.shape[1]
            state["scale"] = scale
            state["offset_x"] = offset_x
            state["offset_y"] = offset_y
            canvas.create_image(offset_x, offset_y, image=photo, anchor="nw")

            active_index = int(state["selected"])
            for index, corners in enumerate(state["squares"]):
                points = [
                    (
                        offset_x + float(x) * scale,
                        offset_y + float(y) * scale,
                    )
                    for x, y in corners
                ]
                color = "#f4c95d" if index == active_index else "#15c4c8"
                canvas.create_polygon(
                    *[coordinate for point in points for coordinate in point],
                    fill="",
                    outline=color,
                    width=3 if index == active_index else 2,
                )
                center_x = sum(point[0] for point in points) / 4
                center_y = sum(point[1] for point in points) / 4
                canvas.create_text(
                    center_x,
                    center_y,
                    text=(
                        chr(ord("A") + index)
                        if index < GRID_COLUMNS
                        else ""
                    ),
                    fill="#ffffff",
                    font=("Segoe UI Semibold", 10),
                    tags=("grid-label",),
                )
                if index == active_index:
                    for point_x, point_y in points:
                        canvas.create_oval(
                            point_x - 6,
                            point_y - 6,
                            point_x + 6,
                            point_y + 6,
                            fill="#f4c95d",
                            outline="#172033",
                            width=1,
                        )
                    for edge_index in range(4):
                        start = points[edge_index]
                        end = points[(edge_index + 1) % 4]
                        midpoint_x = (start[0] + end[0]) / 2
                        midpoint_y = (start[1] + end[1]) / 2
                        canvas.create_rectangle(
                            midpoint_x - 5,
                            midpoint_y - 5,
                            midpoint_x + 5,
                            midpoint_y + 5,
                            fill="#65d6ff",
                            outline="#172033",
                            width=1,
                        )

            manual_points = state["manual_points"]
            for x, y in manual_points:
                canvas_x = offset_x + float(x) * scale
                canvas_y = offset_y + float(y) * scale
                canvas.create_oval(
                    canvas_x - 5,
                    canvas_y - 5,
                    canvas_x + 5,
                    canvas_y + 5,
                    fill="#ff7a59",
                    outline="#ffffff",
                    width=1,
                )

        def draw_result() -> None:
            canvas = result_canvas
            canvas.delete("all")
            image = state["result_image"]
            if image is None:
                return
            preview = fit_preview(
                image,
                (max(1, canvas.winfo_width() - 16),
                 max(1, canvas.winfo_height() - 16)),
                self.visual_mode,
            )
            photo = ImageTk.PhotoImage(preview)
            state["result_photo"] = photo
            canvas.create_image(
                canvas.winfo_width() / 2,
                canvas.winfo_height() / 2,
                image=photo,
                anchor="center",
            )

        def render_result() -> None:
            state["render_job"] = None
            try:
                state["result_image"] = compose_grid_montage(
                    rgb,
                    state["squares"],
                    int(state["spacing"]),
                    state["rotations"],
                )
            except (ValueError, cv2.error) as error:
                status_var.set(f"Falha ao atualizar a prévia: {error}")
                return
            draw_result()

        def schedule_result() -> None:
            pending = state["render_job"]
            if pending is not None:
                dialog.after_cancel(pending)
            state["render_job"] = dialog.after(100, render_result)

        def select_square(_event: tk.Event | None = None) -> None:
            state["selected"] = choices.index(selection_var.get())
            state["manual_points"] = []
            state["placing"] = False
            draw_source()

        selector.bind("<<ComboboxSelected>>", select_square)

        draw_source()
        render_result()
        dialog.after_idle(lambda: self._maximize_grid_dialog(dialog))

    def _grid_canvas_press(
        self,
        event: tk.Event,
        state: dict[str, object],
        rgb: np.ndarray,
        canvas: tk.Canvas,
        draw_source: object,
        schedule_result: object,
        selection_var: tk.StringVar,
        status_var: tk.StringVar,
    ) -> None:
        if bool(state["placing"]):
            point = self._grid_canvas_point(event, state, rgb)
            if point is None:
                return
            points = state["manual_points"]
            points.append(point)
            if len(points) == 4:
                try:
                    state["squares"][int(state["selected"])] = order_corners(
                        np.asarray(points, dtype=np.float32)
                    )
                except (ValueError, cv2.error) as error:
                    status_var.set(f"Não consegui ordenar os cantos: {error}")
                    state["manual_points"] = []
                    draw_source()
                    return
                state["manual_points"] = []
                state["placing"] = False
                status_var.set(
                    f"{self._grid_square_name(int(state['selected']))} "
                    "redefinido por quatro cliques."
                )
                schedule_result()
            else:
                status_var.set(
                    f"Canto {len(points)}/4 marcado. Continue clicando "
                    "nos cantos em qualquer ordem."
                )
            draw_source()
            return

        scale = float(state["scale"])
        offset_x = float(state["offset_x"])
        offset_y = float(state["offset_y"])
        hit: tuple[float, int, str, int] | None = None
        for square_index, square in enumerate(state["squares"]):
            handles = [
                (offset_x + float(x) * scale, offset_y + float(y) * scale)
                for x, y in square
            ]
            corner_distances = [
                (handles[index][0] - event.x) ** 2
                + (handles[index][1] - event.y) ** 2
                for index in range(4)
            ]
            corner = min(range(4), key=corner_distances.__getitem__)
            if corner_distances[corner] <= 18**2:
                candidate = (corner_distances[corner], square_index, "corner", corner)
                if hit is None or candidate[0] < hit[0]:
                    hit = candidate
                continue

            edge_distances = [
                self._grid_segment_distance(
                    event.x,
                    event.y,
                    handles[index],
                    handles[(index + 1) % 4],
                )
                for index in range(4)
            ]
            edge = min(range(4), key=edge_distances.__getitem__)
            if edge_distances[edge] <= 14:
                candidate = (edge_distances[edge], square_index, "edge", edge)
                if hit is None or candidate[0] < hit[0]:
                    hit = candidate

        if hit is None:
            state["drag_mode"] = None
            state["drag_last"] = None
            return

        _, square_index, mode, handle_index = hit
        state["selected"] = square_index
        selection_var.set(self._grid_square_name(square_index))
        state["drag_mode"] = (mode, handle_index)
        state["drag_last"] = self._grid_canvas_point(event, state, rgb)
        status_var.set(
            f"{self._grid_square_name(square_index)} selecionado; "
            "arraste a linha ou o ponto destacado para ajustar."
        )
        draw_source()

    def _grid_canvas_drag(
        self,
        event: tk.Event,
        state: dict[str, object],
        rgb: np.ndarray,
        canvas: tk.Canvas,
        draw_source: object,
        schedule_result: object,
    ) -> None:
        drag_mode = state["drag_mode"]
        previous = state["drag_last"]
        if drag_mode is None or previous is None:
            return
        point = self._grid_canvas_point(event, state, rgb)
        if point is None:
            return
        selected = state["squares"][int(state["selected"])]
        mode, index = drag_mode
        if mode == "corner":
            selected[int(index)] = point
        else:
            delta = point - np.asarray(previous, dtype=np.float32)
            first = int(index)
            second = (first + 1) % 4
            bounds_min = np.asarray([0, 0], dtype=np.float32)
            bounds_max = np.asarray(
                [rgb.shape[1] - 1, rgb.shape[0] - 1], dtype=np.float32
            )
            selected[first] = np.clip(selected[first] + delta, bounds_min, bounds_max)
            selected[second] = np.clip(selected[second] + delta, bounds_min, bounds_max)
        state["drag_last"] = point
        draw_source()
        schedule_result()

    @staticmethod
    def _maximize_grid_dialog(dialog: tk.Toplevel) -> None:
        """Maximize within the monitor work area, leaving the taskbar visible."""
        if sys.platform != "win32":
            try:
                dialog.state("zoomed")
            except tk.TclError:
                pass
            return

        try:
            dialog.update_idletasks()
            hwnd = dialog.winfo_id()
            monitor = ctypes.windll.user32.MonitorFromWindow(hwnd, 2)

            class _Rect(ctypes.Structure):
                _fields_ = [
                    ("left", ctypes.c_long),
                    ("top", ctypes.c_long),
                    ("right", ctypes.c_long),
                    ("bottom", ctypes.c_long),
                ]

            class _MonitorInfo(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.c_ulong),
                    ("monitor", _Rect),
                    ("work", _Rect),
                    ("flags", ctypes.c_ulong),
                ]

            info = _MonitorInfo()
            info.cbSize = ctypes.sizeof(_MonitorInfo)
            if monitor and ctypes.windll.user32.GetMonitorInfoW(
                monitor,
                ctypes.byref(info),
            ):
                work = info.work
                width = work.right - work.left
                height = work.bottom - work.top
                dialog.geometry(f"{width}x{height}+{work.left}+{work.top}")
                ctypes.windll.user32.SetWindowPos(
                    hwnd,
                    0,
                    work.left,
                    work.top,
                    width,
                    height,
                    0x0004 | 0x0010,
                )
                return
        except (AttributeError, OSError, tk.TclError):
            pass

        try:
            dialog.state("zoomed")
        except tk.TclError:
            pass

    @staticmethod
    def _grid_segment_distance(
        point_x: float,
        point_y: float,
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> float:
        point = np.asarray([point_x, point_y], dtype=np.float32)
        first = np.asarray(start, dtype=np.float32)
        second = np.asarray(end, dtype=np.float32)
        vector = second - first
        length_squared = float(np.dot(vector, vector))
        if length_squared <= 0:
            return float(np.linalg.norm(point - first))
        projection = float(np.dot(point - first, vector) / length_squared)
        projection = max(0.0, min(1.0, projection))
        return float(np.linalg.norm(point - (first + projection * vector)))

    @staticmethod
    def _grid_canvas_point(
        event: tk.Event,
        state: dict[str, object],
        rgb: np.ndarray,
    ) -> np.ndarray | None:
        scale = float(state["scale"])
        if scale <= 0:
            return None
        x = (event.x - float(state["offset_x"])) / scale
        y = (event.y - float(state["offset_y"])) / scale
        height, width = rgb.shape[:2]
        if not 0 <= x < width or not 0 <= y < height:
            return None
        return np.asarray(
            [min(width - 1, x), min(height - 1, y)],
            dtype=np.float32,
        )

    def _begin_grid_manual_corners(
        self,
        state: dict[str, object],
        selection_var: tk.StringVar,
        status_var: tk.StringVar,
    ) -> None:
        state["selected"] = self._grid_square_index(selection_var.get())
        state["placing"] = True
        state["manual_points"] = []
        status_var.set(
            f"Clique nos quatro cantos de {selection_var.get()} "
            "(ordem livre)."
        )

    def _reset_grid_square(
        self,
        state: dict[str, object],
        selection_var: tk.StringVar,
        draw_source: object,
        schedule_result: object,
        status_var: tk.StringVar,
    ) -> None:
        index = self._grid_square_index(selection_var.get())
        state["squares"][index] = state["original_squares"][index].copy()
        state["rotations"][index] = 0
        state["placing"] = False
        state["manual_points"] = []
        status_var.set(f"{selection_var.get()} voltou à detecção automática.")
        draw_source()
        schedule_result()

    def _rotate_grid_tiles(
        self,
        state: dict[str, object],
        selection_var: tk.StringVar,
        direction: int,
        draw_source: object,
        schedule_result: object,
        status_var: tk.StringVar,
        all_tiles: bool = False,
    ) -> None:
        indices = range(GRID_COLUMNS * GRID_ROWS) if all_tiles else (
            self._grid_square_index(selection_var.get()),
        )
        for index in indices:
            state["rotations"][index] = (
                int(state["rotations"][index]) + direction
            ) % 4
        if all_tiles:
            status_var.set("Todos os quadrados foram girados 90°.")
        else:
            status_var.set(
                f"{selection_var.get()} girado 90°; a rotação será salva na montagem."
            )
        draw_source()
        schedule_result()

    @staticmethod
    def _set_grid_spacing(
        value: str,
        state: dict[str, object],
        schedule_result: object,
    ) -> None:
        state["spacing"] = max(
            0,
            min(MAX_GRID_SPACING, round(float(value))),
        )
        schedule_result()

    def _save_grid_montage(
        self,
        source: Path,
        rgb: np.ndarray,
        state: dict[str, object],
        dialog: tk.Toplevel,
    ) -> None:
        output_root = Path(self.root_var.get()).expanduser()
        destination = (
            output_root
            / "imgs_results"
            / "Montagens"
            / f"{source.stem}.png"
        )
        if destination.exists() and not messagebox.askyesno(
            "Substituir montagem existente?",
            f"Este arquivo já existe:\n{destination}\n\nDeseja substituí-lo?",
            parent=dialog,
        ):
            return
        try:
            image = compose_grid_montage(
                rgb,
                state["squares"],
                int(state["spacing"]),
                state["rotations"],
            )
            save_grid_montage(image, destination)
        except (OSError, ValueError, cv2.error) as error:
            messagebox.showerror(
                "Falha ao salvar montagem",
                str(error),
                parent=dialog,
            )
            return
        messagebox.showinfo(
            "Montagem salva",
            f"Arquivo salvo em:\n{destination}",
            parent=dialog,
        )
        dialog.destroy()

    @staticmethod
    def _grid_square_name(index: int) -> str:
        column = index % GRID_COLUMNS
        row = index // GRID_COLUMNS
        return f"{chr(ord('A') + column)}{row + 1}"

    @staticmethod
    def _grid_square_index(name: str) -> int:
        column = ord(name[0].upper()) - ord("A")
        row = int(name[1:]) - 1
        if not 0 <= column < GRID_COLUMNS or not 0 <= row < GRID_ROWS:
            raise ValueError(f"Posição inválida: {name}")
        return row * GRID_COLUMNS + column

    @staticmethod
    def _grid_detection_summary(detected_count: int) -> str:
        inferred = GRID_COLUMNS * GRID_ROWS - detected_count
        if inferred:
            return (
                f"{detected_count}/12 cantos detectados; {inferred} posição(ões) "
                "estimadas. Confira e ajuste a prévia antes de salvar."
            )
        return "12 quadrados detectados. Arraste os pontos amarelos para ajustar."
