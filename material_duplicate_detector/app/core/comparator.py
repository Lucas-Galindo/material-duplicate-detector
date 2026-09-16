"""Comparador tecnico profundo e explicavel (Sprint 6).

Nunca decide duplicidade sozinho: produz uma comparacao estruturada por
categoria (termos, numeros, unidades, simbolos, ordem) que o classificador
(Sprint 7) usa para decidir a classificacao final. A similaridade textual
e calculada apenas como sinal auxiliar (``textual_similarity``), nunca
como criterio de decisao.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from app.models.parsed_material import ParsedMaterial
from app.rules.rule_loader import RuleSet

_CODE_LIKE_TERM = re.compile(r"^[A-ZÀ-Ú]+\d+[A-Z0-9]*$")

_FORMATTING_LABELS: dict[str, str] = {
    "espacos_nas_bordas": "espacos nas bordas",
    "maiusculizacao": "uso de maiusculas/minusculas",
    "normalizacao_de_acentos": "acentuacao",
    "separacao_numero_letra": "agrupamento dos caracteres (numero colado a unidade)",
    "separacao_de_x_dimensional": "utilizacao do X como separador dimensional",
    "colapso_de_espacos": "espacos multiplos",
}


@dataclass(frozen=True)
class ComparisonOutcome:
    material_a: ParsedMaterial
    material_b: ParsedMaterial
    equal_elements: list[str] = field(default_factory=list)
    formatting_differences: list[str] = field(default_factory=list)
    technical_differences: list[str] = field(default_factory=list)
    ambiguous_differences: list[str] = field(default_factory=list)
    order_differs_only: bool = False
    ambiguous: bool = False
    textual_similarity: float = 0.0

    @property
    def has_technical_difference(self) -> bool:
        return len(self.technical_differences) > 0


def compare(parsed_a: ParsedMaterial, parsed_b: ParsedMaterial, rules: RuleSet) -> ComparisonOutcome:
    equal_elements: list[str] = []
    technical_differences: list[str] = []
    ambiguous_differences: list[str] = []

    terms_a = set(parsed_a.normalized_terms)
    terms_b = set(parsed_b.normalized_terms)
    equal_elements.extend(sorted(terms_a & terms_b))

    only_a = terms_a - terms_b
    only_b = terms_b - terms_a
    _compare_term_sets(only_a, only_b, rules, technical_differences, ambiguous_differences)

    numbers_a = {_number_key(n) for n in parsed_a.numbers}
    numbers_b = {_number_key(n) for n in parsed_b.numbers}
    if numbers_a != numbers_b:
        only_numbers_a = sorted(numbers_a - numbers_b)
        only_numbers_b = sorted(numbers_b - numbers_a)
        if only_numbers_a or only_numbers_b:
            technical_differences.append(
                f"numeros divergentes: A={only_numbers_a or '-'} B={only_numbers_b or '-'}"
            )

    units_a = set(parsed_a.units)
    units_b = set(parsed_b.units)
    if units_a != units_b:
        technical_differences.append(
            f"unidades divergentes: A={sorted(units_a - units_b) or '-'} "
            f"B={sorted(units_b - units_a) or '-'}"
        )

    symbols_a = set(parsed_a.symbols)
    symbols_b = set(parsed_b.symbols)
    formatting_differences: list[str] = []
    for symbol in symbols_a ^ symbols_b:
        if rules.is_protected_symbol(symbol):
            side = "A" if symbol in symbols_a else "B"
            technical_differences.append(
                f"simbolo tecnico presente apenas em {side}: '{symbol}'"
            )
        else:
            formatting_differences.append(f"simbolo de formatacao: '{symbol}'")

    formatting_transformations = set(parsed_a.applied_transformations) | set(
        parsed_b.applied_transformations
    )
    for key in sorted(formatting_transformations):
        formatting_differences.append(_FORMATTING_LABELS.get(key, key))

    order_differs_only = False
    if not technical_differences and terms_a == terms_b:
        ordered_a = [t for t in parsed_a.normalized_terms]
        ordered_b = [t for t in parsed_b.normalized_terms]
        if ordered_a != ordered_b:
            order_differs_only = True
            formatting_differences.append("ordem dos elementos")

    similarity = SequenceMatcher(None, parsed_a.normalized_text, parsed_b.normalized_text).ratio()

    ambiguous = bool(ambiguous_differences) and not technical_differences

    return ComparisonOutcome(
        material_a=parsed_a,
        material_b=parsed_b,
        equal_elements=equal_elements,
        formatting_differences=sorted(set(formatting_differences)),
        technical_differences=technical_differences,
        ambiguous_differences=ambiguous_differences,
        order_differs_only=order_differs_only,
        ambiguous=ambiguous,
        textual_similarity=similarity,
    )


def _compare_term_sets(
    only_a: set[str],
    only_b: set[str],
    rules: RuleSet,
    technical_differences: list[str],
    ambiguous_differences: list[str],
) -> None:
    """Para cada termo exclusivo de A, verifica se ele e explicitamente
    incompativel com algum termo exclusivo de B (ex.: DIANTEIRO x
    TRASEIRO) — diferenca tecnica certa.

    Termos exclusivos que sobram sem correspondencia sao classificados
    em dois grupos:
      - "codigos tecnicos" (ex.: M10, M12 — letras seguidas de numeros):
        tratados como diferenca tecnica certa, pois codificam uma
        especificacao objetiva.
      - demais palavras sem equivalencia conhecida: tratadas como
        ambiguas — o sistema nao tem regra suficiente para decidir e a
        revisao humana e recomendada.
    """
    matched_a: set[str] = set()
    matched_b: set[str] = set()

    for term_a in only_a:
        for term_b in only_b:
            if rules.are_incompatible(term_a, term_b):
                technical_differences.append(f"termos tecnicamente incompativeis: {term_a} x {term_b}")
                matched_a.add(term_a)
                matched_b.add(term_b)

    remaining_a = only_a - matched_a
    remaining_b = only_b - matched_b

    code_like_a = sorted(t for t in remaining_a if _CODE_LIKE_TERM.match(t))
    code_like_b = sorted(t for t in remaining_b if _CODE_LIKE_TERM.match(t))
    if code_like_a or code_like_b:
        technical_differences.append(
            f"codigos tecnicos exclusivos: A={code_like_a or '-'} B={code_like_b or '-'}"
        )

    word_like_a = sorted(t for t in remaining_a if not _CODE_LIKE_TERM.match(t))
    word_like_b = sorted(t for t in remaining_b if not _CODE_LIKE_TERM.match(t))
    if word_like_a or word_like_b:
        ambiguous_differences.append(
            f"termos exclusivos sem equivalencia conhecida: A={word_like_a or '-'} B={word_like_b or '-'}"
        )


def _number_key(token_value: str) -> str:
    from app.core.tokenizer import numeric_value

    value = numeric_value(token_value)
    return str(int(value)) if value == int(value) else f"{value:g}"
