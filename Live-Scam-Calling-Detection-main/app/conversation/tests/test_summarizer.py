from app.conversation.summarizer import StructuredSummarizer
from app.conversation.state import ConversationState
from app.conversation.snapshot import build_snapshot
from app.conversation.models import IntentStats, TimelineEntry

def test_summarizer_output():
    state = ConversationState(call_id="call_summary")
    state.elapsed_time = 54.0
    state.phase = "REQUEST"
    state.stats = state.stats.__class__(
        total_detections=3,
        unique_intents=2,
        dominant_intent="BANKING",
        detection_frequency=3/54.0,
        average_confidence=0.9,
        highest_confidence=0.98,
        conversation_duration=54.0,
        time_since_last_detection=4.0,
        detection_rate_per_minute=(3/54.0)*60.0
    )
    state.timeline = [
        TimelineEntry(4.0, "00:04", "BANKING"),
        TimelineEntry(11.0, "00:11", "OTP_REQUEST"),
        TimelineEntry(18.0, "00:18", "BANKING")
    ]
    
    intent_summary = {
        "BANKING": IntentStats("BANKING", 2, 0.95, 0.98, 118.0, 50, 4.0),
        "OTP_REQUEST": IntentStats("OTP_REQUEST", 1, 0.8, 0.8, 111.0, 25, 11.0)
    }
    
    snapshot = build_snapshot(state, intent_summary)
    
    summarizer = StructuredSummarizer()
    summary = summarizer.summarize(snapshot)
    
    assert "Conversation Summary" in summary
    assert "Call ID: call_summary" in summary
    assert "Duration: 54 seconds" in summary
    assert "Dominant Intent: BANKING" in summary
    assert "BANKING: 2" in summary
    assert "OTP_REQUEST: 1" in summary
    assert "Highest Confidence: 0.98" in summary
    assert "Recent Timeline:" in summary
    assert "00:04 -> BANKING" in summary
    assert "00:11 -> OTP_REQUEST" in summary
