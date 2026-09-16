"""Testes do indice invertido, indice de assinaturas, trie e geracao de
candidatos (Sprint 5), incluindo um teste de eficiencia (nao deve gerar
O(n^2) comparacoes)."""

from __future__ import annotations

import time

import pytest

from app.core.candidate_generator import generate_candidate_pairs
from app.core.signature_builder import build_signature
from app.core.technical_parser import parse_material
from app.indexes.inverted_index import InvertedIndex
from app.indexes.signature_index import SignatureIndex
from app.indexes.trie import Trie
from app.models.material import Material
from app.rules.rule_loader import load_rules


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _parsed(texts: list[str], rules):
    materials = [Material(row_index=i, code=str(i), analysis_text=t) for i, t in enumerate(texts)]
    return [parse_material(m, rules) for m in materials]


def test_inverted_index_finds_shared_term_candidates(rules):
    parsed = _parsed(["PARAFUSO INOX M10", "PARAFUSO ACO M12", "PORCA INOX M10"], rules)
    index = InvertedIndex()
    index.build(parsed)
    candidates = index.candidates_for(parsed[0], exclude_position=0)
    assert candidates == {1, 2}  # compartilham PARAFUSO ou INOX/M10


def test_signature_index_groups_exact_unordered_matches(rules):
    parsed = _parsed(["PARAFUSO 20 CM X 1/2 MM", "PARAFUSO 20CMX1/2MM", "PORCA M6"], rules)
    signatures = [build_signature(p) for p in parsed]
    index = SignatureIndex()
    index.build(signatures)
    candidates = index.candidates_for(signatures[0], exclude_position=0)
    assert candidates == {1}


def test_trie_basic_operations():
    trie = Trie()
    trie.insert_all(["DIANT", "DIANTEIRO", "DIREITO"])
    assert trie.contains("DIANT")
    assert not trie.contains("DIA")
    assert trie.starts_with("DIA")
    assert sorted(trie.words_with_prefix("DIA")) == ["DIANT", "DIANTEIRO"]
    assert trie.words_with_prefix("ZZZ") == []


def test_generate_candidate_pairs_below_threshold_is_exhaustive(rules):
    # Regressao (perda de duplicados em bases pequenas/medias): ate
    # EXHAUSTIVE_THRESHOLD materiais, TODOS os pares devem ser gerados,
    # mesmo sem nenhum termo/assinatura em comum — elimina de vez a
    # possibilidade de um indice de bloqueio descartar um par valido.
    parsed = _parsed(
        [
            "PARAFUSO 20 CM X 1/2 MM",
            "PARAFUSO 20CMX1/2MM",
            "PORCA SEXTAVADA M6",
        ],
        rules,
    )
    signatures = [build_signature(p) for p in parsed]
    pairs = generate_candidate_pairs(parsed, signatures)
    assert pairs == [(0, 1), (0, 2), (1, 2)]


def test_generate_candidate_pairs_basic_indexed_path(rules):
    # Mesmo cenario de test_generate_candidate_pairs_below_threshold_is_exhaustive,
    # mas forcando o caminho indexado (exhaustive_threshold=0) para
    # continuar testando a selecao por termos/assinaturas em si.
    parsed = _parsed(
        [
            "PARAFUSO 20 CM X 1/2 MM",
            "PARAFUSO 20CMX1/2MM",
            "PORCA SEXTAVADA M6",
        ],
        rules,
    )
    signatures = [build_signature(p) for p in parsed]
    pairs = generate_candidate_pairs(parsed, signatures, exhaustive_threshold=0)
    assert (0, 1) in pairs
    assert (0, 2) not in pairs
    assert (1, 2) not in pairs


def test_generate_candidate_pairs_finds_large_group_of_identical_duplicates(rules):
    # Regressao: um grupo grande de materiais IDENTICOS compartilha
    # apenas termos muito comuns e pode ultrapassar o limite de
    # frequencia dos indices — o pior cenario possivel, pois sao os
    # duplicados mais obvios. O agrupamento por texto exato (sem limite)
    # deve garantir que nenhum deles fique de fora. Forca o caminho
    # indexado (exhaustive_threshold=0): abaixo do limite exaustivo essa
    # garantia e trivial (todos os pares saem de qualquer forma).
    parsed = _parsed(["PARAFUSO INOX PADRAO"] * 500, rules)
    signatures = [build_signature(p) for p in parsed]
    pairs = generate_candidate_pairs(parsed, signatures, exhaustive_threshold=0)
    covered_positions = {p for pair in pairs for p in pair}
    assert covered_positions == set(range(500))


def test_generate_candidate_pairs_avoids_full_cartesian_explosion(rules):
    # 500 materiais em 50 grupos distintos (10 materiais por grupo, com
    # pequenas variacoes de formatacao). Forca o caminho indexado
    # (exhaustive_threshold=0) para testar a selecao em si — abaixo do
    # limite exaustivo, o caminho padrao geraria todos os pares mesmo.
    # O numero de pares candidatos deve ficar proximo do numero de pares
    # DENTRO de cada grupo, nao de C(500, 2) = 124750.
    texts: list[str] = []
    for group in range(50):
        for variant in range(10):
            texts.append(f"PECA TECNICA{group:03d} MODELO{group:03d}X{variant}")

    parsed = _parsed(texts, rules)
    signatures = [build_signature(p) for p in parsed]

    start = time.perf_counter()
    pairs = generate_candidate_pairs(parsed, signatures, exhaustive_threshold=0)
    elapsed = time.perf_counter() - start

    full_cartesian = len(texts) * (len(texts) - 1) // 2
    assert len(pairs) < full_cartesian * 0.2
    assert elapsed < 5.0
