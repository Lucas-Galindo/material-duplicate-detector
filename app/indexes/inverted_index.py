"""Indice invertido termo -> materiais (Sprint 5).

Usado para localizar rapidamente candidatos que compartilham pelo menos
um termo tecnico relevante, evitando comparar todos-contra-todos.
"""

from __future__ import annotations

from collections import defaultdict

from app.models.parsed_material import ParsedMaterial


class InvertedIndex:
    """Indice termo -> posicoes de materiais.

    Termos muito frequentes (ex.: "PARAFUSO" aparecendo em milhares de
    itens) nao ajudam a restringir candidatos e, se usados, geram
    explosao combinatoria. ``max_document_frequency_ratio`` limita quais
    termos participam da geracao de candidatos: um termo presente em mais
    do que essa fracao dos materiais e considerado generico demais e e
    ignorado nessa etapa (ele continua disponivel via ``postings``).
    """

    def __init__(
        self,
        max_document_frequency_ratio: float = 0.05,
        min_absolute_threshold: int = 300,
    ) -> None:
        self._postings: dict[str, set[int]] = defaultdict(set)
        self._max_document_frequency_ratio = max_document_frequency_ratio
        self._min_absolute_threshold = min_absolute_threshold
        self._total_documents = 0

    def build(self, parsed_materials: list[ParsedMaterial]) -> None:
        self._total_documents = len(parsed_materials)
        for position, parsed in enumerate(parsed_materials):
            for term in self._index_terms(parsed):
                self._postings[term].add(position)

    def candidates_for(self, parsed: ParsedMaterial, exclude_position: int) -> set[int]:
        """Retorna as posicoes de materiais que compartilham ao menos um
        termo indexado (nao generico) com ``parsed`` (excluindo o proprio)."""
        max_postings = max(
            self._min_absolute_threshold,
            int(self._total_documents * self._max_document_frequency_ratio),
        )
        candidates: set[int] = set()
        for term in self._index_terms(parsed):
            posting_list = self._postings.get(term, set())
            if len(posting_list) > max_postings:
                continue
            candidates |= posting_list
        candidates.discard(exclude_position)
        return candidates

    def postings(self, term: str) -> set[int]:
        return set(self._postings.get(term.upper(), set()))

    @staticmethod
    def _index_terms(parsed: ParsedMaterial) -> set[str]:
        return set(parsed.normalized_terms) | set(parsed.units) | set(parsed.numbers)
