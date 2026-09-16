"""Geracao das multiplas assinaturas tecnicas (Sprint 5).

Cada assinatura oferece uma forma diferente de agrupar/localizar
candidatos; nenhuma delas, isoladamente, decide duplicidade — isso e
papel do comparador (Sprint 6) e do classificador (Sprint 7).
"""

from __future__ import annotations

from app.core.tokenizer import numeric_value
from app.models.parsed_material import ParsedMaterial
from app.models.technical_signature import TechnicalSignature


def build_signature(parsed: ParsedMaterial) -> TechnicalSignature:
    numeric_values = [_format_number(n) for n in parsed.numbers]
    units_sorted = sorted(parsed.units)
    critical_sorted = sorted(set(parsed.critical_tokens))

    ordered_terms = parsed.normalized_terms + numeric_values + parsed.units
    unordered_terms = frozenset(parsed.normalized_terms) | frozenset(numeric_values) | frozenset(parsed.units)

    return TechnicalSignature(
        normalized_signature=parsed.normalized_text,
        token_signature=" ".join(parsed.raw_tokens),
        numeric_signature=",".join(numeric_values),
        unit_signature=",".join(units_sorted),
        critical_terms_signature=",".join(critical_sorted),
        ordered_signature=" ".join(ordered_terms),
        unordered_signature=unordered_terms,
    )


def _format_number(token_value: str) -> str:
    """Normaliza o valor numerico para comparacao (1/2 e 0.5 -> '0.5')."""
    value = numeric_value(token_value)
    if value == int(value):
        return str(int(value))
    return f"{value:g}"
