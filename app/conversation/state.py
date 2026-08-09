import uuid
from typing import List, Dict, Any
from app.conversation.models import TimelineEntry, ConversationStats
from app.conversation.events import ConversationEvent
from app.conversation.utils import get_current_timestamp

class ConversationState:
    """Holds the mutable internal state of a conversation session.
    
    This object is managed exclusively by the ConversationManager / ConversationEngine
    to protect session state consistency.
    """
    
    def __init__(self, call_id: str = None) -> None:
        self.call_id: str = call_id or f"call_{uuid.uuid4().hex[:10]}"
        self.start_time: float = get_current_timestamp()
        self.elapsed_time: float = 0.0
        self.last_update_time: float = self.start_time
        
        self.transcript_count: int = 0
        self.detection_count: int = 0
        self.intent_counts: Dict[str, int] = {}
        
        self.average_confidence: float = 0.0
        self.highest_confidence: float = 0.0
        self.latest_intent: str = "NONE"
        self.dominant_intent: str = "NONE"
        self.phase: str = "UNKNOWN"
        
        self.timeline: List[TimelineEntry] = []
        self.recent_events: List[ConversationEvent] = []
        self.stats: ConversationStats = ConversationStats(
            total_detections=0,
            unique_intents=0,
            dominant_intent="NONE",
            detection_frequency=0.0,
            average_confidence=0.0,
            highest_confidence=0.0,
            conversation_duration=0.0,
            time_since_last_detection=0.0,
            detection_rate_per_minute=0.0
        )
        self.metadata: Dict[str, Any] = {}
