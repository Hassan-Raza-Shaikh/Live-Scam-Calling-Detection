class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end = False

class KeywordTrie:
    """Trie structure for fast multi-keyword matching."""
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word: str):
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end = True
