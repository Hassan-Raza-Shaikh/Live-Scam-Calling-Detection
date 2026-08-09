class PromptBuilder:
    """Builds structured instruction prompts for LLM threat verification."""
    def build_verification_prompt(self, transcript: str, tactics: list) -> str:
        return f"Verify the following transcript for scams:\n{transcript}\nTactics: {tactics}"
