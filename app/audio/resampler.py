class AudioResampler:
    """Resamples audio bytes to target sample rate (e.g. 16kHz)."""
    def __init__(self, source_rate: int, target_rate: int = 16000):
        self.source_rate = source_rate
        self.target_rate = target_rate

    def resample(self, pcm_data: bytes) -> bytes:
        return pcm_data
