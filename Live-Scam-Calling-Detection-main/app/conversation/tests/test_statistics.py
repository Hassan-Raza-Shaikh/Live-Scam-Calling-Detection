from app.conversation.statistics import StatisticsCalculator
from app.conversation.events import ConversationEvent

def test_statistics_calculator_empty():
    calc = StatisticsCalculator()
    stats = calc.calculate([], start_time=100.0, current_time=200.0)
    
    assert stats.total_detections == 0
    assert stats.dominant_intent == "NONE"
    assert stats.conversation_duration == 100.0
    assert stats.average_confidence == 0.0

def test_statistics_calculator_aggregates():
    calc = StatisticsCalculator()
    
    events = [
        ConversationEvent(
            timestamp=110.0,
            intent="BANKING",
            confidence=0.9,
            weight=10,
            matched_text="bank",
            detector_name="Pattern",
            matching_strategy="phrase",
            source_file="bank.yaml",
            transcript="call your bank"
        ),
        ConversationEvent(
            timestamp=120.0,
            intent="OTP_REQUEST",
            confidence=0.8,
            weight=20,
            matched_text="otp",
            detector_name="Pattern",
            matching_strategy="phrase",
            source_file="otp.yaml",
            transcript="tell me the otp"
        ),
        ConversationEvent(
            timestamp=130.0,
            intent="OTP_REQUEST",
            confidence=1.0,
            weight=20,
            matched_text="code",
            detector_name="Pattern",
            matching_strategy="phrase",
            source_file="otp.yaml",
            transcript="read code"
        )
    ]
    
    stats = calc.calculate(events, start_time=100.0, current_time=140.0)
    
    assert stats.total_detections == 3
    assert stats.unique_intents == 2
    assert stats.dominant_intent == "OTP_REQUEST"
    assert stats.highest_confidence == 1.0
    # Average of 0.9, 0.8, 1.0 is 0.9
    assert abs(stats.average_confidence - 0.9) < 1e-6
    assert stats.conversation_duration == 40.0
    assert stats.time_since_last_detection == 10.0  # 140 - 130
    
    # Check intent summaries
    intent_summary = calc.calculate_intent_summary(events, current_time=140.0)
    assert len(intent_summary) == 2
    
    banking_stats = intent_summary["BANKING"]
    assert banking_stats.count == 1
    assert banking_stats.average_confidence == 0.9
    assert banking_stats.weight_sum == 10
    assert banking_stats.time_since_last_seen == 30.0  # 140 - 110
    
    otp_stats = intent_summary["OTP_REQUEST"]
    assert otp_stats.count == 2
    assert otp_stats.average_confidence == 0.9  # (0.8 + 1.0) / 2
    assert otp_stats.highest_confidence == 1.0
    assert otp_stats.weight_sum == 40
    assert otp_stats.time_since_last_seen == 10.0  # 140 - 130
