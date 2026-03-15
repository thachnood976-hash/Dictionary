from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class TrieNode:
    children: dict[str, "TrieNode"] = field(default_factory=dict)
    is_end: bool = False


class Trie:
    def __init__(self) -> None:
        self.root = TrieNode()

    def insert(self, word: str) -> None:
        node = self.root
        for char in word:
            node = node.children.setdefault(char, TrieNode())
        node.is_end = True

    def starts_with(self, prefix: str, limit: int = 20) -> list[str]:
        node = self.root
        for char in prefix:
            node = node.children.get(char)
            if node is None:
                return []
        results: list[str] = []
        self._dfs(node, prefix, results, limit)
        return results

    def _dfs(self, node: TrieNode, prefix: str, results: list[str], limit: int) -> None:
        if len(results) >= limit:
            return
        if node.is_end:
            results.append(prefix)
        for char in sorted(node.children):
            self._dfs(node.children[char], prefix + char, results, limit)
            if len(results) >= limit:
                return

    @classmethod
    def from_words(cls, words: list[str]) -> "Trie":
        trie = cls()
        for word in words:
            trie.insert(word)
        return trie
