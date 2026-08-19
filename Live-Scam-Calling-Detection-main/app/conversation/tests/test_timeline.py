from app.conversation.timeline import ConversationTimeline

def test_timeline_formatting_and_ordering():
    timeline = ConversationTimeline()
    
    timeline.add_entry(4.0, "BANKING")
    timeline.add_entry(11.5, "OTP_REQUEST")
    timeline.add_entry(72.0, "URGENCY")
    
    entries = timeline.get_entries()
    assert len(entries) == 3
    
    assert entries[0].formatted_time == "00:04"
    assert entries[0].intent == "BANKING"
    
    assert entries[1].formatted_time == "00:11"
    assert entries[1].intent == "OTP_REQUEST"
    
    assert entries[2].formatted_time == "01:12"
    assert entries[2].intent == "URGENCY"
