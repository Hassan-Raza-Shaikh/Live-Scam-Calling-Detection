import threading
from app.conversation.engine import ConversationEngine
from app.detection.models import DetectionReport, Detection

def create_report(transcript: str, intent: str, confidence: float, timestamp: float) -> DetectionReport:
    det = Detection(
        intent=intent,
        matched_text="sample",
        matched_rule="rule",
        confidence=confidence,
        weight=10,
        detector_name="Pattern",
        matching_strategy="phrase",
        start_index=0,
        end_index=6,
        source_file="file.yaml",
        timestamp=timestamp
    )
    return DetectionReport(
        original_transcript=transcript,
        normalized_transcript=transcript.lower(),
        detections=[det],
        processing_time_ms=1.0,
        detector_versions={},
        timestamp=timestamp,
        metadata={}
    )

def test_engine_scenarios():
    engine = ConversationEngine()
    
    # Timeline sequence:
    # 0s: BANKING
    # 5s: OTP_REQUEST
    # 10s: OTP_REQUEST
    # 15s: REMOTE_ACCESS
    
    start_time = 1000.0
    r1 = create_report("Your card was blocked.", "BANKING", 0.9, start_time)
    r2 = create_report("What is the code?", "OTP_REQUEST", 0.8, start_time + 5.0)
    r3 = create_report("Read me the OTP.", "OTP_REQUEST", 0.95, start_time + 10.0)
    r4 = create_report("Download AnyDesk.", "REMOTE_ACCESS", 1.0, start_time + 15.0)
    
    engine.update(r1)
    engine.update(r2)
    engine.update(r3)
    snapshot = engine.update(r4)
    
    # Assert counts
    assert snapshot.intent_summary["BANKING"].count == 1
    assert snapshot.intent_summary["OTP_REQUEST"].count == 2
    assert snapshot.intent_summary["REMOTE_ACCESS"].count == 1
    
    # Dominant intent (OTP_REQUEST count=2 vs others count=1)
    assert snapshot.stats.dominant_intent == "OTP_REQUEST"
    
    # Check timeline length
    assert len(snapshot.timeline) == 4
    assert snapshot.timeline[0].intent == "BANKING"
    assert snapshot.timeline[1].intent == "OTP_REQUEST"
    assert snapshot.timeline[2].intent == "OTP_REQUEST"
    assert snapshot.timeline[3].intent == "REMOTE_ACCESS"
    
    # Verify phases progressed (since we have OTP/remote access, phase should be REQUEST or PRESSURE)
    # Since we have no urgency, phase should be REQUEST
    assert snapshot.phase == "REQUEST"

def test_engine_thread_safety():
    engine = ConversationEngine()
    
    # Update from 50 threads concurrently and check if counts match
    threads = []
    
    def worker(i: int):
        report = create_report(f"transcript {i}", "OTP_REQUEST", 0.9, 2000.0 + i)
        # Force the same call ID
        report.metadata["call_id"] = "shared_call"
        engine.update(report)
        
    for i in range(50):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    snapshot = engine.get_snapshot("shared_call")
    assert snapshot is not None
    # All 50 should be inserted
    assert snapshot.stats.total_detections == 50
    assert snapshot.intent_summary["OTP_REQUEST"].count == 50
