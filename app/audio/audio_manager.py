from app.audio.recorder import AudioRecorder
from app.audio.stream import AudioStream
from app.audio.buffer import AudioBuffer

class AudioManager:
    """Orchestrates audio capture, buffering, and resampling."""
    def __init__(self):
        self.recorder = AudioRecorder()
        self.stream = AudioStream()
        self.buffer = AudioBuffer()
