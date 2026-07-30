class DecisionSupervisor:
    """Computes final decision, risk level classification, and threat mitigation action."""
    
    def evaluate(self, risk_score: float):
        if risk_score >= 0.85:
            return {
                "risk_level": "CRITICAL",
                "alert": True,
                "action": "HANG UP IMMEDIATELY! NEVER SHARE OTP OR PIN CODES."
            }
        elif risk_score >= 0.65:
            return {
                "risk_level": "HIGH",
                "alert": True,
                "action": "Do not provide financial info or follow wire transfer instructions."
            }
        elif risk_score >= 0.40:
            return {
                "risk_level": "MEDIUM",
                "alert": False,
                "action": "Verify caller identity independently."
            }
        return {
            "risk_level": "LOW",
            "alert": False,
            "action": "No threat indicators detected."
        }
