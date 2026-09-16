"""Normalizacao segura do texto original (Sprint 2).

Realiza apenas transformacoes que NAO alteram o significado tecnico:
maiusculas, normalizacao de espacos, normalizacao segura de acentos e
padronizacao de agrupamento entre numero/unidade/separador. Simbolos
tecnicos (definidos em config/protected_symbols.json) nunca sao
removidos aqui — essa lista e aplicada pela camada de regras (Sprint 4).

O resultado e auditavel: ``normalize`` sempre retorna tanto o texto
normalizado quanto a lista de transformacoes aplicadas.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

_ACCENT_SAFE_MAP = str.maketrans(
    "ÁÀÂÃÄáàâãäÉÈÊËéèêëÍÌÎÏíìîïÓÒÔÕÖóòôõöÚÙÛÜúùûüÇç",
    "AAAAAaaaaaEEEEeeeeIIIIiiiiOOOOOoooooUUUUuuuuCc",
)

# Insere espaco entre numero e letra colados (20CM -> 20 CM). NAO faz o
# inverso (letra seguida de numero, ex.: "M10"): codigos tecnicos como
# M10/M12 devem permanecer colados, pois separar mudaria a leitura do
# codigo.
_NUMBER_LETTER_BOUNDARY = re.compile(r"(?<=[0-9])(?=[A-Za-zÀ-Úà-ú])")

# "X" usado como separador dimensional colado entre numeros/unidades
# (CMX1/2MM -> CM X 1/2MM) — soh quando adjacente a um digito de um dos
# lados, nunca quando ja esta isolado ou faz parte de outra palavra.
_X_SEPARATOR = re.compile(
    r"(?<=[0-9A-Za-zÀ-Úà-ú])X(?=[0-9])|(?<=[0-9])X(?=[0-9A-Za-zÀ-Úà-ú])"
)

_MULTI_SPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class NormalizationResult:
    original_text: str
    normalized_text: str
    applied_transformations: list[str] = field(default_factory=list)


def normalize(text: str) -> NormalizationResult:
    """Normaliza ``text`` preservando o significado tecnico.

    Etapas (auditaveis, na ordem aplicada):
      1. Espacos nas bordas
      2. Maiusculizacao
      3. Normalizacao segura de acentos
      4. Separacao de numero/letra colados
      5. Separacao do "X" usado como separador dimensional
      6. Colapso de espacos multiplos
    """
    transformations: list[str] = []
    current = text

    stripped = current.strip()
    if stripped != current:
        transformations.append("espacos_nas_bordas")
    current = stripped

    upper = current.upper()
    if upper != current:
        transformations.append("maiusculizacao")
    current = upper

    de_accented = current.translate(_ACCENT_SAFE_MAP)
    de_accented = unicodedata.normalize("NFKC", de_accented)
    if de_accented != current:
        transformations.append("normalizacao_de_acentos")
    current = de_accented

    with_boundaries = _NUMBER_LETTER_BOUNDARY.sub(" ", current)
    if with_boundaries != current:
        transformations.append("separacao_numero_letra")
    current = with_boundaries

    with_x = _X_SEPARATOR.sub(" X ", current)
    if with_x != current:
        transformations.append("separacao_de_x_dimensional")
    current = with_x

    collapsed = _MULTI_SPACE.sub(" ", current).strip()
    if collapsed != current:
        transformations.append("colapso_de_espacos")
    current = collapsed

    return NormalizationResult(
        original_text=text,
        normalized_text=current,
        applied_transformations=transformations,
    )
