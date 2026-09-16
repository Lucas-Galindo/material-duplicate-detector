"""Indice por assinatura tecnica — Hash Map (Sprint 5).

Agrupa materiais que compartilham exatamente a mesma assinatura
(ex.: mesma ``unordered_signature``), o caminho mais rapido para achar
fortes candidatos a duplicidade.

Assim como o ``InvertedIndex``, aplica um limite de tamanho de grupo:
uma assinatura (em especial a numerica, que ignora qualquer palavra e
so ve os numeros) pode ser compartilhada por materiais de familias
tecnicas completamente diferentes (ex.: "20 CM" aparece em milhares de
itens nao relacionados). Sem esse limite, um grupo gigante gera
O(k^2) pares candidatos e derruba o desempenho em bases grandes.
"""

from __future__ import annotations

from collections import defaultdict

from app.models.technical_signature import TechnicalSignature


class SignatureIndex:
    def __init__(
        self,
        max_group_size_ratio: float = 0.05,
        min_absolute_threshold: int = 300,
    ) -> None:
        self._by_unordered_signature: dict[frozenset[str], set[int]] = defaultdict(set)
        self._by_numeric_signature: dict[str, set[int]] = defaultdict(set)
        self._max_group_size_ratio = max_group_size_ratio
        self._min_absolute_threshold = min_absolute_threshold
        self._total_documents = 0

    def build(self, signatures: list[TechnicalSignature]) -> None:
        self._total_documents = len(signatures)
        for position, signature in enumerate(signatures):
            self._by_unordered_signature[signature.unordered_signature].add(position)
            if signature.numeric_signature:
                self._by_numeric_signature[signature.numeric_signature].add(position)

    def candidates_for(self, signature: TechnicalSignature, exclude_position: int) -> set[int]:
        max_group_size = max(
            self._min_absolute_threshold,
            int(self._total_documents * self._max_group_size_ratio),
        )

        candidates: set[int] = set()
        unordered_group = self._by_unordered_signature.get(signature.unordered_signature, set())
        if len(unordered_group) <= max_group_size:
            candidates |= unordered_group

        if signature.numeric_signature:
            numeric_group = self._by_numeric_signature.get(signature.numeric_signature, set())
            if len(numeric_group) <= max_group_size:
                candidates |= numeric_group

        candidates.discard(exclude_position)
        return candidates
