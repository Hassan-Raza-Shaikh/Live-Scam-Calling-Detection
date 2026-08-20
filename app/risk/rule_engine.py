from typing import List, Dict, Any
from app.conversation.context import WorkerAnalysisResult

class OTPDetectionAgent:
    """Agent specialized in detecting OTP and 2FA code theft requests."""
    
    KEYWORDS = [
        "verification code", "one-time password", "one time password", "otp", "otp code",
        "6-digit code", "six digit code", "6-digit", "six digit", "pin number", "pin code", "read me the code", 
        "security code", "passcode", "pass code", "sms code", "authentication code",
        "two-factor code", "2fa code", "confirmation digits", "sms authorization code"
    ]
    
    def analyze(self, transcript: str) -> WorkerAnalysisResult:
        text_lower = transcript.lower()
        matched = [kw for kw in self.KEYWORDS if kw in text_lower]
        score = 0.95 if len(matched) > 0 else 0.0
        
        return WorkerAnalysisResult(
            agent_name="otp_detection_agent",
            confidence=0.95,
            score=score,
            detected_tactics=["OTP_DEMAND", "OTP_THEFT"] if len(matched) > 0 else [],
            reasoning=f"Matched high-risk verification code theft indicators: {matched}" if matched else "No OTP theft indicators found."
        )

class EmotionalManipulationAgent:
    """Agent specialized in detecting psychological, sentimental, and emotional traps."""
    
    FEAR_INTIMIDATION = [
        "arrest warrant", "warrant for your arrest", "sheriff", "police department", 
        "jail", "prison", "lawsuit", "legal charges", "assets will be frozen", 
        "bank account will be suspended", "deportation", "federal crime", "subpoena",
        "court summons", "asset seizure", "illegal package", "border patrol", "felony charges",
        "bench warrant", "contempt of court", "grand jury citation", "police outside your door",
        "webcam footage", "pegasus spyware", "leak your video", "ruin your reputation"
    ]
    
    ISOLATION_SECRECY = [
        "do not tell anyone", "do not talk to the bank", "do not hang up", 
        "stay on the line", "keep this between us", "strictly confidential", 
        "undercover investigation", "do not tell your family", "do not tell your spouse",
        "do not tell the teller", "do not disconnect", "keep the line open",
        "stay on the line while driving", "leave the room", "confidential executive wire"
    ]
    
    EMERGENCY_SYMPATHY = [
        "hospital", "car accident", "bail money", "in jail", "grandson", 
        "granddaughter", "kidnapped", "emergency funds", "please help me grandma",
        "please help me grandpa", "need money right now for surgery", "lawyer needs cash",
        "public defender wire", "in the back of the van", "they have your daughter",
        "deployed peacekeeper", "oil rig surgery"
    ]
    
    PRESSURE_URGENCY = [
        "within 1 hour", "within 30 minutes", "within 10 minutes", "in 2 minutes", "in 5 minutes",
        "immediately", "right now", "final chance", "before it is too late", "last warning", 
        "officer is on the way", "power cut off", "service disconnection", "final shutoff notice",
        "sim card deactivation", "medicare open enrollment deadline today", "timer has started"
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
            
        total_hits = len(matched_fear) + len(matched_isolation) + len(matched_sympathy) + len(matched_pressure)
        if total_hits >= 2:
            score = 0.95
        elif total_hits == 1:
            score = 0.80
        else:
            score = 0.0
            
        reasoning_parts = []
        if matched_fear:
            reasoning_parts.append(f"Fear/Arrest/Blackmail intimidation: {matched_fear}")
        if matched_isolation:
            reasoning_parts.append(f"Isolation/Secrecy tactics: {matched_isolation}")
        if matched_sympathy:
            reasoning_parts.append(f"Family/Kidnapping emergency exploitation: {matched_sympathy}")
        if matched_pressure:
            reasoning_parts.append(f"High-pressure artificial urgency: {matched_pressure}")
            
        return WorkerAnalysisResult(
            agent_name="emotional_manipulation_agent",
            confidence=0.92,
            score=score,
            detected_tactics=tactics,
            reasoning="; ".join(reasoning_parts) if reasoning_parts else "No psychological or emotional traps detected."
        )

class SocialEngineeringPredictorAgent:
    """Agent that assesses conversational trajectory and predicts imminent scam demands."""
    
    AUTHORITY_TRAPS = [
        "federal officer", "badge number", "case number", "investigator", "agent id",
        "fraud division", "senior analyst", "customs officer", "department of justice",
        "district court clerk", "deputy sheriff", "irs criminal investigation", "ftc investigator",
        "medicare compliance officer", "verizon security", "att fraud division"
    ]
    PAYMENT_TRAPS = [
        "gift card", "target card", "apple card", "steam card", "crypto", "bitcoin atm", "bitcoin kiosk",
        "wire transfer", "cash in envelope", "greendot", "moneypak", "usdt", "safe account", "zelle", "venmo",
        "cashier check", "certified check mover", "western union", "moneygram"
    ]
    
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
            
        score = 0.95 if (matched_auth and matched_pay) else (0.85 if matched_pay else (0.70 if matched_auth else 0.0))
        
        return WorkerAnalysisResult(
            agent_name="social_engineering_predictor",
            confidence=0.90,
            score=score,
            detected_tactics=tactics,
            reasoning=" | ".join(predictions) if predictions else "Normal conversational flow."
        )

class ScamDetectionAgent:
    """Agent specialized in identifying core scam taxonomy signatures."""
    
    PATTERNS = [
        "fraud department", "suspicious transaction", "safe account",
        "account freeze", "microsoft support", "unauthorized charge",
        "unusual activity", "security verification", "confirm your name",
        "anydesk", "teamviewer", "eventvwr", "publishers clearing house",
        "bitcoin atm", "wire money", "zelle payment", "parcel seized",
        "pig butchering", "guaranteed returns", "task optimization",
        "medicare card replacement", "sim swap", "port out pin", "overpaid check"
    ]
    
    def analyze(self, transcript: str) -> WorkerAnalysisResult:
        text_lower = transcript.lower()
        matched = [p for p in self.PATTERNS if p in text_lower]
        score = 0.90 if len(matched) > 0 else 0.0
        
        return WorkerAnalysisResult(
            agent_name="scam_detection_agent",
            confidence=0.88,
            score=score,
            detected_tactics=["SCAM_TAXONOMY_MATCH"] if len(matched) > 0 else [],
            reasoning=f"Matched scam patterns: {matched}" if matched else "No scam patterns identified."
        )

class OrganizationVerificationAgent:
    """Agent that identifies claimed organizations and verifies official security protocols."""
    
    ORGANIZATIONS = {
        "irs": "Internal Revenue Service - Never demands immediate phone payment or gift cards.",
        "fbi": "Federal Bureau of Investigation - Does not call citizens requesting fund transfers.",
        "social security": "Social Security Administration - Never threatens to suspend SSN over the phone.",
        "amazon": "Amazon Customer Support - Never asks users to install remote desktop apps.",
        "microsoft": "Microsoft Technical Support - Does not make unsolicited calls about computer viruses.",
        "apple": "Apple Support - Never asks for Apple Gift Card numbers to unblock iCloud.",
        "chase": "Chase Bank - Will never ask for your PIN, full card number, or OTP over the phone.",
        "bank of america": "Bank of America - Fraud department will never ask for one-time passcodes.",
        "wells fargo": "Wells Fargo - Never asks customers to transfer money to a 'safe holding account'.",
        "usps": "US Postal Service - Does not ask for credit card payment for redelivery via text or call.",
        "medicare": "Medicare - Never calls requesting your card number for a 'new chip card'."
    }
    
    def analyze(self, transcript: str) -> WorkerAnalysisResult:
        text_lower = transcript.lower()
        matched_orgs = [org for org in self.ORGANIZATIONS if org in text_lower]
        
        tactics = []
        notes = []
        if matched_orgs:
            tactics.append("ORGANIZATION_IMPERSONATION")
            for org in matched_orgs:
                notes.append(f"Claimed entity: '{org.upper()}' ({self.ORGANIZATIONS[org]})")
                
        return WorkerAnalysisResult(
            agent_name="organization_verification_agent",
            confidence=0.92,
            score=0.85 if matched_orgs else 0.0,
            detected_tactics=tactics,
            reasoning=" | ".join(notes) if notes else "No specific corporate or institutional claims detected."
        )

class VictimComplianceAgent:
    """Agent specialized in tracking victim compliance vs. resistance cues."""
    
    COMPLIANCE_CUES = [
        "opening my banking app", "opening the app", "logging in right now", "logging into my bank",
        "let me get my credit card", "let me get my card", "let me get my wallet", "getting my wallet",
        "reading the code", "here is the code", "here is the number", "the number is",
        "going to the atm", "driving to the bank", "buying the gift cards", "buying the card",
        "downloading anydesk", "installing anydesk", "installing teamviewer", "downloading teamviewer",
        "sending the wire", "transferring the money", "i will transfer", "i will send it right now"
    ]
    
    RESISTANCE_CUES = [
        "i am not giving you", "i will not share", "who is your supervisor", "what is your badge number",
        "i am hanging up", "calling the police", "this sounds like a scam", "i will visit my local branch",
        "let me call the bank directly", "i do not trust this"
    ]
    
    def analyze(self, transcript: str) -> WorkerAnalysisResult:
        text_lower = transcript.lower()
        matched_compliance = [cue for cue in self.COMPLIANCE_CUES if cue in text_lower]
        matched_resistance = [cue for cue in self.RESISTANCE_CUES if cue in text_lower]
        
        tactics = []
        if matched_compliance:
            tactics.append("VICTIM_COMPLIANCE_ACTION")
        if matched_resistance:
            tactics.append("VICTIM_ACTIVE_RESISTANCE")
            
        is_complying = len(matched_compliance) > 0
        score = 0.98 if is_complying else 0.0
        
        reasoning = ""
        if matched_compliance:
            reasoning = f"CRITICAL: Victim is actively complying with scam directives: {matched_compliance}"
        elif matched_resistance:
            reasoning = f"Victim is actively resisting/questioning caller: {matched_resistance}"
        else:
            reasoning = "Neutral victim stance."
            
        return WorkerAnalysisResult(
            agent_name="victim_compliance_agent",
            confidence=0.95,
            score=score,
            detected_tactics=tactics,
            reasoning=reasoning,
            metadata={"is_complying": is_complying, "is_resisting": len(matched_resistance) > 0}
        )


