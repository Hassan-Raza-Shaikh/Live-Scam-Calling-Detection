from app.risk.thresholds import RiskThresholds

class RiskScorer:
    """Calculates final level based on risk score threshold rules."""
    def get_level(self, score: float) -> str:
        if score >= RiskThresholds.CRITICAL:
            return "CRITICAL"
        elif score >= RiskThresholds.HIGH:
            return "HIGH"
        elif score >= RiskThresholds.LOW:
            return "MEDIUM"
        return "LOW"
