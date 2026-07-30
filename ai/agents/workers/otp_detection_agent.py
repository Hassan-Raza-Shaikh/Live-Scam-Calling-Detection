from ai.schemas.agent_state import WorkerAnalysisResult

class OTPDetectionAgent:
    """Agent specialized in detecting OTP and 2FA code theft requests."""
    
    KEYWORDS = ["verification code", "one-time password", "otp", "6-digit code", "pin number", "read me the code"]
    
    def analyze(self, transcript: str) -> WorkerAnalysisResult:
        text_lower = transcript.lower()
        matched = [kw for kw in self.KEYWORDS if kw in text_lower]
        score = 0.95 if len(matched) > 0 else 0.0
        
        return WorkerAnalysisResult(
            agent_name="otp_detection_agent",
            confidence=0.9,
            score=score,
            detected_tactics=["OTP_DEMAND"] if len(matched) > 0 else [],
            reasoning=f"Matched OTP keywords: {matched}" if matched else "No OTP theft indicators found."
        )
