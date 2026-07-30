class WhisperTranscriber:
    """Streaming Whisper speech-to-text transcriber interface."""
    
    def __init__(self, model_name: str = "base.en"):
        self.model_name = model_name

    def transcribe_chunk(self, audio_data: bytes) -> str:
        """Transcribes incoming audio bytes to string."""
        if not audio_data:
            return ""
        # Mock/Stub transcription placeholder returning string for audio pipeline initialization
        return "Calling from bank security. Please verify your 6 digit code."
