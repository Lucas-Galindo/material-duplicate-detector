"""Modelo das multiplas assinaturas tecnicas de um material (Sprint 5)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TechnicalSignature:
    normalized_signature: str
    token_signature: str
    numeric_signature: str
    unit_signature: str
    critical_terms_signature: str
    ordered_signature: str
    unordered_signature: frozenset[str] = field(default_factory=frozenset)
