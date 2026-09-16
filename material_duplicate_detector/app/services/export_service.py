"""Exportacao dos resultados para Excel (Sprint 9).

Escreve com ``openpyxl`` no modo ``write_only`` (streaming): cada linha
e serializada e descartada da memoria assim que e escrita, em vez de
manter todas as celulas da planilha como objetos Python (o que e o que
``pandas.DataFrame.to_excel``/``openpyxl`` no modo normal fazem, e o
que causava ``MemoryError`` ao exportar centenas de milhares de pares).

Aplica tambem o filtro de confianca minima (``min_confidence``, padrao
0.70 = 70%) exigido para o arquivo final: pares abaixo do limite nunca
chegam a ser escritos.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from openpyxl import Workbook

from app.models.comparison_result import ComparisonResult

_COLUMNS = [
    "Codigo A",
    "Codigo B",
    "Texto A",
    "Texto B",
    # Puramente informativas (contexto): NUNCA entram no calculo de
    # Confianca/Classificacao, que considera so os campos de "Dados
    # Basicos" (Texto A/Texto B) acima. Ver Material.short_description.
    "Descricao Curta A",
    "Descricao Curta B",
    "Classificacao",
    "Confianca",
    "Elementos Tecnicos Iguais",
    "Diferencas de Formatacao",
    "Diferencas Tecnicas",
    "Termos Ambiguos",
    "Status de Revisao",
    "Observacao",
]

# Limite real do Excel (.xlsx): 1.048.576 linhas por planilha, contando
# o cabecalho. Quando o numero de resultados ultrapassa isso, os dados
# sao divididos em varias planilhas dentro do mesmo arquivo.
_EXCEL_MAX_ROWS_PER_SHEET = 1_048_576

# Limite real do Excel para o conteudo de uma unica celula de texto.
# Uma celula acima disso faz o proprio openpyxl levantar erro ao salvar
# (outra forma de "perda"/falha silenciosa em textos muito longos,
# incomum mas possivel em campos de observacao/diferencas extensos).
_EXCEL_MAX_CELL_LENGTH = 32_767

# Filtro obrigatorio do arquivo final: so pares com confianca >= 70%.
DEFAULT_MIN_CONFIDENCE = 0.70


@dataclass(frozen=True)
class ExportSummary:
    sheet_names: list[str]
    total_input: int
    exported_count: int
    filtered_out_by_confidence: int


def export_results_to_excel(
    results: list[ComparisonResult],
    output_path: str | Path,
    min_confidence: float | None = DEFAULT_MIN_CONFIDENCE,
    max_rows_per_sheet: int = _EXCEL_MAX_ROWS_PER_SHEET,
) -> ExportSummary:
    """Exporta ``results`` para ``output_path`` em modo streaming.

    - Filtra por ``min_confidence`` (padrao 0.70 = 70%) antes de
      escrever: pares abaixo do limite nao entram no arquivo. Passe
      ``None`` para exportar tudo sem esse filtro.
    - Se o total apos o filtro ultrapassar o limite de linhas de uma
      planilha do Excel, os dados sao divididos automaticamente em
      varias planilhas ("Resultados", "Resultados_2", ...) dentro do
      mesmo arquivo, em vez de falhar.
    - Celulas de texto muito longas (> 32.767 caracteres, o limite do
      proprio Excel) sao truncadas com um aviso, em vez de derrubar a
      exportacao inteira por causa de um unico campo extenso.

    Retorna um ``ExportSummary`` com quantos pares entraram, quantos
    foram cortados pelo filtro de confianca e em quais planilhas.
    """
    total_input = len(results) if hasattr(results, "__len__") else None

    if min_confidence is not None:
        filtered_results = (r for r in results if r.confidence >= min_confidence)
    else:
        filtered_results = iter(results)

    max_data_rows = max(1, max_rows_per_sheet - 1)  # a linha 1 e o cabecalho

    workbook = Workbook(write_only=True)
    sheet_names: list[str] = []

    def start_sheet():
        sheet_index = len(sheet_names) + 1
        name = "Resultados" if sheet_index == 1 else f"Resultados_{sheet_index}"
        sheet_names.append(name)
        worksheet = workbook.create_sheet(title=name)
        worksheet.append(_COLUMNS)
        return worksheet

    current_sheet = start_sheet()
    rows_in_current_sheet = 0
    exported_count = 0
    for result in filtered_results:
        if rows_in_current_sheet >= max_data_rows:
            current_sheet = start_sheet()
            rows_in_current_sheet = 0
        current_sheet.append(_result_to_row(result))
        rows_in_current_sheet += 1
        exported_count += 1

    workbook.save(output_path)

    filtered_out = (total_input - exported_count) if total_input is not None else 0
    return ExportSummary(
        sheet_names=sheet_names,
        total_input=total_input if total_input is not None else exported_count,
        exported_count=exported_count,
        filtered_out_by_confidence=filtered_out,
    )


def _result_to_row(r: ComparisonResult) -> list:
    return [
        r.code_a,
        r.code_b,
        _truncate_for_excel(r.text_a),
        _truncate_for_excel(r.text_b),
        _truncate_for_excel(r.short_description_a),
        _truncate_for_excel(r.short_description_b),
        r.classification,
        r.confidence,
        _truncate_for_excel("; ".join(r.equal_elements)),
        _truncate_for_excel("; ".join(r.formatting_differences)),
        _truncate_for_excel("; ".join(r.technical_differences)),
        _truncate_for_excel("; ".join(r.ambiguous_differences)),
        r.review_status,
        _truncate_for_excel(r.observation),
    ]


def _truncate_for_excel(value: str) -> str:
    if len(value) <= _EXCEL_MAX_CELL_LENGTH:
        return value
    suffix = " [...TRUNCADO...]"
    return value[: _EXCEL_MAX_CELL_LENGTH - len(suffix)] + suffix
