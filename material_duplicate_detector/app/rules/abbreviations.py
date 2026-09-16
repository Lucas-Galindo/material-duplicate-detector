"""Fachada para consulta de abreviacoes (Sprint 4).

Reexporta a operacao de normalizacao de termos a partir do ``RuleSet``
carregado por ``rule_loader``, mantendo a estrutura modular prevista na
arquitetura (um arquivo por dominio de regra).
"""

from __future__ import annotations

from app.rules.rule_loader import RuleSet


def canonical_term(term: str, rules: RuleSet) -> str:
    """Aplica abreviacoes/equivalencias, retornando o termo canonico."""
    return rules.canonical_term(term)


def normalize_terms(terms: list[str], rules: RuleSet) -> list[str]:
    """Aplica ``canonical_term`` a uma lista de termos, preservando a ordem."""
    return [rules.canonical_term(term) for term in terms]
