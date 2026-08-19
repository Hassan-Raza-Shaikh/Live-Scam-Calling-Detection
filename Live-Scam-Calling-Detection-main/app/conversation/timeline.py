from typing import List
from app.conversation.models import TimelineEntry
from app.conversation.utils import format_relative_time

class ConversationTimeline:
    """Manages the chronological log of detected scam intents throughout a phone call.
    
    Exposes a clean sequence showing when specific threats were identified relative
    to the start of the call session.
    """
    
    def __init__(self) -> None:
        self._entries: List[TimelineEntry] = []

    def add_entry(self, relative_time_seconds: float, intent: str) -> None:
        """Records a new intent occurrence on the timeline.
        
        Args:
            relative_time_seconds: Elapsed time in seconds since the conversation started.
            intent: The name of the detected intent.
        """
        formatted = format_relative_time(relative_time_seconds)
        self._entries.append(
            TimelineEntry(
                relative_time_seconds=relative_time_seconds,
                formatted_time=formatted,
                intent=intent
            )
        )

    def get_entries(self) -> List[TimelineEntry]:
        """Retrieves a read-only list of all timeline entries.
        
        Returns:
            A list of TimelineEntry dataclass objects.
        """
        return list(self._entries)
