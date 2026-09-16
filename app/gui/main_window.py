"""Janela principal (Sprint 8/9).

Compoe ``ImportFrame`` e ``AnalysisFrame``; a tela de resultados
(``ResultsFrame``) e adicionada na Sprint 9. Nao contem regra de
negocio — apenas orquestra os frames e repassa dados entre eles.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.gui.analysis_view import AnalysisFrame
from app.gui.import_view import ImportFrame
from app.gui.results_view import ResultsFrame
from app.models.comparison_result import ComparisonResult
from app.services.analysis_service import AnalysisStats


class MainWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Detector de Duplicidade de Materiais")
        self.geometry("720x560")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        setup_tab = ttk.Frame(notebook)
        notebook.add(setup_tab, text="Configuracao")

        self._import_frame = ImportFrame(setup_tab, on_selection_changed=self._on_selection_changed)
        self._import_frame.pack(fill="x")

        self._analysis_frame = AnalysisFrame(setup_tab, on_done=self._on_analysis_done)
        self._analysis_frame.pack(fill="x")

        self._results_tab = ttk.Frame(notebook)
        notebook.add(self._results_tab, text="Resultados")
        self._results_frame = ResultsFrame(self._results_tab)
        self._results_frame.pack(fill="both", expand=True)

        self._notebook = notebook

    def _on_selection_changed(self, file_path: str, sheet_name: str, code_column: str, analysis_column: str) -> None:
        self._analysis_frame.set_selection(file_path, sheet_name, code_column, analysis_column)

    def _on_analysis_done(self, results: list[ComparisonResult], stats: AnalysisStats) -> None:
        self._results_frame.load_results(results)
        self._notebook.select(self._results_tab)


def main() -> None:
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
