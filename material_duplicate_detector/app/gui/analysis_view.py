"""Tela/frame de configuracao e execucao da analise (Sprint 8).

Dispara ``analysis_service.start_analysis_thread`` e faz polling da
fila de progresso via ``after`` (nunca bloqueia a thread da interface).
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from app.models.comparison_result import ComparisonResult
from app.services.analysis_service import AnalysisStats, start_analysis_thread

_POLL_INTERVAL_MS = 100

DoneCallback = Callable[[list[ComparisonResult], AnalysisStats], None]

_STAGE_LABELS = {
    "ANALISANDO_TEXTOS": "Analisando materiais",
    "COMPARANDO_CANDIDATOS": "Comparando candidatos",
}


class AnalysisFrame(ttk.Frame):
    def __init__(self, master: tk.Misc, on_done: DoneCallback) -> None:
        super().__init__(master, padding=10)
        self._on_done = on_done
        self._selection: tuple[str, str, str, str] | None = None
        self._queue: "queue.Queue" = queue.Queue()
        self._thread: threading.Thread | None = None

        self._status_var = tk.StringVar(value="Aguardando selecao da planilha")
        self._start_button = ttk.Button(
            self, text="INICIAR ANALISE", command=self._start, state="disabled"
        )
        self._start_button.grid(row=0, column=0, pady=(0, 8))

        self._progress = ttk.Progressbar(self, mode="determinate", length=320)
        self._progress.grid(row=1, column=0, sticky="ew")

        ttk.Label(self, textvariable=self._status_var).grid(row=2, column=0, sticky="w", pady=(4, 0))

        self.columnconfigure(0, weight=1)

    def set_selection(self, file_path: str, sheet_name: str, code_column: str, analysis_column: str) -> None:
        valid = bool(file_path and sheet_name and code_column and analysis_column)
        self._selection = (file_path, sheet_name, code_column, analysis_column) if valid else None
        self._start_button["state"] = "normal" if valid else "disabled"
        if valid:
            self._status_var.set("Pronto para iniciar a analise")

    def _start(self) -> None:
        if self._selection is None:
            return
        self._start_button["state"] = "disabled"
        self._progress["value"] = 0
        self._status_var.set("Iniciando...")
        file_path, sheet_name, code_column, analysis_column = self._selection
        self._queue = queue.Queue()
        self._thread = start_analysis_thread(file_path, sheet_name, code_column, analysis_column, self._queue)
        self.after(_POLL_INTERVAL_MS, self._poll)

    def _poll(self) -> None:
        try:
            while True:
                message = self._queue.get_nowait()
                self._handle_message(message)
        except queue.Empty:
            pass

        if self._thread is not None and self._thread.is_alive():
            self.after(_POLL_INTERVAL_MS, self._poll)

    def _handle_message(self, message: dict) -> None:
        kind = message["type"]
        if kind == "progress":
            processed, total = message["processed"], max(message["total"], 1)
            stage_label = _STAGE_LABELS.get(message["stage"], message["stage"])
            self._progress["maximum"] = total
            self._progress["value"] = processed
            percent = (processed / total) * 100
            self._status_var.set(f"{stage_label}... {processed} de {total} ({percent:.0f}%)")
        elif kind == "done":
            self._status_var.set(
                f"Concluido: {message['stats'].total_candidates} candidatos comparados."
            )
            self._start_button["state"] = "normal"
            self._on_done(message["results"], message["stats"])
        elif kind == "error":
            self._status_var.set("Erro na analise")
            self._start_button["state"] = "normal"
            messagebox.showerror("Erro na analise", message["message"])
        elif kind == "cancelled":
            self._status_var.set("Analise cancelada")
            self._start_button["state"] = "normal"
