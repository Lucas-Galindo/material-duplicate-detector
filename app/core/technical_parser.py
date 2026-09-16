"""Monta o ``ParsedMaterial`` com todas as representacoes do texto
(Sprint 3/4), combinando normalizer + tokenizer + regras.
"""

from __future__ import annotations

from app.core.normalizer import normalize
from app.core.tokenizer import (
    extract_numbers,
    extract_symbols,
    extract_units,
    extract_words,
    tokenize,
)
from app.models.material import Material
from app.models.parsed_material import ParsedMaterial
from app.rules.rule_loader import RuleSet


def parse_material(material: Material, rules: RuleSet) -> ParsedMaterial:
    """Gera todas as representacoes do texto de ``material``.

    O texto original nunca e alterado — cada representacao e um campo
    adicional em ``ParsedMaterial``.
    """
    normalization = normalize(material.analysis_text)
    tokens = tokenize(normalization.normalized_text)

    raw_tokens = [t.value for t in tokens]
    technical_tokens = extract_words(tokens)
    numbers = extract_numbers(tokens)
    units = extract_units(tokens)
    symbols = extract_symbols(tokens)
    normalized_terms = [rules.canonical_term(term) for term in technical_tokens]

    critical_tokens = [
        term
        for term in normalized_terms
        if any(term in group for group in rules.incompatible_groups)
    ]

    return ParsedMaterial(
        material=material,
        original_text=normalization.original_text,
        normalized_text=normalization.normalized_text,
        applied_transformations=normalization.applied_transformations,
        raw_tokens=raw_tokens,
        technical_tokens=technical_tokens,
        critical_tokens=critical_tokens,
        numbers=numbers,
        units=units,
        symbols=symbols,
        normalized_terms=normalized_terms,
    )


def parse_materials(materials: list[Material], rules: RuleSet) -> list[ParsedMaterial]:
    return [parse_material(m, rules) for m in materials]
