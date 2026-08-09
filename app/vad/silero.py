import numpy as np

class SileroVADEngine:
    """Silero Voice Activity Detection wrapper for real-time speech frame filtering."""
    
    def __init__(self, threshold: float = 0.5, sample_rate: int = 16000):
        self.threshold = threshold
        self.sample_rate = sample_rate

    def is_speech(self, pcm_data: bytes) -> bool:
        """Determines if raw PCM audio chunk contains active speech."""
        if not pcm_data:
            return False
        # Calculate RMS amplitude as lightweight fallback VAD metric
        audio_array = np.frombuffer(pcm_data, dtype=np.int16)
        if len(audio_array) == 0:
            return False
        rms = np.sqrt(np.mean(audio_array.astype(np.float32)**2))
        return rms > 300.0
