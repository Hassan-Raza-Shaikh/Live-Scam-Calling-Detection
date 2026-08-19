class WarningGenerator:
    """Generates localized warning texts for user presentation."""
    def generate_warning(self, level: str) -> str:
        return f"CRITICAL: {level} risk warning."
