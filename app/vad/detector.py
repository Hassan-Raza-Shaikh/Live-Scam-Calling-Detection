from app.vad.silero import SileroVADEngine

class VADDetector:
    """Detects active speech in incoming audio frames using VAD engine."""
    def __init__(self):
        self.engine = SileroVADEngine()

    def process(self, chunk: bytes) -> bool:
        return self.engine.is_speech(chunk)
