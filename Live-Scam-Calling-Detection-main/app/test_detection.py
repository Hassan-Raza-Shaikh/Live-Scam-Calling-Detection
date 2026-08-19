"""
test_detection.py

Purpose:
    Interactive CLI tool to test the modular Detection Engine.
    Processes user input text, runs the detection pipeline, and prints structured reports.

Run:
    python -m app.test_detection
"""

import sys
from app.detection.engine import DetectionEngine

def print_banner():
    print("=" * 60)
    print("🕵️  Scam Detection Framework Interactive CLI Test")
    print("=" * 60)
    print("Type a sentence to test or press CTRL+C / CTRL+D to exit.")
    print("=" * 60)
    print()

def main():
    try:
        engine = DetectionEngine()
    except Exception as e:
        print(f"❌ Failed to initialize DetectionEngine: {str(e)}")
        sys.exit(1)

    print_banner()

    try:
        while True:
            try:
                text = input("> ")
            except (KeyboardInterrupt, EOFError):
                print("\n\nExiting. Goodbye!")
                break

            if not text.strip():
                continue

            report = engine.detect(text)
            
            print("\n--- Detection Report ---")
            print(f"Original Transcript  : '{report.original_transcript}'")
            print(f"Normalized Transcript: '{report.normalized_transcript}'")
            print(f"Processing Time (ms) : {report.processing_time_ms:.4f} ms")
            print(f"Active Detectors     : {', '.join(report.detector_versions.keys())}")
            
            if report.detections:
                print(f"🚨 Detections ({len(report.detections)} found):")
                for idx, detection in enumerate(report.detections, 1):
                    print(f"  {idx}. Intent            : {detection.intent}")
                    print(f"     Matched Text      : '{detection.matched_text}'")
                    print(f"     Strategy          : {detection.matching_strategy}")
                    print(f"     Matched Rule      : '{detection.matched_rule}'")
                    print(f"     Weight / Conf     : weight={detection.weight}, conf={detection.confidence}")
                    print(f"     Offsets (Char)    : [{detection.start_index}:{detection.end_index}]")
                    print(f"     Source File       : {detection.source_file}")
            else:
                print("✅ No detections.")
            print("-" * 24 + "\n")

    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
