"""
test_conversation.py

Purpose:
    Demo script to feed synthetic DetectionReports to the ConversationEngine
    and print the resulting ConversationSnapshot and formatted summaries.

Run:
    python -m app.test_conversation
"""

import time
from app.conversation.engine import ConversationEngine
from app.conversation.summarizer import StructuredSummarizer
from app.detection.models import DetectionReport, Detection

def create_synthetic_report(
    transcript: str, 
    intent: str, 
    confidence: float, 
    weight: int, 
    offset_sec: float,
    call_id: str
) -> DetectionReport:
    """Helper to construct synthetic DetectionReports simulating pipeline outputs."""
    timestamp = 1700000000.0 + offset_sec
    detection = Detection(
        intent=intent,
        matched_text=transcript.split()[-1].replace(".", ""),
        matched_rule=f"dummy_{intent.lower()}",
        confidence=confidence,
        weight=weight,
        detector_name="PatternDetector",
        matching_strategy="phrase",
        start_index=0,
        end_index=len(transcript),
        source_file=f"{intent.lower()}.yaml",
        timestamp=timestamp
    )
    return DetectionReport(
        original_transcript=transcript,
        normalized_transcript=transcript.lower(),
        detections=[detection],
        processing_time_ms=0.5,
        detector_versions={"PatternDetector": "1.0.0"},
        timestamp=timestamp,
        metadata={"call_id": call_id}
    )

def main():
    print("=" * 60)
    print("📞 Conversation Context Engine Demo")
    print("=" * 60)
    print("Simulating a scam phone call timeline...")
    print()

    engine = ConversationEngine()
    summarizer = StructuredSummarizer()
    call_id = "demo_call_123"

    # Synthetic transcript flow:
    # 0s: Scammer starts with greeting
    # 10s: Scammer claims banking block (BANKING_FRAUD)
    # 25s: Scammer requests verification code (OTP_REQUEST)
    # 40s: Scammer repeats code request (OTP_REQUEST)
    # 55s: Scammer applies pressure to download remote software (REMOTE_ACCESS)
    
    scam_flow = [
        ("Hello, this is standard chartered support.", "IMPERSONATION", 0.95, 25, 0.0),
        ("Your bank account has been blocked due to suspicious activity.", "BANKING_FRAUD", 0.90, 30, 10.0),
        ("Please tell me the verification code sent to your mobile.", "OTP_REQUEST", 0.85, 35, 25.0),
        ("Read me the six digit code now.", "OTP_REQUEST", 0.98, 35, 40.0),
        ("You must install AnyDesk screen sharing immediately to secure funds.", "REMOTE_ACCESS", 1.0, 35, 55.0)
    ]

    for transcript, intent, confidence, weight, elapsed in scam_flow:
        print(f"\n[+{int(elapsed)}s] Incoming transcript segment:")
        print(f"  \"{transcript}\" (Intent: {intent})")
        
        report = create_synthetic_report(
            transcript=transcript,
            intent=intent,
            confidence=confidence,
            weight=weight,
            offset_sec=elapsed,
            call_id=call_id
        )
        
        # Update the engine
        snapshot = engine.update(report)
        
        # Print summary of snapshot
        print("\n--- Updated Snapshot Summary ---")
        summary_text = summarizer.summarize(snapshot)
        print(summary_text)
        print("-" * 40)
        time.sleep(1.0)  # Pause for readability

    print("\n✅ Simulation complete.")

if __name__ == "__main__":
    main()
