import pytest
from app.keywords.matcher import KeywordMatcher

def test_keyword_matcher():
    matcher = KeywordMatcher()
    
    # Test matching banking keywords
    matched = matcher.match("This is bank security department")
    assert "IMPERSONATION" in matched

    # Test matching OTP keywords
    matched = matcher.match("Please give me the otp verification code")
    assert "OTP_DEMAND" in matched
