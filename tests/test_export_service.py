"""Testes de exportacao de resultados para Excel (Sprint 9 + filtro de
confianca minima e correcoes de perda de dados)."""

from __future__ import annotations

import openpyxl
import pandas as pd

from app.models.comparison_result import ComparisonResult
from app.services.export_service import export_results_to_excel


def test_export_results_to_excel(tmp_path):
    results = [
        ComparisonResult(
            code_a="5000000001",
            code_b="5000000002",
            text_a="PARAFUSO 20 CM X 1/2 MM",
            text_b="PARAFUSO 20CMX1/2MM",
            classification="DUPLICADO_CONFIRMADO",
            confidence=0.95,
            equal_elements=["PARAFUSO"],
            formatting_differences=["espacos"],
            technical_differences=[],
            ambiguous_differences=[],
        ),
        ComparisonResult(
            code_a="5000000003",
            code_b="5000000004",
            text_a="PARAFUSO M10",
            text_b="PARAFUSO M12",
            classification="SEMELHANTE_DIFERENTE",
            confidence=0.9,
            equal_elements=["PARAFUSO"],
            formatting_differences=[],
            technical_differences=["codigos tecnicos exclusivos: A=['M10'] B=['M12']"],
            ambiguous_differences=[],
        ),
    ]
    output_path = tmp_path / "resultados.xlsx"

    summary = export_results_to_excel(results, output_path)

    assert output_path.exists()
    assert summary.sheet_names == ["Resultados"]
    assert summary.exported_count == 2
    assert summary.filtered_out_by_confidence == 0
    df = pd.read_excel(output_path, engine="openpyxl", dtype=str)
    assert list(df["Codigo A"]) == ["5000000001", "5000000003"]
    assert list(df["Classificacao"]) == ["DUPLICADO_CONFIRMADO", "SEMELHANTE_DIFERENTE"]
    assert df.loc[0, "Elementos Tecnicos Iguais"] == "PARAFUSO"


def test_export_empty_results(tmp_path):
    output_path = tmp_path / "vazio.xlsx"
    summary = export_results_to_excel([], output_path)
    assert summary.sheet_names == ["Resultados"]
    assert summary.exported_count == 0
    df = pd.read_excel(output_path, engine="openpyxl")
    assert df.empty


def test_export_includes_short_description_columns_for_context_only(tmp_path):
    results = [
        ComparisonResult(
            code_a="1", code_b="2", text_a="PARAFUSO A", text_b="PARAFUSO B",
            classification="DUPLICADO_CONFIRMADO", confidence=0.95,
            short_description_a="Parafuso sextavado zincado",
            short_description_b="Parafuso p/ estrutura metalica",
        ),
    ]
    output_path = tmp_path / "com_descricao.xlsx"

    summary = export_results_to_excel(results, output_path)
    assert summary.exported_count == 1

    df = pd.read_excel(output_path, engine="openpyxl", dtype=str)
    assert "Descricao Curta A" in df.columns
    assert "Descricao Curta B" in df.columns
    assert df.loc[0, "Descricao Curta A"] == "Parafuso sextavado zincado"
    assert df.loc[0, "Descricao Curta B"] == "Parafuso p/ estrutura metalica"


def test_export_filters_out_results_below_70_percent_confidence_by_default(tmp_path):
    # Requisito obrigatorio: o arquivo final so pode conter pares com
    # confianca >= 70%. Por padrao (sem passar min_confidence), pares
    # abaixo disso nunca devem chegar a ser escritos no arquivo.
    results = [
        ComparisonResult(
            code_a="1", code_b="2", text_a="A", text_b="B",
            classification="DUPLICADO_CONFIRMADO", confidence=0.95,
        ),
        ComparisonResult(
            code_a="3", code_b="4", text_a="A", text_b="B",
            classification="PROVAVEL_DUPLICADO", confidence=0.70,  # limite: entra
        ),
        ComparisonResult(
            code_a="5", code_b="6", text_a="A", text_b="B",
            classification="SEMELHANTE_DIFERENTE", confidence=0.69,  # abaixo: fora
        ),
        ComparisonResult(
            code_a="7", code_b="8", text_a="A", text_b="B",
            classification="SEMELHANTE_DIFERENTE", confidence=0.10,
        ),
    ]
    output_path = tmp_path / "resultados_filtrados.xlsx"

    summary = export_results_to_excel(results, output_path)

    assert summary.exported_count == 2
    assert summary.filtered_out_by_confidence == 2
    df = pd.read_excel(output_path, engine="openpyxl", dtype=str)
    assert list(df["Codigo A"]) == ["1", "3"]
    assert all(float(c) >= 0.70 for c in df["Confianca"])


def test_export_min_confidence_none_disables_filter(tmp_path):
    results = [
        ComparisonResult(
            code_a=str(i), code_b=str(i + 1), text_a="A", text_b="B",
            classification="SEMELHANTE_DIFERENTE", confidence=0.1,
        )
        for i in range(5)
    ]
    output_path = tmp_path / "sem_filtro.xlsx"

    summary = export_results_to_excel(results, output_path, min_confidence=None)

    assert summary.exported_count == 5
    assert summary.filtered_out_by_confidence == 0


def test_export_splits_across_multiple_sheets_when_exceeding_row_limit(tmp_path):
    # Regressao: planilhas reais com muitos candidatos podem gerar mais
    # resultados do que uma unica planilha do Excel suporta (limite real:
    # 1.048.576 linhas). Antes da correcao, pandas.to_excel lancava
    # ValueError ("This sheet is too large!") e a exportacao falhava por
    # completo. Usa um limite pequeno via `max_rows_per_sheet` para nao
    # precisar gerar milhoes de linhas neste teste. min_confidence=None
    # porque o foco aqui e a divisao em planilhas, nao o filtro de score.
    results = [
        ComparisonResult(
            code_a=str(i),
            code_b=str(i + 1),
            text_a="PARAFUSO A",
            text_b="PARAFUSO B",
            classification="SEMELHANTE_DIFERENTE",
            confidence=0.5,
        )
        for i in range(25)
    ]
    output_path = tmp_path / "resultados_grandes.xlsx"

    summary = export_results_to_excel(
        results, output_path, min_confidence=None, max_rows_per_sheet=10
    )

    # 10 linhas por planilha, 1 delas e o cabecalho -> 9 linhas de dados
    # por planilha; 25 resultados / 9 = 3 planilhas.
    assert summary.sheet_names == ["Resultados", "Resultados_2", "Resultados_3"]
    assert summary.exported_count == 25

    total_rows = 0
    for sheet_name in summary.sheet_names:
        df = pd.read_excel(output_path, sheet_name=sheet_name, engine="openpyxl", dtype=str)
        assert len(df) <= 9
        total_rows += len(df)
    assert total_rows == 25


def test_export_large_volume_streams_without_loading_everything_in_memory(tmp_path):
    # Regressao: exportar centenas de milhares de pares causava
    # MemoryError porque pandas/openpyxl (modo normal) mantem toda
    # celula como objeto Python em memoria antes de escrever. Usa modo
    # "write_only" do openpyxl (streaming). 50.000 e grande o suficiente
    # para exercitar o caminho de escrita real sem deixar o teste lento
    # (o volume de milhoes de linhas foi validado manualmente).
    # min_confidence=None porque o foco aqui e volume/streaming, nao o
    # filtro de score (results e um gerador, entao nao tem len() — o
    # teste abaixo confere que isso nao quebra o resumo retornado).
    results = (
        ComparisonResult(
            code_a=str(i),
            code_b=str(i + 1),
            text_a="PARAFUSO A",
            text_b="PARAFUSO B",
            classification="SEMELHANTE_DIFERENTE",
            confidence=0.5,
        )
        for i in range(50_000)
    )
    output_path = tmp_path / "resultados_volume.xlsx"

    summary = export_results_to_excel(results, output_path, min_confidence=None)
    assert summary.sheet_names == ["Resultados"]
    assert summary.exported_count == 50_000

    workbook = openpyxl.load_workbook(output_path, read_only=True)
    worksheet = workbook["Resultados"]
    row_count = sum(1 for _ in worksheet.iter_rows())
    assert row_count == 50_001  # +1 do cabecalho
    workbook.close()


def test_export_truncates_extremely_long_cell_content(tmp_path):
    # Guarda de seguranca: uma unica celula acima de 32.767 caracteres
    # (limite do Excel) faz o openpyxl falhar ao salvar. Em vez de
    # derrubar a exportacao inteira por causa de um campo de texto
    # anormalmente longo, o conteudo e truncado com um aviso visivel.
    huge_text = "X" * 40_000
    results = [
        ComparisonResult(
            code_a="1", code_b="2", text_a=huge_text, text_b="B",
            classification="DUPLICADO_CONFIRMADO", confidence=1.0,
        )
    ]
    output_path = tmp_path / "texto_longo.xlsx"

    summary = export_results_to_excel(results, output_path)
    assert summary.exported_count == 1

    df = pd.read_excel(output_path, engine="openpyxl", dtype=str)
    assert len(df.loc[0, "Texto A"]) <= 32_767
    assert "TRUNCADO" in df.loc[0, "Texto A"]
