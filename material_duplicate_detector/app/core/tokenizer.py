"""Tokenizador tecnico (Sprint 3).

Recebe o texto ja normalizado (``normalizer.normalize``) e o quebra em
tokens tipados, reconhecendo:

  - palavras (``WORD``)
  - codigos tecnicos alfanumericos, ex.: M10, M12 (``CODE``)
  - numeros inteiros (``INTEGER``)
  - numeros decimais, ex.: 12,5 / 12.5 (``DECIMAL``)
  - fracoes, ex.: 1/2 (``FRACTION``)
  - unidades conhecidas, ex.: CM, MM, KG (``UNIT``)
  - simbolos tecnicos, ex.: " ' - # % ° (``SYMBOL``)
  - separador dimensional "X" (``SEPARATOR``)

Nao decide duplicidade nem aplica equivalencias — isso e feito nas
camadas de regras (Sprint 4) e no comparador (Sprint 6).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Unidades tecnicas conhecidas. Lista inicial cobrindo as categorias
# citadas no escopo (comprimento, peso, eletricas, pressao, temperatura).
# Pode ser estendida futuramente via config (Sprint 4).
KNOWN_UNITS: frozenset[str] = frozenset(
    {
        "MM", "CM", "M", "KM", "POL",
        "MG", "G", "KG", "TON",
        "ML", "L",
        "V", "A", "W", "KW", "HZ", "OHM",
        "PA", "KPA", "MPA", "BAR",
        "C", "F", "K",
        "UN", "PC", "PCT", "CX", "KIT",
    }
)

_TOKEN_PATTERN = re.compile(
    r"""
    (?P<FRACTION>\d+/\d+)
  | (?P<DECIMAL>\d+[.,]\d+)
  | (?P<CODE>[A-Za-zÀ-Úà-ú]+\d+[A-Za-zÀ-Úà-ú0-9]*)
  | (?P<INTEGER>\d+)
  | (?P<X_SEP>\bX\b)
  | (?P<WORD>[A-Za-zÀ-Úà-ú]+)
  | (?P<SYMBOL>["'\-#%°])
  | (?P<OTHER>\S)
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class Token:
    type: str
    value: str


def tokenize(normalized_text: str) -> list[Token]:
    """Tokeniza um texto ja normalizado (maiusculo, espacos padronizados)."""
    tokens: list[Token] = []
    for match in _TOKEN_PATTERN.finditer(normalized_text):
        kind = match.lastgroup
        value = match.group()
        if kind == "WORD" and value in KNOWN_UNITS:
            kind = "UNIT"
        elif kind == "X_SEP":
            kind = "SEPARATOR"
        tokens.append(Token(type=kind, value=value))
    return tokens


def extract_numbers(tokens: list[Token]) -> list[str]:
    """Retorna os valores numericos (inteiros, decimais e fracoes), em ordem."""
    return [t.value for t in tokens if t.type in ("INTEGER", "DECIMAL", "FRACTION")]


def extract_units(tokens: list[Token]) -> list[str]:
    """Retorna as unidades tecnicas reconhecidas, em ordem."""
    return [t.value for t in tokens if t.type == "UNIT"]


def extract_symbols(tokens: list[Token]) -> list[str]:
    """Retorna os simbolos tecnicos preservados, em ordem."""
    return [t.value for t in tokens if t.type == "SYMBOL"]


def extract_words(tokens: list[Token]) -> list[str]:
    """Retorna palavras e codigos alfanumericos, em ordem."""
    return [t.value for t in tokens if t.type in ("WORD", "CODE")]


def numeric_value(token_value: str) -> float:
    """Converte um valor numerico de token (inteiro/decimal/fracao) em float.

    Alguns tokens no formato N/D nao sao fracoes matematicas de verdade,
    e sim codigos/bitolas tecnicas com denominador zero (ex.: cabo/fio
    "1/0 AWG", "2/0", "4/0" — notacao real e comum em materiais
    eletricos). Nesses casos a divisao e indefinida; em vez de propagar
    ZeroDivisionError e derrubar a analise inteira, o numerador e usado
    como valor de referencia — o token continua distinto de outros (via
    o texto original preservado e o token_signature), apenas o valor
    numerico auxiliar nao pode ser calculado por divisao.
    """
    if "/" in token_value:
        numerator, denominator = token_value.split("/", 1)
        denominator_value = float(denominator)
        if denominator_value == 0:
            return float(numerator)
        return float(numerator) / denominator_value
    return float(token_value.replace(",", "."))
