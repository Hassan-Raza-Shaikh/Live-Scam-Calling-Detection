from app.keywords.dictionary import KeywordDictionary

class KeywordMatcher:
    """Matches text against the dictionary categories."""
    def __init__(self):
        self.dictionary = KeywordDictionary()

    def match(self, text: str) -> list[str]:
        text_lower = text.lower()
        matched = []
        for cat, keywords in self.dictionary.CATEGORIES.items():
            if any(kw in text_lower for kw in keywords):
                matched.append(cat)
        return matched
