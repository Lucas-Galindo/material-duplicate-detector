"""Trie auxiliar para termos tecnicos/abreviacoes conhecidas (Sprint 5).

Usada apenas como apoio (reconhecimento de prefixos/termos conhecidos);
NAO decide duplicidade — essa responsabilidade e do comparador/classificador.
"""

from __future__ import annotations


class _TrieNode:
    __slots__ = ("children", "is_word")

    def __init__(self) -> None:
        self.children: dict[str, _TrieNode] = {}
        self.is_word: bool = False


class Trie:
    def __init__(self) -> None:
        self._root = _TrieNode()

    def insert(self, word: str) -> None:
        node = self._root
        for char in word.upper():
            node = node.children.setdefault(char, _TrieNode())
        node.is_word = True

    def insert_all(self, words: list[str]) -> None:
        for word in words:
            self.insert(word)

    def contains(self, word: str) -> bool:
        node = self._find_node(word.upper())
        return node is not None and node.is_word

    def starts_with(self, prefix: str) -> bool:
        return self._find_node(prefix.upper()) is not None

    def words_with_prefix(self, prefix: str) -> list[str]:
        node = self._find_node(prefix.upper())
        if node is None:
            return []
        results: list[str] = []
        self._collect(node, prefix.upper(), results)
        return results

    def _find_node(self, text: str) -> _TrieNode | None:
        node = self._root
        for char in text:
            node = node.children.get(char)
            if node is None:
                return None
        return node

    def _collect(self, node: _TrieNode, prefix: str, results: list[str]) -> None:
        if node.is_word:
            results.append(prefix)
        for char, child in node.children.items():
            self._collect(child, prefix + char, results)
