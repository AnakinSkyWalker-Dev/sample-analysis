from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from ..services.user_settings import load_user_settings, save_user_settings


DEFAULT_SHORTCUTS = {
    "zoom_in": "Ctrl+=",
    "zoom_out": "Ctrl+-",
    "zoom_reset": "Ctrl+0",
    "previous_crop": "Alt+Left",
    "next_crop": "Alt+Right",
    "toggle_manual": "Ctrl+M",
}

SHORTCUT_LABELS = {
    "zoom_in": "Aumentar zoom",
    "zoom_out": "Diminuir zoom",
    "zoom_reset": "Ajustar à tela",
    "previous_crop": "Recorte anterior",
    "next_crop": "Próximo recorte",
    "toggle_manual": "Iniciar / concluir marcação manual",
}


def _event_shortcut(event: tk.Event) -> str | None:
    keysym = str(event.keysym)
    if keysym in {
        "Alt_L",
        "Alt_R",
        "Control_L",
        "Control_R",
        "Shift_L",
        "Shift_R",
    }:
        return None

    modifiers = []
    if event.state & 0x4:
        modifiers.append("Ctrl")
    if event.state & (0x8 | 0x20000):
        modifiers.append("Alt")
    if event.state & 0x1:
        modifiers.append("Shift")

    key_names = {
        "equal": "=",
        "minus": "-",
        "plus": "+",
        "KP_Add": "+",
        "KP_Subtract": "-",
        "Return": "Enter",
        "Prior": "PageUp",
        "Next": "PageDown",
        "space": "Space",
    }
    key = key_names.get(keysym, keysym.upper() if len(keysym) == 1 else keysym)
    if key in {"Control", "Alt", "Shift"}:
        return None
    return "+".join([*modifiers, key])


class ShortcutsMixin:
    def _initialize_shortcuts(self) -> None:
        self.shortcuts = DEFAULT_SHORTCUTS.copy()
        try:
            saved = load_user_settings()
        except (OSError, ValueError) as error:
            self.status_var.set(f"Atalhos padrão carregados: {error}")
        else:
            for action, shortcut in saved.items():
                if action in self.shortcuts and shortcut:
                    self.shortcuts[action] = shortcut
        self.shortcut_capture_action: str | None = None
        self.shortcut_vars: dict[str, tk.StringVar] = {}
        self.window.bind_all("<KeyPress>", self._handle_shortcut_key, add="+")

    def _handle_shortcut_key(self, event: tk.Event) -> str | None:
        shortcut = _event_shortcut(event)
        if shortcut is None:
            return None
        if self.shortcut_capture_action is not None:
            self._set_captured_shortcut(self.shortcut_capture_action, shortcut)
            return "break"
        try:
            focus = self.window.focus_get()
        except (KeyError, tk.TclError):
            return None
        if focus is not None and focus.winfo_class() in {
            "Entry",
            "TEntry",
            "TCombobox",
            "Text",
        }:
            return None
        for action, assigned in self.shortcuts.items():
            if assigned == shortcut:
                self._run_shortcut_action(action)
                return "break"
        return None

    def _run_shortcut_action(self, action: str) -> None:
        handlers = {
            "zoom_in": self._zoom_in,
            "zoom_out": self._zoom_out,
            "zoom_reset": self._reset_zoom,
            "previous_crop": self._previous_crop,
            "next_crop": self._next_crop,
            "toggle_manual": self._toggle_manual_crop,
        }
        handlers[action]()

    def _toggle_manual_crop(self) -> None:
        if self.manual_active:
            self._finish_manual_crop()
        else:
            self._start_manual_crop()

    def _begin_shortcut_capture(self, action: str) -> None:
        self.shortcut_capture_action = action
        self.shortcut_status_var.set(
            f"Pressione a combinação para “{SHORTCUT_LABELS[action]}”…"
        )
        self.window.focus_force()

    def _set_captured_shortcut(self, action: str, shortcut: str) -> None:
        self.shortcut_capture_action = None
        duplicate_action = next(
            (
                other_action
                for other_action, assigned in self.shortcuts.items()
                if other_action != action and assigned == shortcut
            ),
            None,
        )
        duplicate = (
            SHORTCUT_LABELS[duplicate_action]
            if duplicate_action is not None
            else None
        )
        if duplicate:
            self.shortcut_status_var.set(
                f"{shortcut} já está atribuído a “{duplicate}”."
            )
            return
        self.shortcuts[action] = shortcut
        self.shortcut_vars[action].set(shortcut)
        self._save_shortcuts()
        self.shortcut_status_var.set(
            f"Atalho salvo: {SHORTCUT_LABELS[action]} — {shortcut}."
        )

    def _reset_shortcuts(self) -> None:
        self.shortcuts = DEFAULT_SHORTCUTS.copy()
        for action, shortcut in self.shortcuts.items():
            self.shortcut_vars[action].set(shortcut)
        self._save_shortcuts()
        self.shortcut_status_var.set("Atalhos padrão restaurados.")

    def _save_shortcuts(self) -> None:
        try:
            save_user_settings(self.shortcuts)
        except OSError as error:
            messagebox.showerror("Falha ao salvar atalhos", str(error))
