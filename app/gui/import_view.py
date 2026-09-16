"""Tela/frame de importacao de planilha (Sprint 8).

Responsavel apenas por: selecionar o arquivo, listar planilhas e
colunas, e notificar o container (``main_window``) quando a selecao
muda. Nao contem nenhuma regra de negocio — toda leitura passa por
``app.services.excel_service``.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from app.services.excel_service import ExcelFileError, list_columns, list_sheet_names

SelectionCallback = Callable[[str, str, str, str], None]


class ImportFrame(ttk.Frame):
    def __init__(self, master: tk.Misc, on_selection_changed: SelectionCallback) -> None:
        super().__init__(master, padding=10)
        self._on_selection_changed = on_selection_changed
        self._file_path: str = ""

        self._file_label_var = tk.StringVar(value="Nenhum arquivo selecionado")
        self._sheet_var = tk.StringVar()
        self._code_column_var = tk.StringVar()
        self._analysis_column_var = tk.StringVar()

        ttk.Label(self, text="Arquivo:").grid(row=0, column=0, sticky="w")
        ttk.Button(self, text="Selecionar arquivo", command=self._select_file).grid(
            row=0, column=1, sticky="w", padx=5
        )
        ttk.Label(self, textvariable=self._file_label_var).grid(row=0, column=2, sticky="w")

        ttk.Label(self, text="Planilha:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self._sheet_combo = ttk.Combobox(self, textvariable=self._sheet_var, state="readonly")
        self._sheet_combo.grid(row=1, column=1, columnspan=2, sticky="ew", pady=(8, 0))
        self._sheet_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_sheet_selected())

        ttk.Label(self, text="Coluna do codigo:").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self._code_combo = ttk.Combobox(self, textvariable=self._code_column_var, state="readonly")
        self._code_combo.grid(row=2, column=1, columnspan=2, sticky="ew", pady=(8, 0))
        self._code_combo.bind("<<ComboboxSelected>>", lambda _e: self._notify())

        ttk.Label(self, text="Coluna para analise:").grid(row=3, column=0, sticky="w", pady=(8, 0))
        self._analysis_combo = ttk.Combobox(
            self, textvariable=self._analysis_column_var, state="readonly"
        )
        self._analysis_combo.grid(row=3, column=1, columnspan=2, sticky="ew", pady=(8, 0))
        self._analysis_combo.bind("<<ComboboxSelected>>", lambda _e: self._notify())

        self.columnconfigure(2, weight=1)

    def _select_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Selecionar planilha",
            filetypes=[("Planilhas Excel", "*.xlsx")],
        )
        if not file_path:
            return
        try:
            sheet_names = list_sheet_names(file_path)
        except ExcelFileError as exc:
            messagebox.showerror("Erro ao abrir arquivo", str(exc))
            return

        self._file_path = file_path
        self._file_label_var.set(file_path.split("/")[-1])
        self._sheet_combo["values"] = sheet_names
        if sheet_names:
            self._sheet_var.set(sheet_names[0])
            self._on_sheet_selected()

    def _on_sheet_selected(self) -> None:
        try:
            columns = list_columns(self._file_path, self._sheet_var.get())
        except ExcelFileError as exc:
            messagebox.showerror("Erro ao ler planilha", str(exc))
            return

        self._code_combo["values"] = columns
        self._analysis_combo["values"] = columns
        if columns:
            self._code_column_var.set(columns[0])
            self._analysis_column_var.set(columns[-1])
        self._notify()

    def _notify(self) -> None:
        self._on_selection_changed(
            self._file_path,
            self._sheet_var.get(),
            self._code_column_var.get(),
            self._analysis_column_var.get(),
        )
