"""
test_asr.py

Purpose:
    Verify that the streaming ASR pipeline is functioning correctly.

Checks:
    1. Model loads successfully
    2. Microphone captures audio
    3. Partial transcripts are produced
    4. Final transcripts are produced
    5. Basic latency measurements

Run:
    python test_asr.py
"""

import time
import traceback

from app.audio.recorder import AudioRecorder
from app.asr.sherpa import ASRService


def print_banner():
    print("=" * 60)
    print("🎤 Real-Time Streaming ASR Test")
    print("=" * 60)
    print()


def main():

    print_banner()

    ##################################################
    # Load ASR
    ##################################################

    try:
        print("Loading Sherpa model...")

        asr = ASRService()

        print("✅ Sherpa initialized successfully\n")

    except Exception as e:

        print("❌ Failed to initialize Sherpa\n")

        traceback.print_exc()

        return

    ##################################################
    # Initialize microphone
    ##################################################

    try:

        recorder = AudioRecorder()

        print("✅ Microphone initialized\n")

    except Exception:

        print("❌ Failed to initialize microphone\n")

        traceback.print_exc()

        return

    ##################################################
    # Start listening
    ##################################################

    print("=" * 60)
    print("🎙️ Listening...")
    print("Press CTRL+C to stop.")
    print("=" * 60)

    previous_text = ""

    chunk_count = 0

    total_processing_time = 0.0

    try:

        for chunk in recorder.stream():

            start = time.perf_counter()

            transcript = asr.process_audio(chunk)

            elapsed = (time.perf_counter() - start) * 1000

            total_processing_time += elapsed

            chunk_count += 1

            ##################################################
            # Print only when transcript changes
            ##################################################

            if transcript and transcript != previous_text:

                previous_text = transcript

                print()

                print(f"📝 {transcript}")

                print(f"⚡ Processing Time: {elapsed:.2f} ms")

    except KeyboardInterrupt:

        print()

        print("=" * 60)
        print("Stopping...")

    finally:

        print()

        print("=" * 60)

        print("Session Summary")

        print("=" * 60)

        if chunk_count > 0:

            avg = total_processing_time / chunk_count

            print(f"Chunks Processed : {chunk_count}")
            print(f"Average Processing Time : {avg:.2f} ms")

        print()

        print("Test completed.")


if __name__ == "__main__":
    main()