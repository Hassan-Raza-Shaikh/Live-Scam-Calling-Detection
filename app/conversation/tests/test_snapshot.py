import pytest
from dataclasses import FrozenInstanceError
from app.conversation.state import ConversationState
from app.conversation.snapshot import build_snapshot
from app.conversation.models import ConversationStats

def test_snapshot_immutability():
    state = ConversationState(call_id="call_test")
    state.elapsed_time = 15.0
    state.phase = "TRUST_BUILDING"
    
    snapshot = build_snapshot(state, intent_summary={})
    
    assert snapshot.call_id == "call_test"
    assert snapshot.duration == 15.0
    assert snapshot.phase == "TRUST_BUILDING"
    
    # Try modifying snapshot field and verify it raises FrozenInstanceError
    with pytest.raises(FrozenInstanceError):
        snapshot.phase = "PRESSURE"  # type: ignore

def test_snapshot_serialization():
    state = ConversationState(call_id="call_serial")
    snapshot = build_snapshot(state, intent_summary={})
    
    dict_repr = snapshot.to_dict()
    assert isinstance(dict_repr, dict)
    assert dict_repr["call_id"] == "call_serial"
    assert "stats" in dict_repr
    assert "timeline" in dict_repr
