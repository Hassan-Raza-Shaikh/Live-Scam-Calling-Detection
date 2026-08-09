class TextFormatter:
    """Formats text for console output display or logs."""
    def format_transcript_line(self, speaker: str, text: str) -> str:
        return f"[{speaker}]: {text}"
