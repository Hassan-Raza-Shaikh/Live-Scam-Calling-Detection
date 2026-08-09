import pytest
import numpy as np
from app.vad.silero import SileroVADEngine
from app.speakers.diarization import SpeakerDiarizer

def test_silero_vad():
    engine = SileroVADEngine()
    # Test empty or small buffer behavior
    assert not engine.is_speech(b"")
    
    # Test mock speech audio (represented by RMS calculation)
    # Generate high amplitude numpy array for "active speech" mock
    speech_pcm = np.random.randint(-16000, 16000, 16000, dtype=np.int16).tobytes()
    assert engine.is_speech(speech_pcm)

def test_speaker_diarizer():
    diarizer = SpeakerDiarizer()
    assert diarizer.process_frame(b"", channel=0) == "CALLER"
    assert diarizer.process_frame(b"", channel=1) == "RECEIVER"
