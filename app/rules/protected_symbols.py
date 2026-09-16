"""Fachada para consulta de simbolos tecnicos protegidos (Sprint 4)."""

from __future__ import annotations

from app.rules.rule_loader import RuleSet


def is_protected(symbol: str, rules: RuleSet) -> bool:
    """True se ``symbol`` carrega significado tecnico e nao pode ser
    ignorado em uma comparacao (ex.: a polegada em 1/2")."""
    return rules.is_protected_symbol(symbol)
