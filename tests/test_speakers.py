import pytest
import numpy as np
from app.speakers.diarization import SpeakerDiarizer
from app.speakers.speaker_tracker import SpeakerTracker

def test_speaker_diarizer_channels():
    diarizer = SpeakerDiarizer()
    assert diarizer.process_frame(channel=0) == "CALLER"
    assert diarizer.process_frame(channel=1) == "RECEIVER"

def test_speaker_diarizer_voiceprint():
    diarizer = SpeakerDiarizer()
    np.random.seed(42)
    sr = 16000
    t_enroll = np.linspace(0, 0.5, 8000, endpoint=False)
    user_samples = (np.sin(2 * np.pi * 150 * t_enroll) * 5000 + np.sin(2 * np.pi * 300 * t_enroll) * 2000).astype(np.int16)
    diarizer.enroll_voiceprint(user_samples)
    assert diarizer.enrolled_voiceprint is not None

    # Similar voice (same pitch & harmonics)
    t_test = np.linspace(0, 0.25, 4000, endpoint=False)
    matching_chunk = (np.sin(2 * np.pi * 150 * t_test) * 4800 + np.sin(2 * np.pi * 300 * t_test) * 1900).astype(np.int16)
    assert diarizer.identify_audio_speaker(matching_chunk) == "VICTIM"

    # Different frequency / noise voice (e.g. 260Hz different speaker)
    different_chunk = (np.sin(2 * np.pi * 260 * t_test) * 5000 + np.sin(2 * np.pi * 520 * t_test) * 2500).astype(np.int16)
    assert diarizer.identify_audio_speaker(different_chunk) == "CALLER"

def test_speaker_diarizer_linguistic_role():
    diarizer = SpeakerDiarizer()
    assert diarizer.predict_role_from_text("This is Officer Miller from fraud department") == "CALLER"
    assert diarizer.predict_role_from_text("Why are you calling me? What is this code?") == "VICTIM"

def test_speaker_tracker():
    tracker = SpeakerTracker()
    tracker.register_turn("CALLER", 3.0, "Hello")
    tracker.register_turn("VICTIM", 2.0, "Who is this?")
    
    summary = tracker.get_summary()
    assert summary["total_turns"] == 2
    assert summary["caller_turns"] == 1
    assert summary["victim_turns"] == 1
    assert summary["last_speaker"] == "VICTIM"
