class LanguageDetector:
    """Detects spoken language of the speech stream (default 'en')."""
    def detect_language(self, audio_data: bytes) -> str:
        return "en"
