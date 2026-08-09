from abc import ABC, abstractmethod
from typing import List, Dict, Any
from app.conversation.events import ConversationEvent
from app.conversation.models import ConversationSnapshot, ConversationStats, IntentStats

class IMemoryManager(ABC):
    """Interface for managing sliding event memory."""
    
    @abstractmethod
    def insert(self, event: ConversationEvent) -> None:
        """Inserts a new event and triggers sliding-window expiration."""
        pass

    @abstractmethod
    def get_events(self) -> List[ConversationEvent]:
        """Returns all unexpired events sorted by timestamp ascending."""
        pass

    @abstractmethod
    def get_recent_events(self, limit: int) -> List[ConversationEvent]:
        """Returns the most recent events up to the specified limit."""
        pass

    @abstractmethod
    def get_events_for_intent(self, intent: str) -> List[ConversationEvent]:
        """Returns all unexpired events matching a specific intent."""
        pass

    @abstractmethod
    def expire_old_events(self, current_time: float) -> int:
        """Manually triggers sliding window age expiration based on current time."""
        pass


class IStatisticsCalculator(ABC):
    """Interface for processing and compiling statistics from event history."""
    
    @abstractmethod
    def calculate(
        self, 
        events: List[ConversationEvent], 
        start_time: float, 
        current_time: float
    ) -> ConversationStats:
        """Calculates global aggregates for the conversation."""
        pass

    @abstractmethod
    def calculate_intent_summary(
        self, 
        events: List[ConversationEvent], 
        current_time: float
    ) -> Dict[str, IntentStats]:
        """Calculates metrics for each unique intent type."""
        pass


class IPhaseDetector(ABC):
    """Interface for detecting the active conversational phase."""
    
    @abstractmethod
    def detect_phase(
        self, 
        current_phase: str, 
        events: List[ConversationEvent], 
        intent_stats: Dict[str, IntentStats]
    ) -> str:
        """Evaluates heuristic transitions and returns the next conversation phase."""
        pass


class ISummarizer(ABC):
    """Interface for generating user-friendly summaries from snapshots."""
    
    @abstractmethod
    def summarize(self, snapshot: ConversationSnapshot) -> str:
        """Generates a text summary representation of the conversation state."""
        pass
