from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any
from app.conversation.events import ConversationEvent

@dataclass(frozen=True)
class IntentStats:
    """Statistics aggregated for a specific scam intent class."""
    intent: str
    count: int
    average_confidence: float
    highest_confidence: float
    latest_timestamp: float
    weight_sum: int
    time_since_last_seen: float

@dataclass(frozen=True)
class TimelineEntry:
    """Represents a chronological marker in the conversation's detection timeline."""
    relative_time_seconds: float
    formatted_time: str  # e.g., "00:04"
    intent: str

@dataclass(frozen=True)
class ConversationStats:
    """Aggregate statistics for the entire conversation's detections."""
    total_detections: int
    unique_intents: int
    dominant_intent: str
    detection_frequency: float
    average_confidence: float
    highest_confidence: float
    conversation_duration: float
    time_since_last_detection: float
    detection_rate_per_minute: float

@dataclass(frozen=True)
class ConversationSnapshot:
    """An immutable, read-only representation of the conversation state at a point in time."""
    call_id: str
    start_time: float
    duration: float
    phase: str
    stats: ConversationStats
    intent_summary: Dict[str, IntentStats]
    timeline: List[TimelineEntry]
    recent_events: List[ConversationEvent]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Converts the snapshot into a serializable dictionary representation."""
        return asdict(self)
