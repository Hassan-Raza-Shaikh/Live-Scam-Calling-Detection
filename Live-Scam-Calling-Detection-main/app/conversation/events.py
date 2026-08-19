from dataclasses import dataclass

@dataclass(frozen=True)
class ConversationEvent:
    """Represents a single scam detection event within the conversation history.
    
    This object is immutable (frozen) to ensure history integrity.
    """
    timestamp: float
    intent: str
    confidence: float
    weight: int
    matched_text: str
    detector_name: str
    matching_strategy: str
    source_file: str
    transcript: str
