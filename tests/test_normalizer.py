"""Testes de normalizacao segura (Sprint 2)."""

from __future__ import annotations

import pytest

from app.core.normalizer import normalize


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("  parafuso   inox  ", "PARAFUSO INOX"),
        ("Parafuso Ação", "PARAFUSO ACAO"),
        ("20CMX1/2MM", "20 CM X 1/2 MM"),
        ("20 CM X 1/2 MM", "20 CM X 1/2 MM"),
        ("PARAFUSO 20CMX1/2MM INOX", "PARAFUSO 20 CM X 1/2 MM INOX"),
    ],
)
def test_normalize_examples(raw, expected):
    assert normalize(raw).normalized_text == expected


def test_normalize_does_not_split_technical_codes():
    # M10/M12 sao codigos tecnicos: letra seguida de numero deve
    # permanecer colada (nao pode virar "M 10").
    assert normalize("PARAFUSO M10").normalized_text == "PARAFUSO M10"
    assert normalize("PARAFUSO M12").normalized_text == "PARAFUSO M12"


def test_normalize_preserves_original_text():
    result = normalize("  parafuso 20cmX1/2mm  ")
    assert result.original_text == "  parafuso 20cmX1/2mm  "
    assert result.normalized_text != result.original_text


def test_normalize_reports_applied_transformations():
    result = normalize("  parafuso 20cmX1/2mm  ")
    assert "espacos_nas_bordas" in result.applied_transformations
    assert "maiusculizacao" in result.applied_transformations
    assert "separacao_numero_letra" in result.applied_transformations
    assert "separacao_de_x_dimensional" in result.applied_transformations


def test_normalize_equivalence_case_from_spec():
    a = normalize("PARAFUSO 20 CM X 1/2 MM")
    b = normalize("PARAFUSO 20CMX1/2MM")
    assert a.normalized_text == b.normalized_text


def test_normalize_empty_string():
    result = normalize("")
    assert result.normalized_text == ""
    assert result.applied_transformations == []
