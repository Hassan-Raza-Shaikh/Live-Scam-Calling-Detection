class AcousticFeatureExtractor:
    """Extracts raw pitch, energy, spectral features from audio chunk."""
    def extract_features(self, audio_data: bytes) -> dict:
        return {"pitch": 0.0, "energy": 0.0}
