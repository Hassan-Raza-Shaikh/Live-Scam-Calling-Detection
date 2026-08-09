class LLMExplanation:
    """Generates detailed, readable threat explanation context."""
    def generate_explanation(self, tactics: list) -> str:
        return f"Warning: Caller is utilizing known scam techniques including {tactics}."
