class TextNormalizer:
    """Normalizes text by converting to lowercase, removing double spacing, etc."""
    def normalize(self, text: str) -> str:
        if not text:
            return ""
        return " ".join(text.lower().split())
