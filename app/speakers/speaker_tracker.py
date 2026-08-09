class SpeakerTracker:
    """Tracks active speaking turns and channel IDs."""
    def __init__(self):
        self.turns = []

    def register_turn(self, speaker: str, duration_sec: float):
        self.turns.append({"speaker": speaker, "duration": duration_sec})
