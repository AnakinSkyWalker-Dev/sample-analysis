from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from ..services.result_organizer import (
    RenamePlan,
    apply_result_renames,
    build_result_rename_plan,
)


class ResultOrganizerMixin:
    def _open_result_organizer(self) -> None:
        root = Path(self.root_var.get()).expanduser() / "imgs_results"
        try:
            plan = build_result_rename_plan(root)
        except (OSError, ValueError) as error:
            messagebox.showerror("Falha ao analisar nomes", str(error))
            return

        dialog = tk.Toplevel(self.window)
        dialog.title("Organizar nomes de imgs_results")
        dialog.geometry("820x500")
        dialog.minsize(640, 360)
        dialog.transient(self.window)
        dialog.grab_set()

        container = ttk.Frame(dialog, padding=16)
        container.pack(fill="both", expand=True)
        ttk.Label(
            container,
            text=(
                f"{len(plan.renames)} arquivo(s) podem ser renomeados. "
                "Confira a prévia antes de aplicar."
            ),
            style="Section.TLabel",
        ).pack(anchor="w", pady=(0, 10))

        table_frame = ttk.Frame(container)
        table_frame.pack(fill="both", expand=True)
        tree = ttk.Treeview(
            table_frame,
            columns=("current", "new", "status"),
            show="headings",
            selectmode="browse",
        )
        tree.heading("current", text="Nome atual")
        tree.heading("new", text="Novo nome")
        tree.heading("status", text="Estado")
        tree.column("current", width=250, minwidth=150)
        tree.column("new", width=300, minwidth=180)
        tree.column("status", width=190, minwidth=150)
        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=tree.yview,
        )
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        conflict_sources = {item.source for item in plan.conflicts}
        for entry in plan.renames:
            status = (
                "conflito: destino existente"
                if entry.source in conflict_sources
                else "pronto"
            )
            tree.insert(
                "",
                "end",
                values=(
                    str(entry.source.relative_to(root)),
                    str(entry.destination.relative_to(root)),
                    status,
                ),
            )
        for entry in plan.skipped:
            tree.insert(
                "",
                "end",
                values=(
                    str(entry.path.relative_to(root)),
                    "—",
                    f"mantido: {entry.reason}",
                ),
            )

        footer = ttk.Frame(container)
        footer.pack(fill="x", pady=(12, 0))
        ttk.Label(
            footer,
            text=(
                f"{len(plan.skipped)} arquivo(s) serão mantidos sem alteração."
                if plan.skipped
                else "Todos os nomes reconhecidos estão prontos."
            ),
            style="Muted.TLabel",
        ).pack(side="left", fill="x", expand=True)
        ttk.Button(
            footer,
            text="Fechar",
            command=dialog.destroy,
        ).pack(side="right", padx=(8, 0))
        apply_button = ttk.Button(
            footer,
            text="Renomear arquivos",
            style="Primary.TButton",
            command=lambda: self._apply_result_rename_plan(dialog, plan),
            state="normal" if plan.renames and not plan.conflicts else "disabled",
        )
        apply_button.pack(side="right")

    def _apply_result_rename_plan(
        self,
        dialog: tk.Toplevel,
        plan: RenamePlan,
    ) -> None:
        if not messagebox.askyesno(
            "Confirmar renomeação",
            f"{len(plan.renames)} arquivo(s) em imgs_results serão "
            "renomeados. Os arquivos não serão movidos para outra pasta.\n\n"
            "Deseja continuar?",
            parent=dialog,
        ):
            return
        try:
            count = apply_result_renames(plan)
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Falha ao renomear arquivos",
                str(error),
                parent=dialog,
            )
            return
        messagebox.showinfo(
            "Renomeação concluída",
            f"{count} arquivo(s) renomeado(s).",
            parent=dialog,
        )
        dialog.destroy()
