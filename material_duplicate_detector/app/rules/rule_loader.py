"""Carregamento de regras externas (Sprint 4).

Le os arquivos JSON de ``config/`` e monta estruturas em memoria (Hash
Maps) usadas pelas demais camadas de ``app.rules`` e pelo comparador.
Nenhuma regra fica hardcoded no codigo — tudo vem dos arquivos JSON,
permitindo evoluir o dicionario tecnico sem alterar o algoritmo.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

_DEFAULT_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"

_REQUIRED_FILES = (
    "abbreviations.json",
    "equivalents.json",
    "critical_terms.json",
    "protected_symbols.json",
)


def _candidate_config_dirs() -> list[Path]:
    """Locais onde os JSON de regras podem estar, em ordem de preferencia.

    Em execucao normal (``python -m app.main``), ``_DEFAULT_CONFIG_DIR``
    (a pasta ``config/`` do projeto) e suficiente. Em um executavel
    gerado pelo PyInstaller, ``__file__`` aponta para dentro do bundle
    (``_internal/`` no modo --onedir, ou uma pasta temporaria
    ``_MEIxxxxx`` no modo --onefile) e a mesma conta ja costuma
    funcionar — MAS so se o `.spec` usado para gerar o executavel
    realmente empacotou ``config/`` como dado (``datas=...`` em
    ``packaging/app.spec``). Se o build foi feito com um comando
    avulso do PyInstaller (sem usar essa spec), a pasta config nao
    existe no bundle, e por isso alguns locais extras sao tentados
    antes de desistir.
    """
    candidates = [_DEFAULT_CONFIG_DIR]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "config")
    if getattr(sys, "frozen", False):
        # Pasta onde o .exe esta (fora de _internal/_MEIxxxxx) — cobre o
        # caso de alguem copiar a pasta config/ manualmente para o lado
        # do executavel como contorno.
        candidates.append(Path(sys.executable).resolve().parent / "config")
    return candidates


@dataclass(frozen=True)
class RuleSet:
    """Regras carregadas, com indices (Hash Maps) prontos para consulta."""

    abbreviation_to_canonical: dict[str, str] = field(default_factory=dict)
    incompatible_groups: list[frozenset[str]] = field(default_factory=list)
    protected_symbols: frozenset[str] = field(default_factory=frozenset)

    def canonical_term(self, term: str) -> str:
        """Retorna o termo canonico para ``term`` (ou o proprio termo)."""
        return self.abbreviation_to_canonical.get(term.upper(), term.upper())

    def are_incompatible(self, term_a: str, term_b: str) -> bool:
        """True se ``term_a`` e ``term_b`` sao termos tecnicos mutuamente
        exclusivos (ex.: DIANTEIRO vs TRASEIRO) — uma diferenca aqui NUNCA
        pode ser tratada como equivalente, independente de formatacao."""
        a, b = term_a.upper(), term_b.upper()
        if a == b:
            return False
        for group in self.incompatible_groups:
            if a in group and b in group:
                return True
        return False

    def is_protected_symbol(self, symbol: str) -> bool:
        return symbol in self.protected_symbols


def load_rules(config_dir: str | Path | None = None) -> RuleSet:
    """Carrega abbreviations.json, equivalents.json, critical_terms.json e
    protected_symbols.json de ``config_dir`` (padrao: tenta a pasta
    config/ do projeto e, se estiver rodando de um executavel
    PyInstaller, alguns locais alternativos dentro do bundle — ver
    ``_candidate_config_dirs``) e retorna um ``RuleSet`` pronto para
    consulta."""
    directory = Path(config_dir) if config_dir is not None else _find_config_dir()

    abbreviations = _load_json(directory / "abbreviations.json")
    equivalents = _load_json(directory / "equivalents.json")
    critical_terms = _load_json(directory / "critical_terms.json")
    protected_symbols_raw = _load_json(directory / "protected_symbols.json")

    abbreviation_to_canonical: dict[str, str] = {
        key.upper(): value.upper()
        for key, value in abbreviations.items()
        if not key.startswith("_")
    }

    for group in equivalents.get("groups", []):
        upper_group = [term.upper() for term in group]
        # O termo canonico e o mais longo do grupo (a forma completa,
        # ex.: DIANTEIRO), nao a abreviacao — abreviacoes explicitas em
        # abbreviations.json continuam tendo prioridade sobre isso.
        canonical = max(upper_group, key=len)
        for term in upper_group:
            if term in abbreviation_to_canonical:
                continue
            abbreviation_to_canonical[term] = canonical

    incompatible_groups = [
        frozenset(term.upper() for term in group)
        for group in critical_terms.get("incompatible_groups", [])
    ]

    protected_symbols = frozenset(protected_symbols_raw.get("protected", []))

    return RuleSet(
        abbreviation_to_canonical=abbreviation_to_canonical,
        incompatible_groups=incompatible_groups,
        protected_symbols=protected_symbols,
    )


def _find_config_dir() -> Path:
    candidates = _candidate_config_dirs()
    for candidate in candidates:
        if all((candidate / name).exists() for name in _REQUIRED_FILES):
            return candidate

    tried = "\n".join(f"  - {c}" for c in candidates)
    raise FileNotFoundError(
        "Nao foi possivel encontrar a pasta config/ com os arquivos de "
        f"regras ({', '.join(_REQUIRED_FILES)}). Locais verificados:\n{tried}\n\n"
        "Se este e um executavel gerado com PyInstaller, gere-o com "
        "'pyinstaller packaging/app.spec' (nao com um comando avulso do "
        "PyInstaller) — so essa spec inclui a pasta config/ como dado "
        "empacotado."
    )


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Arquivo de regras nao encontrado: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
