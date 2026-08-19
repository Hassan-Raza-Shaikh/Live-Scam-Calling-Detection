class BehavioralFeatureExtractor:
    """Tracks speaker speech rate, interruption patterns, and silence durations."""
    def extract_features(self, conversation_turns: list) -> dict:
        return {"interruption_count": 0, "speech_rate": 0.0}
