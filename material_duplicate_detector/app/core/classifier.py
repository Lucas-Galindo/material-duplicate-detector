"""Classificacao final (Sprint 7).

Nao decide por percentual: a classificacao vem das categorias de
diferenca produzidas pelo comparador (Sprint 6).

  - DUPLICADO_CONFIRMADO: nenhuma diferenca tecnica nem termo ambiguo —
    apenas formatacao/ordem diferentes (ou nada diferente).
  - PROVAVEL_DUPLICADO: nenhuma diferenca tecnica certa, mas ha termos
    exclusivos sem equivalencia conhecida — exige revisao humana.
  - SEMELHANTE_DIFERENTE: ha ao menos uma diferenca tecnica confirmada
    (termos incompativeis, codigos diferentes, numeros/unidades/simbolos
    divergentes).
"""

from __future__ import annotations

from app.core.comparator import ComparisonOutcome
from app.models.comparison_result import Classification, ComparisonResult


def classify(outcome: ComparisonOutcome) -> Classification:
    if outcome.has_technical_difference:
        return "SEMELHANTE_DIFERENTE"
    if outcome.ambiguous:
        return "PROVAVEL_DUPLICADO"
    return "DUPLICADO_CONFIRMADO"


def confidence_score(outcome: ComparisonOutcome) -> float:
    """Sinal auxiliar (0-1), NUNCA usado para decidir a classificacao —
    apenas exibido ao usuario como contexto adicional."""
    return round(outcome.textual_similarity, 4)


def build_comparison_result(outcome: ComparisonOutcome) -> ComparisonResult:
    classification = classify(outcome)
    return ComparisonResult(
        code_a=outcome.material_a.code,
        code_b=outcome.material_b.code,
        text_a=outcome.material_a.original_text,
        text_b=outcome.material_b.original_text,
        classification=classification,
        confidence=confidence_score(outcome),
        equal_elements=outcome.equal_elements,
        formatting_differences=outcome.formatting_differences,
        technical_differences=outcome.technical_differences,
        ambiguous_differences=outcome.ambiguous_differences,
        # Copiados so para contexto/exportacao — `outcome` (produzido por
        # `compare()`) nunca leva em conta short_description em nenhum
        # calculo; ela e lida diretamente do Material aqui, depois de
        # toda a comparacao/classificacao ja estarem decididas.
        short_description_a=outcome.material_a.material.short_description,
        short_description_b=outcome.material_b.material.short_description,
    )
