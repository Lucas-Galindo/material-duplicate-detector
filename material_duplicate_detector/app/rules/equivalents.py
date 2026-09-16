"""Fachada para consulta de grupos de equivalencia (Sprint 4)."""

from __future__ import annotations

from app.rules.rule_loader import RuleSet


def are_equivalent(term_a: str, term_b: str, rules: RuleSet) -> bool:
    """True se ``term_a`` e ``term_b`` representam o mesmo conceito
    (mesmo termo canonico), ex.: DIANT e DIANTEIRO."""
    return rules.canonical_term(term_a) == rules.canonical_term(term_b)
