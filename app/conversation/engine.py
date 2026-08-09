import threading
from typing import Optional, Dict
from app.detection.models import DetectionReport
from app.conversation.models import ConversationSnapshot
from app.conversation.manager import ConversationManager
from app.conversation.state import ConversationState

class ConversationEngine:
    """The central thread-safe orchestrator for the Conversation Context Framework.
    
    Exposes the public update API, manages active call context registries, and protects
    internal states from concurrent write hazards using reentrant locks.
    
    Thread safety:
        All mutating operations are guarded by a reentrant lock (threading.RLock).
        
    Future extension points:
        - Add database backing for persistent storage and session replaying.
        - Add multi-language and speaker diarization routing.
    """
    
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._conversations: Dict[str, ConversationManager] = {}

    def update(
        self, 
        report: DetectionReport, 
        call_id: Optional[str] = None
    ) -> ConversationSnapshot:
        """Processes a DetectionReport, advancing the conversation state and returning an immutable snapshot.
        
        Args:
            report: The input DetectionReport dataclass.
            call_id: Optional session identifier. If omitted, checks report.metadata
                     for 'call_id' or 'session_id', defaulting to 'default_call'.
                     
        Returns:
            An immutable, read-only ConversationSnapshot.
        """
        # Resolve call ID
        if not call_id:
            call_id = report.metadata.get("call_id") or report.metadata.get("session_id") or "default_call"
            
        with self._lock:
            if call_id not in self._conversations:
                # Create a new conversation session state
                state = ConversationState(call_id=call_id)
                self._conversations[call_id] = ConversationManager(state=state)
                
            manager = self._conversations[call_id]
            return manager.update(report)

    def get_snapshot(self, call_id: str) -> Optional[ConversationSnapshot]:
        """Retrieves a read-only snapshot of the active call without mutating state.
        
        Args:
            call_id: Unique call identifier.
            
        Returns:
            ConversationSnapshot if found, else None.
        """
        with self._lock:
            manager = self._conversations.get(call_id)
            if not manager:
                return None
            
            # Recalculate stats for current snapshot query to keep time aggregates accurate
            # We can run update with an empty report, or construct from active state.
            # Building from active state is simplest:
            from app.conversation.snapshot import build_snapshot
            active_events = manager._memory.get_events()
            current_time = manager.state.last_update_time
            intent_summary = manager._statistics_calculator.calculate_intent_summary(
                events=active_events,
                current_time=current_time
            )
            return build_snapshot(manager.state, intent_summary)

    def close_conversation(self, call_id: str) -> None:
        """Closes the conversation session and purges it from memory.
        
        Args:
            call_id: Unique call identifier.
        """
        with self._lock:
            self._conversations.pop(call_id, None)
