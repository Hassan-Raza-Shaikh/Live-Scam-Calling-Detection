from app.phrases.templates import PhraseTemplates

class PhraseMatcher:
    """Matches text against complex semantic threat phrase templates."""
    def __init__(self):
        self.templates = PhraseTemplates()

    def match_phrases(self, text: str) -> list[str]:
        text_lower = text.lower()
        return [t for t in self.templates.TEMPLATES if t in text_lower]
