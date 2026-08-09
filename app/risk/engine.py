from app.risk.rule_engine import OTPDetectionAgent, ScamDetectionAgent
from app.risk.scorer import RiskScorer

class RiskEngine:
    """Combines rule engine, classifiers, and heuristics to compute threat scores."""
    def __init__(self):
        self.otp_agent = OTPDetectionAgent()
        self.scam_agent = ScamDetectionAgent()
        self.scorer = RiskScorer()

    def evaluate_text(self, text: str) -> dict:
        otp_res = self.otp_agent.analyze(text)
        scam_res = self.scam_agent.analyze(text)
        max_score = max(otp_res.score, scam_res.score)
        level = self.scorer.get_level(max_score)
        return {
            "score": max_score,
            "level": level
        }
