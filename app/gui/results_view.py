"""Tela de resultados: tabela, filtros, busca, detalhe do par e
exportacao (Sprint 9)."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app.models.comparison_result import ComparisonResult
from app.services.export_service import DEFAULT_MIN_CONFIDENCE, export_results_to_excel

_ALL_CLASSIFICATIONS = "TODAS"
_REVIEW_STATUSES = ["PENDENTE", "APROVADO", "REJEITADO"]


class ResultsFrame(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, padding=10)
        self._results: list[ComparisonResult] = []
        self._visible_indices: list[int] = []

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x")

        ttk.Label(toolbar, text="Classificacao:").pack(side="left")
        self._classification_var = tk.StringVar(value=_ALL_CLASSIFICATIONS)
        self._classification_combo = ttk.Combobox(
            toolbar,
            textvariable=self._classification_var,
            state="readonly",
            values=[
                _ALL_CLASSIFICATIONS,
                "DUPLICADO_CONFIRMADO",
                "PROVAVEL_DUPLICADO",
                "SEMELHANTE_DIFERENTE",
            ],
            width=22,
        )
        self._classification_combo.pack(side="left", padx=(4, 12))
        self._classification_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh())

        ttk.Label(toolbar, text="Buscar:").pack(side="left")
        self._search_var = tk.StringVar()
        search_entry = ttk.Entry(toolbar, textvariable=self._search_var, width=30)
        search_entry.pack(side="left", padx=4)
        search_entry.bind("<KeyRelease>", lambda _e: self._refresh())

        ttk.Label(toolbar, text="Confianca minima (%):").pack(side="left", padx=(12, 0))
        # Padrao 70% — mesmo limite exigido no arquivo exportado, para a
        # tabela e a exportacao mostrarem sempre o mesmo conjunto.
        self._min_confidence_var = tk.StringVar(value=str(int(DEFAULT_MIN_CONFIDENCE * 100)))
        min_confidence_entry = ttk.Entry(toolbar, textvariable=self._min_confidence_var, width=5)
        min_confidence_entry.pack(side="left", padx=4)
        min_confidence_entry.bind("<KeyRelease>", lambda _e: self._refresh())

        ttk.Button(toolbar, text="Exportar para Excel", command=self._export).pack(side="right")

        columns = ("code_a", "code_b", "classification", "confidence", "summary")
        self._tree = ttk.Treeview(self, columns=columns, show="headings")
        for column, heading, width in [
            ("code_a", "Codigo A", 100),
            ("code_b", "Codigo B", 100),
            ("classification", "Classificacao", 160),
            ("confidence", "Confianca", 80),
            ("summary", "Resumo da diferenca", 260),
        ]:
            self._tree.heading(column, text=heading)
            self._tree.column(column, width=width)
        self._tree.pack(fill="both", expand=True, pady=(8, 0))
        self._tree.bind("<Double-1>", lambda _e: self._open_detail())

        status_bar = ttk.Frame(self)
        status_bar.pack(fill="x", pady=(4, 0))
        self._summary_var = tk.StringVar(value="Nenhum resultado carregado")
        ttk.Label(status_bar, textvariable=self._summary_var).pack(side="left")

    def load_results(self, results: list[ComparisonResult]) -> None:
        self._results = list(results)
        self._refresh()

    def _refresh(self) -> None:
        self._tree.delete(*self._tree.get_children())
        classification_filter = self._classification_var.get()
        search_text = self._search_var.get().strip().upper()
        min_confidence = self._parsed_min_confidence()

        self._visible_indices = []
        for index, result in enumerate(self._results):
            if classification_filter != _ALL_CLASSIFICATIONS and result.classification != classification_filter:
                continue
            if result.confidence < min_confidence:
                continue
            haystack = f"{result.code_a} {result.code_b} {result.text_a} {result.text_b}".upper()
            if search_text and search_text not in haystack:
                continue
            self._visible_indices.append(index)
            self._tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    result.code_a,
                    result.code_b,
                    result.classification,
                    f"{result.confidence:.2f}",
                    _summarize(result),
                ),
            )

        self._summary_var.set(
            f"{len(self._visible_indices)} de {len(self._results)} pares exibidos"
        )

    def _parsed_min_confidence(self) -> float:
        """Le o campo 'Confianca minima (%)', tolerante a texto invalido
        (ex.: campo vazio enquanto o usuario ainda esta digitando)."""
        raw = self._min_confidence_var.get().strip().replace(",", ".")
        try:
            return max(0.0, min(100.0, float(raw))) / 100.0
        except ValueError:
            return 0.0

    def _open_detail(self) -> None:
        selection = self._tree.selection()
        if not selection:
            return
        result = self._results[int(selection[0])]
        _DetailDialog(self, result, on_review_status_changed=self._refresh)

    def _export(self) -> None:
        if not self._results:
            messagebox.showinfo("Exportar", "Nao ha resultados para exportar.")
            return

        # Exporta apenas os resultados atualmente visiveis (respeitando o
        # filtro de classificacao, a confianca minima e a busca), nao
        # todos os pares — assim a tabela e o arquivo exportado sempre
        # mostram exatamente o mesmo conjunto.
        results_to_export = [self._results[i] for i in self._visible_indices]
        if not results_to_export:
            messagebox.showinfo(
                "Exportar", "Nenhum resultado visivel com os filtros/busca atuais."
            )
            return

        if len(results_to_export) > 200_000:
            proceed = messagebox.askyesno(
                "Exportar muitos resultados",
                f"Ha {len(results_to_export)} pares visiveis — um volume muito grande para "
                "revisao manual em Excel. Considere aumentar a confianca minima ou filtrar "
                "por Classificacao antes de exportar.\n\nDeseja exportar mesmo assim?",
            )
            if not proceed:
                return

        output_path = filedialog.asksaveasfilename(
            title="Exportar resultados",
            defaultextension=".xlsx",
            filetypes=[("Planilhas Excel", "*.xlsx")],
        )
        if not output_path:
            return

        # min_confidence=None: a tabela ja aplicou o filtro de confianca
        # (self._visible_indices) de acordo com o campo da tela; nao
        # faz sentido o export_service filtrar de novo com o padrao de
        # 70% fixo, ignorando o valor que o usuario escolheu aqui.
        summary = export_results_to_excel(results_to_export, output_path, min_confidence=None)
        message = f"{summary.exported_count} resultados exportados para:\n{output_path}"
        if len(results_to_export) < len(self._results):
            message += (
                f"\n\n(Filtros aplicados: {len(self._results) - len(results_to_export)} "
                "pares nao visiveis nao foram exportados.)"
            )
        if len(summary.sheet_names) > 1:
            message += (
                f"\n\nO arquivo tem {len(summary.sheet_names)} planilhas "
                f"({', '.join(summary.sheet_names)}) porque o numero de pares ultrapassa o "
                "limite de linhas de uma unica planilha do Excel (1.048.576)."
            )
        messagebox.showinfo("Exportar", message)


def _summarize(result: ComparisonResult) -> str:
    if result.technical_differences:
        return result.technical_differences[0]
    if result.ambiguous_differences:
        return result.ambiguous_differences[0]
    if result.formatting_differences:
        return "apenas formatacao: " + ", ".join(result.formatting_differences[:2])
    return "identico"


class _DetailDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, result: ComparisonResult, on_review_status_changed) -> None:
        super().__init__(master)
        self.title(f"Detalhe: {result.code_a} x {result.code_b}")
        self._result = result
        self._on_review_status_changed = on_review_status_changed

        frame = ttk.Frame(self, padding=10)
        frame.pack(fill="both", expand=True)

        self._add_section(frame, f"MATERIAL A — Codigo: {result.code_a}", result.text_a)
        if result.short_description_a:
            self._add_section(frame, "Descricao curta (contexto, A)", result.short_description_a)
        self._add_section(frame, f"MATERIAL B — Codigo: {result.code_b}", result.text_b)
        if result.short_description_b:
            self._add_section(frame, "Descricao curta (contexto, B)", result.short_description_b)
        self._add_section(frame, "RESULTADO", result.classification)
        self._add_list_section(frame, "ELEMENTOS TECNICOS IGUAIS", result.equal_elements)
        self._add_list_section(frame, "DIFERENCAS DE FORMATACAO", result.formatting_differences)
        self._add_list_section(frame, "DIFERENCAS TECNICAS", result.technical_differences)
        self._add_list_section(frame, "TERMOS AMBIGUOS (REVISAO SUGERIDA)", result.ambiguous_differences)

        review_row = ttk.Frame(frame)
        review_row.pack(fill="x", pady=(8, 0))
        ttk.Label(review_row, text="Status de revisao:").pack(side="left")
        self._review_var = tk.StringVar(value=result.review_status)
        review_combo = ttk.Combobox(
            review_row, textvariable=self._review_var, state="readonly", values=_REVIEW_STATUSES
        )
        review_combo.pack(side="left", padx=4)
        review_combo.bind("<<ComboboxSelected>>", lambda _e: self._apply_review_status())

    def _add_section(self, parent: tk.Misc, title: str, text: str) -> None:
        ttk.Label(parent, text=title, font=("TkDefaultFont", 9, "bold")).pack(anchor="w", pady=(6, 0))
        ttk.Label(parent, text=text, wraplength=440, justify="left").pack(anchor="w")

    def _add_list_section(self, parent: tk.Misc, title: str, items: list[str]) -> None:
        ttk.Label(parent, text=title, font=("TkDefaultFont", 9, "bold")).pack(anchor="w", pady=(6, 0))
        text = ", ".join(items) if items else "nenhuma"
        ttk.Label(parent, text=text, wraplength=440, justify="left").pack(anchor="w")

    def _apply_review_status(self) -> None:
        self._result.review_status = self._review_var.get()
        self._on_review_status_changed()
