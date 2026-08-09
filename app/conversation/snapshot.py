from typing import Dict
from app.conversation.state import ConversationState
from app.conversation.models import ConversationSnapshot, IntentStats

def build_snapshot(
    state: ConversationState, 
    intent_summary: Dict[str, IntentStats]
) -> ConversationSnapshot:
    """Builds an immutable read-only ConversationSnapshot from mutable state.
    
    Deep copies or converts collections to protect state integrity.
    
    Args:
        state: The current mutable ConversationState object.
        intent_summary: Pre-calculated IntentStats dictionary.
        
    Returns:
        A read-only ConversationSnapshot.
    """
    return ConversationSnapshot(
        call_id=state.call_id,
        start_time=state.start_time,
        duration=state.elapsed_time,
        phase=state.phase,
        stats=state.stats,
        intent_summary=dict(intent_summary),
        timeline=list(state.timeline),
        recent_events=list(state.recent_events),
        metadata=dict(state.metadata)
    )
