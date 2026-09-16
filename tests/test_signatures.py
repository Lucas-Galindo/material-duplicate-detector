"""Testes de parsing e assinaturas tecnicas (Sprint 5)."""

from __future__ import annotations

import pytest

from app.core.signature_builder import build_signature
from app.core.technical_parser import parse_material
from app.models.material import Material
from app.rules.rule_loader import load_rules


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _parse(text: str, rules):
    material = Material(row_index=0, code="X", analysis_text=text)
    return parse_material(material, rules)


def test_parse_material_preserves_original_text(rules):
    parsed = _parse("  parafuso 20cmX1/2mm  ", rules)
    assert parsed.original_text == "  parafuso 20cmX1/2mm  "
    assert parsed.normalized_text == "PARAFUSO 20 CM X 1/2 MM"


def test_parse_material_fills_all_representations(rules):
    parsed = _parse("PARAFUSO DIANT M10", rules)
    assert "PARAFUSO" in parsed.technical_tokens
    assert "M10" in parsed.technical_tokens
    assert parsed.normalized_terms == ["PARAFUSO", "DIANTEIRO", "M10"]
    assert parsed.critical_tokens == ["DIANTEIRO"]


def test_glued_and_spaced_texts_have_same_ordered_signature(rules):
    a = build_signature(_parse("PARAFUSO 20 CM X 1/2 MM", rules))
    b = build_signature(_parse("PARAFUSO 20CMX1/2MM", rules))
    assert a.ordered_signature == b.ordered_signature
    assert a.unordered_signature == b.unordered_signature
    assert a.numeric_signature == b.numeric_signature
    assert a.unit_signature == b.unit_signature


def test_reordered_terms_share_unordered_signature_but_not_ordered(rules):
    a = build_signature(_parse("PARAFUSO INOX M10 X 20", rules))
    b = build_signature(_parse("PARAFUSO M10 X 20 INOX", rules))
    assert a.unordered_signature == b.unordered_signature
    assert a.ordered_signature != b.ordered_signature


def test_fraction_and_decimal_share_numeric_signature(rules):
    a = build_signature(_parse("PARAFUSO 1/2 MM", rules))
    b = build_signature(_parse("PARAFUSO 0.5 MM", rules))
    assert a.numeric_signature == b.numeric_signature == "0.5"


def test_build_signature_does_not_crash_on_zero_denominator_gauge(rules):
    # Regressao: texto real com bitola de cabo ("1/0 AWG") derrubava a
    # analise inteira com ZeroDivisionError ao montar a assinatura numerica.
    signature_a = build_signature(_parse("CABO 1/0 AWG", rules))
    signature_b = build_signature(_parse("CABO 2/0 AWG", rules))
    assert signature_a.numeric_signature == "1"
    assert signature_b.numeric_signature == "2"
    assert signature_a.numeric_signature != signature_b.numeric_signature


def test_m10_and_m12_have_different_signatures(rules):
    a = build_signature(_parse("PARAFUSO M10", rules))
    b = build_signature(_parse("PARAFUSO M12", rules))
    assert a.unordered_signature != b.unordered_signature
    assert a.ordered_signature != b.ordered_signature
