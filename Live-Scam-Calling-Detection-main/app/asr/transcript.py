class TranscriptManager:
    """Manages transcript history log segments."""
    def __init__(self):
        self.segments = []

    def add_segment(self, segment: str):
        self.segments.append(segment)

    def get_full_text(self) -> str:
        return " ".join(self.segments)
