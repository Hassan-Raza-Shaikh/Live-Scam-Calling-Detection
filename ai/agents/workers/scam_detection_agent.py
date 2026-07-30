from ai.schemas.agent_state import WorkerAnalysisResult

class ScamDetectionAgent:
    """Agent specialized in identifying core scam taxonomy signatures."""
    
    PATTERNS = [
        "fraud department", "suspicious transaction", "safe account",
        "account freeze", "microsoft support", "unauthorized charge"
    ]
    
    def analyze(self, transcript: str) -> WorkerAnalysisResult:
        text_lower = transcript.lower()
        matched = [p for p in self.PATTERNS if p in text_lower]
        score = 0.88 if len(matched) > 0 else 0.0
        
        return WorkerAnalysisResult(
            agent_name="scam_detection_agent",
            confidence=0.85,
            score=score,
            detected_tactics=["SCAM_TAXONOMY_MATCH"] if len(matched) > 0 else [],
            reasoning=f"Matched scam patterns: {matched}" if matched else "No scam patterns identified."
        )
