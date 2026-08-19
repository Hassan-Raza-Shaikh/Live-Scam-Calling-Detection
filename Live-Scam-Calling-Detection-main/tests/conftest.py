import pytest

@pytest.fixture
def sample_scam_transcript():
    return "This is Chase Bank fraud department. Please provide the 6-digit verification code sent to your phone."

@pytest.fixture
def sample_safe_transcript():
    return "Hi, just calling to see if we are still meeting for dinner tonight at 7 PM."
