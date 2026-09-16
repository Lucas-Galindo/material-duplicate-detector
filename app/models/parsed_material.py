"""Multiplas representacoes do texto de um material (Sprint 2/3/4).

Nenhum campo aqui substitui outro: ``original_text`` nunca e alterado, e
cada estagio do pipeline apenas adiciona uma nova representacao.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.material import Material


@dataclass(frozen=True)
class ParsedMaterial:
    material: Material
    original_text: str
    normalized_text: str
    applied_transformations: list[str] = field(default_factory=list)

    # Preenchidos nas Sprints 3/4 (tokenizador e regras). Mantidos aqui
    # desde ja para que o modelo final nao precise ser redesenhado depois.
    raw_tokens: list[str] = field(default_factory=list)
    technical_tokens: list[str] = field(default_factory=list)
    critical_tokens: list[str] = field(default_factory=list)
    numbers: list[str] = field(default_factory=list)
    units: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    normalized_terms: list[str] = field(default_factory=list)

    @property
    def code(self) -> str:
        return self.material.code
