from typing import List, Dict
from app.conversation.interfaces import IPhaseDetector
from app.conversation.events import ConversationEvent
from app.conversation.models import IntentStats

# Phase ordering to ensure progressive phase transitions (once a high-severity stage is reached, we don't regress)
PHASE_ORDER = {
    "UNKNOWN": 0,
    "GREETING": 1,
    "TRUST_BUILDING": 2,
    "IDENTITY": 3,
    "REQUEST": 4,
    "PRESSURE": 5,
    "ENDING": 6
}

class HeuristicPhaseDetector(IPhaseDetector):
    """Heuristic state machine to transition the conversation through scam phases.
    
    Phases:
        - UNKNOWN: Initial state.
        - GREETING: Conversation opening/start.
        - TRUST_BUILDING: Scammer setting up context (e.g., banking/investments details).
        - IDENTITY: Scammer establishing fake credentials or impersonating representatives.
        - REQUEST: Scammer demanding sensitive action (OTP, remote access software install).
        - PRESSURE: High-pressure tactics (legal threats, urgency triggers).
        - ENDING: Wrap up.
        
    Future extension points:
        - Swap this implementation with a trained Classifier or LLM-based sequence tagger.
    """
    
    def detect_phase(
        self, 
        current_phase: str, 
        events: List[ConversationEvent], 
        intent_stats: Dict[str, IntentStats]
    ) -> str:
        """Determines the next conversation phase using heuristic thresholds.
        
        Args:
            current_phase: The active phase name before this evaluation.
            events: Chronological list of active ConversationEvent items.
            intent_stats: Pre-calculated intent aggregations.
            
        Returns:
            The next phase name as a string.
        """
        if not events:
            return current_phase if current_phase in PHASE_ORDER else "UNKNOWN"

        # Determine target candidate phase based on intent prevalence
        candidate_phase = "UNKNOWN"
        
        has_otp = "OTP_REQUEST" in intent_stats
        has_remote = "REMOTE_ACCESS" in intent_stats
        has_banking = "BANKING_FRAUD" in intent_stats
        has_investment = "INVESTMENT_SCAM" in intent_stats
        has_crypto = "CRYPTO_SCAM" in intent_stats
        has_urgency = "URGENCY" in intent_stats
        has_gov = "GOVERNMENT_IMPERSONATION" in intent_stats
        has_impersonation = "IMPERSONATION" in intent_stats

        # Heuristic rules:
        if has_urgency or has_gov:
            candidate_phase = "PRESSURE"
        elif has_otp or has_remote:
            candidate_phase = "REQUEST"
        elif has_banking or has_investment or has_crypto:
            candidate_phase = "TRUST_BUILDING"
        elif has_impersonation:
            candidate_phase = "IDENTITY"
        else:
            # If we have some events but none of the above, we are building trust or in greeting
            latest_time = max(e.timestamp for e in events)
            earliest_time = min(e.timestamp for e in events)
            duration = latest_time - earliest_time
            if duration < 15.0:
                candidate_phase = "GREETING"
            else:
                candidate_phase = "TRUST_BUILDING"

        # Enforce progressive transitions (don't downgrade to GREETING/TRUST_BUILDING if already in REQUEST/PRESSURE)
        current_rank = PHASE_ORDER.get(current_phase, 0)
        candidate_rank = PHASE_ORDER.get(candidate_phase, 0)
        
        if candidate_rank > current_rank:
            return candidate_phase
            
        return current_phase
