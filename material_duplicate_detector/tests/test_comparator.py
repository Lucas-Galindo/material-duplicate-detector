"""Testes do comparador tecnico (Sprint 6) — casos obrigatorios do escopo."""

from __future__ import annotations

import pytest

from app.core.comparator import compare
from app.core.technical_parser import parse_material
from app.models.material import Material
from app.rules.rule_loader import load_rules


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _parse(text: str, rules):
    return parse_material(Material(row_index=0, code="X", analysis_text=text), rules)


def _compare(text_a: str, text_b: str, rules):
    return compare(_parse(text_a, rules), _parse(text_b, rules), rules)


def test_glued_vs_spaced_is_equivalent_no_technical_difference(rules):
    outcome = _compare("PARAFUSO 20 CM X 1/2 MM", "PARAFUSO 20CMX1/2MM", rules)
    assert not outcome.has_technical_difference
    assert outcome.formatting_differences  # houve diferenca de formatacao
    assert "PARAFUSO" in outcome.equal_elements


def test_protected_symbol_creates_technical_difference(rules):
    outcome = _compare('CANO 1/2"', "CANO 1/2", rules)
    assert outcome.has_technical_difference
    assert any("simbolo tecnico" in diff for diff in outcome.technical_differences)


def test_m10_vs_m12_is_technical_difference(rules):
    outcome = _compare("PARAFUSO M10", "PARAFUSO M12", rules)
    assert outcome.has_technical_difference


def test_diant_equivalent_to_dianteiro_no_difference(rules):
    outcome = _compare("SUPORTE DIANT", "SUPORTE DIANTEIRO", rules)
    assert not outcome.has_technical_difference
    assert "DIANTEIRO" in outcome.equal_elements


def test_dianteiro_vs_traseiro_is_technical_difference(rules):
    outcome = _compare("SUPORTE DIANTEIRO", "SUPORTE TRASEIRO", rules)
    assert outcome.has_technical_difference
    assert any("DIANTEIRO x TRASEIRO" in diff or "TRASEIRO x DIANTEIRO" in diff for diff in outcome.technical_differences)


def test_masculino_vs_feminino_is_technical_difference(rules):
    outcome = _compare("CONECTOR MASCULINO", "CONECTOR FEMININO", rules)
    assert outcome.has_technical_difference


def test_azul_vs_preto_is_technical_difference(rules):
    outcome = _compare("TAMPA AZUL", "TAMPA PRETO", rules)
    assert outcome.has_technical_difference


def test_reordered_terms_reported_as_formatting_difference(rules):
    outcome = _compare("PARAFUSO INOX M10 X 20", "PARAFUSO M10 X 20 INOX", rules)
    assert not outcome.has_technical_difference
    assert outcome.order_differs_only
    assert "ordem dos elementos" in outcome.formatting_differences


def test_unknown_extra_word_is_ambiguous_not_technical(rules):
    outcome = _compare("PARAFUSO INOX REFORCADO", "PARAFUSO INOX", rules)
    assert not outcome.has_technical_difference
    assert outcome.ambiguous
    assert outcome.ambiguous_differences


def test_identical_text_has_no_differences(rules):
    outcome = _compare("PARAFUSO INOX M10", "PARAFUSO INOX M10", rules)
    assert not outcome.has_technical_difference
    assert not outcome.formatting_differences
    assert not outcome.order_differs_only
