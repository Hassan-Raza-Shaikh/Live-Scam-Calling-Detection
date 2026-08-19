import pytest
from app.phrases.matcher import PhraseMatcher

def test_phrase_matcher():
    matcher = PhraseMatcher()
    matched = matcher.match_phrases("your account has been suspended due to suspicious activity")
    assert len(matched) > 0
    assert "suspicious activity" in matched[0]
