class PhraseParser:
    """Parses text into sentence or clause phrases."""
    def parse_clauses(self, text: str) -> list[str]:
        if not text:
            return []
        return [clause.strip() for clause in text.split(",") if clause.strip()]
