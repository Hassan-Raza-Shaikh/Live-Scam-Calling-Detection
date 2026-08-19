from app.conversation.memory import SlidingEventMemory
from app.conversation.events import ConversationEvent

def test_memory_capacity_expiration():
    # Set capacity to 2
    memory = SlidingEventMemory(max_events=2, max_age_seconds=100.0)
    
    event1 = ConversationEvent(10.0, "BANKING", 0.9, 10, "bank", "Det", "strat", "f.yaml", "t")
    event2 = ConversationEvent(20.0, "URGENCY", 0.8, 20, "now", "Det", "strat", "f.yaml", "t")
    event3 = ConversationEvent(30.0, "OTP_REQUEST", 0.9, 30, "otp", "Det", "strat", "f.yaml", "t")
    
    memory.insert(event1)
    memory.insert(event2)
    assert len(memory._events) == 2
    
    # Inserting third should expire the first one
    memory.insert(event3)
    events = memory.get_events()
    assert len(events) == 2
    assert events[0].intent == "URGENCY"
    assert events[1].intent == "OTP_REQUEST"

def test_memory_age_expiration():
    # Set age limit to 10 seconds
    memory = SlidingEventMemory(max_events=100, max_age_seconds=10.0)
    
    event1 = ConversationEvent(10.0, "BANKING", 0.9, 10, "bank", "Det", "strat", "f.yaml", "t")
    event2 = ConversationEvent(15.0, "URGENCY", 0.8, 20, "now", "Det", "strat", "f.yaml", "t")
    
    memory.insert(event1)
    memory.insert(event2)
    
    # If reference time is 22.0: event1 (10.0) is expired (> 10s age). event2 (15.0) remains.
    expired = memory.expire_old_events(22.0)
    assert expired == 1
    
    events = memory._events
    assert len(events) == 1
    assert events[0].intent == "URGENCY"
