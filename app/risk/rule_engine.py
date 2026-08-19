from typing import List, Dict, Any
from app.conversation.context import WorkerAnalysisResult

class OTPDetectionAgent:
    """Agent specialized in detecting OTP and 2FA code theft requests."""
    
    KEYWORDS = [
        "verification code", "one-time password", "one time password", "otp", 
        "6-digit code", "six digit code", "pin number", "read me the code", 
        "security code", "passcode", "pass code"
    ]
    
    def analyze(self, transcript: str) -> WorkerAnalysisResult:
        text_lower = transcript.lower()
        matched = [kw for kw in self.KEYWORDS if kw in text_lower]
        score = 0.95 if len(matched) > 0 else 0.0
        
        return WorkerAnalysisResult(
            agent_name="otp_detection_agent",
            confidence=0.95,
            score=score,
            detected_tactics=["OTP_THEFT"] if len(matched) > 0 else [],
            reasoning=f"Matched high-risk verification code theft indicators: {matched}" if matched else "No OTP theft indicators found."
        )

class EmotionalManipulationAgent:
    """Agent specialized in detecting psychological, sentimental, and emotional traps."""
    
    FEAR_INTIMIDATION = [
        "arrest warrant", "warrant for your arrest", "sheriff", "police department", 
        "jail", "prison", "lawsuit", "legal charges", "assets will be frozen", 
        "bank account will be suspended", "deportation", "federal crime", "subpoena"
    ]
    
    ISOLATION_SECRECY = [
        "do not tell anyone", "do not talk to the bank", "do not hang up", 
        "stay on the line", "keep this between us", "strictly confidential", 
        "undercover investigation", "do not tell your family", "do not tell your spouse",
        "do not tell the teller"
    ]
    
    EMERGENCY_SYMPATHY = [
        "hospital", "car accident", "bail money", "in jail", "grandson", 
        "granddaughter", "kidnapped", "emergency funds", "please help me grandma",
        "please help me grandpa", "need money right now for surgery"
    ]
    
    PRESSURE_URGENCY = [
        "within 1 hour", "within 30 minutes", "immediately", "right now", 
        "final chance", "before it is too late", "last warning", "officer is on the way"
    ]
    
    def analyze(self, transcript: str) -> WorkerAnalysisResult:
        text_lower = transcript.lower()
        
        matched_fear = [p for p in self.FEAR_INTIMIDATION if p in text_lower]
        matched_isolation = [p for p in self.ISOLATION_SECRECY if p in text_lower]
        matched_sympathy = [p for p in self.EMERGENCY_SYMPATHY if p in text_lower]
        matched_pressure = [p for p in self.PRESSURE_URGENCY if p in text_lower]
        
        tactics: List[str] = []
        if matched_fear:
            tactics.append("FEAR_INTIMIDATION")
        if matched_isolation:
            tactics.append("ISOLATION_COERCION")
        if matched_sympathy:
            tactics.append("FAMILY_EMERGENCY_EXPLOITATION")
        if matched_pressure:
            tactics.append("HIGH_PRESSURE_URGENCY")
            
        # Compute combined emotional manipulation severity score
        total_hits = len(matched_fear) + len(matched_isolation) + len(matched_sympathy) + len(matched_pressure)
        if total_hits >= 2:
            score = 0.92
        elif total_hits == 1:
            score = 0.78
        else:
            score = 0.0
            
        reasoning_parts = []
        if matched_fear:
            reasoning_parts.append(f"Fear/Arrest intimidation: {matched_fear}")
        if matched_isolation:
            reasoning_parts.append(f"Isolation/Secrecy tactics: {matched_isolation}")
        if matched_sympathy:
            reasoning_parts.append(f"Family/Emergency exploitation: {matched_sympathy}")
        if matched_pressure:
            reasoning_parts.append(f"High-pressure artificial urgency: {matched_pressure}")
            
        return WorkerAnalysisResult(
            agent_name="emotional_manipulation_agent",
            confidence=0.90,
            score=score,
            detected_tactics=tactics,
            reasoning="; ".join(reasoning_parts) if reasoning_parts else "No psychological or emotional traps detected."
        )

class SocialEngineeringPredictorAgent:
    """Agent that assesses conversational trajectory and predicts imminent scam demands."""
    
    AUTHORITY_TRAPS = ["federal officer", "badge number", "case number", "investigator", "agent id"]
    PAYMENT_TRAPS = ["gift card", "target card", "apple card", "crypto", "bitcoin atm", "wire transfer", "cash in envelope"]
    
    def analyze(self, transcript: str, history: List[Dict[str, Any]] = None) -> WorkerAnalysisResult:
        text_lower = transcript.lower()
        
        matched_auth = [p for p in self.AUTHORITY_TRAPS if p in text_lower]
        matched_pay = [p for p in self.PAYMENT_TRAPS if p in text_lower]
        
        tactics = []
        predictions = []
        
        if matched_auth:
            tactics.append("FALSE_AUTHORITY_ASSERTION")
            predictions.append("Caller is establishing false legal authority to induce compliance")
        if matched_pay:
            tactics.append("UNTRACEABLE_PAYMENT_DEMAND")
            predictions.append("Caller is attempting to redirect funds into untraceable payment channels")
            
        score = 0.90 if (matched_auth and matched_pay) else (0.80 if matched_pay else (0.65 if matched_auth else 0.0))
        
        return WorkerAnalysisResult(
            agent_name="social_engineering_predictor",
            confidence=0.88,
            score=score,
            detected_tactics=tactics,
            reasoning=" | ".join(predictions) if predictions else "Normal conversational flow."
        )

class ScamDetectionAgent:
    """Agent specialized in identifying core scam taxonomy signatures."""
    
    PATTERNS = [
        "fraud department", "suspicious transaction", "safe account",
        "account freeze", "microsoft support", "unauthorized charge",
        "unusual activity", "security verification", "confirm your name"
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

