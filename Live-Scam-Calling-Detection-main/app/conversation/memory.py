from typing import List
from app.conversation.interfaces import IMemoryManager
from app.conversation.events import ConversationEvent

class SlidingEventMemory(IMemoryManager):
    """Memory manager that stores conversation events within a rolling window.
    
    Enforces capacity limits (max_events) and temporal limits (max_age_seconds),
    automatically cleaning up old entries to keep memory usage bounded.
    """
    
    def __init__(self, max_events: int = 100, max_age_seconds: float = 60.0):
        self.max_events = max_events
        self.max_age_seconds = max_age_seconds
        self._events: List[ConversationEvent] = []
        self._latest_time: float = 0.0

    def insert(self, event: ConversationEvent) -> None:
        """Inserts a new event and immediately prunes the history.
        
        Args:
            event: The ConversationEvent to store.
        """
        self._events.append(event)
        self._latest_time = max(self._latest_time, event.timestamp)
        self.expire_old_events(event.timestamp)

    def get_events(self) -> List[ConversationEvent]:
        """Retrieves all non-expired events in chronological order.
        
        Returns:
            A list of ConversationEvent objects.
        """
        if self._latest_time > 0.0:
            self.expire_old_events(self._latest_time)
        return list(self._events)

    def get_recent_events(self, limit: int) -> List[ConversationEvent]:
        """Retrieves the most recent events, limited by count.
        
        Args:
            limit: The maximum number of recent events to return.
            
        Returns:
            A list of recent ConversationEvent objects.
        """
        events = self.get_events()
        return events[-limit:]

    def get_events_for_intent(self, intent: str) -> List[ConversationEvent]:
        """Retrieves all stored events matching the specified intent.
        
        Args:
            intent: The intent string to match.
            
        Returns:
            A list of matching ConversationEvent objects.
        """
        return [e for e in self.get_events() if e.intent == intent]

    def expire_old_events(self, current_time: float) -> int:
        """Removes events that exceed the maximum age or capacity bounds.
        
        Args:
            current_time: The reference timestamp (usually now).
            
        Returns:
            The number of expired events removed.
        """
        initial_count = len(self._events)
        
        # 1. Expire by age
        cutoff_time = current_time - self.max_age_seconds
        self._events = [e for e in self._events if e.timestamp >= cutoff_time]
        
        # 2. Expire by capacity (retain newest)
        if len(self._events) > self.max_events:
            self._events = self._events[-self.max_events:]
            
        # Update latest time to reflect current reference clock
        self._latest_time = max(self._latest_time, current_time)
        
        return initial_count - len(self._events)
