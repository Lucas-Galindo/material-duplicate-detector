"""Modelo do resultado de comparacao explicavel (Sprint 6/7)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Classification = Literal["DUPLICADO_CONFIRMADO", "PROVAVEL_DUPLICADO", "SEMELHANTE_DIFERENTE"]
ReviewStatus = Literal["PENDENTE", "APROVADO", "REJEITADO"]


@dataclass
class ComparisonResult:
    """Resultado explicavel de uma comparacao entre dois materiais.

    Diferente de ``Material``/``ParsedMaterial`` (que preservam o texto
    original e nunca mudam), este objeto representa um item de trabalho
    de revisao: ``review_status`` e ``observation`` sao alterados pelo
    usuario ao revisar o par na interface (Sprint 9).
    """

    code_a: str
    code_b: str
    text_a: str
    text_b: str
    classification: Classification
    confidence: float
    equal_elements: list[str] = field(default_factory=list)
    formatting_differences: list[str] = field(default_factory=list)
    technical_differences: list[str] = field(default_factory=list)
    ambiguous_differences: list[str] = field(default_factory=list)
    review_status: ReviewStatus = "PENDENTE"
    observation: str = ""
    # Puramente informativo (coluna "Descricao Curta" da planilha de
    # origem, quando presente) — NUNCA usado no calculo de
    # classification/confidence, so carregado para dar contexto ao
    # usuario na revisao/exportacao (ver Material.short_description).
    short_description_a: str = ""
    short_description_b: str = ""
