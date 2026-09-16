"""Testes de importacao de Excel (Sprint 1)."""

from __future__ import annotations

import pandas as pd
import pytest

from app.services.excel_service import (
    ColumnNotFoundError,
    ExcelFileError,
    find_short_description_column,
    list_columns,
    list_sheet_names,
    load_materials,
)


@pytest.fixture
def sample_xlsx(tmp_path):
    path = tmp_path / "materiais.xlsx"
    df = pd.DataFrame(
        {
            "Codigo Material": ["5000000001", "5000000002", "5000000003", ""],
            "Texto Dados Basicos": [
                "PARAFUSO 20 CM X 1/2 MM",
                "PARAFUSO 20CMX1/2MM",
                None,
                "SEM CODIGO",
            ],
        }
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Data", index=False)
        df.head(1).to_excel(writer, sheet_name="Resumo", index=False)
    return path


def test_list_sheet_names(sample_xlsx):
    assert list_sheet_names(sample_xlsx) == ["Data", "Resumo"]


def test_list_columns(sample_xlsx):
    assert list_columns(sample_xlsx, "Data") == ["Codigo Material", "Texto Dados Basicos"]


def test_load_materials_skips_empty_analysis_text(sample_xlsx):
    materials = load_materials(sample_xlsx, "Data", "Codigo Material", "Texto Dados Basicos")
    assert len(materials) == 3
    assert materials[0].code == "5000000001"
    assert materials[0].analysis_text == "PARAFUSO 20 CM X 1/2 MM"
    assert materials[2].code == ""
    assert materials[2].analysis_text == "SEM CODIGO"


def test_load_materials_missing_column_raises(sample_xlsx):
    with pytest.raises(ColumnNotFoundError):
        load_materials(sample_xlsx, "Data", "Codigo Inexistente", "Texto Dados Basicos")


def test_file_not_found_raises():
    with pytest.raises(ExcelFileError):
        list_sheet_names("nao_existe.xlsx")


def test_invalid_extension_raises(tmp_path):
    bad = tmp_path / "materiais.txt"
    bad.write_text("nao e um excel")
    with pytest.raises(ExcelFileError):
        list_sheet_names(bad)


def test_corrupted_file_raises(tmp_path):
    bad = tmp_path / "materiais.xlsx"
    bad.write_bytes(b"isto nao e um arquivo xlsx valido")
    with pytest.raises(ExcelFileError):
        list_sheet_names(bad)


@pytest.mark.parametrize(
    "column_name",
    ["Descrição Curta", "Descricao Curta", "DESCRICAO CURTA", "  descricao   curta  "],
)
def test_find_short_description_column_accepts_variations(column_name):
    columns = ["Codigo", "Texto Dados Basicos", column_name]
    assert find_short_description_column(columns) == column_name


def test_find_short_description_column_returns_none_when_absent():
    assert find_short_description_column(["Codigo", "Texto Dados Basicos"]) is None


def test_find_short_description_column_does_not_match_unrelated_description():
    # Uma coluna de descricao "longa"/generica nao deve ser confundida
    # com a "Descricao Curta" especificamente.
    assert find_short_description_column(["Codigo", "Descricao Detalhada"]) is None


@pytest.fixture
def sample_xlsx_with_short_description(tmp_path):
    path = tmp_path / "materiais_com_descricao.xlsx"
    df = pd.DataFrame(
        {
            "Codigo Material": ["1", "2"],
            "Texto Dados Basicos": ["PARAFUSO 20 CM X 1/2 MM", "PARAFUSO 20CMX1/2MM"],
            "Descrição Curta": ["Parafuso sextavado zincado", "Parafuso p/ estrutura metalica"],
        }
    )
    df.to_excel(path, sheet_name="Data", index=False, engine="openpyxl")
    return path


def test_load_materials_auto_detects_short_description_column(sample_xlsx_with_short_description):
    materials = load_materials(
        sample_xlsx_with_short_description, "Data", "Codigo Material", "Texto Dados Basicos"
    )
    assert materials[0].short_description == "Parafuso sextavado zincado"
    assert materials[1].short_description == "Parafuso p/ estrutura metalica"
    # E continua sendo um campo puramente informativo: nao altera o
    # texto usado para analise.
    assert materials[0].analysis_text == "PARAFUSO 20 CM X 1/2 MM"


def test_load_materials_without_short_description_column_defaults_to_empty(sample_xlsx):
    materials = load_materials(sample_xlsx, "Data", "Codigo Material", "Texto Dados Basicos")
    assert all(m.short_description == "" for m in materials)


def test_load_materials_explicit_short_description_column_override(sample_xlsx_with_short_description):
    materials = load_materials(
        sample_xlsx_with_short_description,
        "Data",
        "Codigo Material",
        "Texto Dados Basicos",
        short_description_column="Descrição Curta",
    )
    assert materials[0].short_description == "Parafuso sextavado zincado"


def test_load_materials_invalid_short_description_column_raises(sample_xlsx):
    with pytest.raises(ColumnNotFoundError):
        load_materials(
            sample_xlsx,
            "Data",
            "Codigo Material",
            "Texto Dados Basicos",
            short_description_column="Coluna Inexistente",
        )
