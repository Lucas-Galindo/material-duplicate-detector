"""Fachada para consulta de termos tecnicos incompativeis (Sprint 4)."""

from __future__ import annotations

from app.rules.rule_loader import RuleSet


def are_incompatible(term_a: str, term_b: str, rules: RuleSet) -> bool:
    """True se ``term_a`` e ``term_b`` sao mutuamente exclusivos (ex.:
    DIANTEIRO vs TRASEIRO, MASCULINO vs FEMININO, AZUL vs PRETO)."""
    return rules.are_incompatible(term_a, term_b)


def find_incompatible_terms(terms_a: list[str], terms_b: list[str], rules: RuleSet) -> list[tuple[str, str]]:
    """Retorna todos os pares (termo_a, termo_b) mutuamente incompativeis
    encontrados entre as duas listas de termos."""
    pairs: list[tuple[str, str]] = []
    for term_a in terms_a:
        for term_b in terms_b:
            if rules.are_incompatible(term_a, term_b):
                pairs.append((term_a.upper(), term_b.upper()))
    return pairs
