from ai.agents.workers.otp_detection_agent import OTPDetectionAgent

def test_otp_detection_agent_positive(sample_scam_transcript):
    agent = OTPDetectionAgent()
    result = agent.analyze(sample_scam_transcript)
    assert result.score >= 0.85
    assert "OTP_DEMAND" in result.detected_tactics

def test_otp_detection_agent_negative(sample_safe_transcript):
    agent = OTPDetectionAgent()
    result = agent.analyze(sample_safe_transcript)
    assert result.score == 0.0
    assert len(result.detected_tactics) == 0
