from pathlib import Path
from app.detection.detectors.pattern_detector import PatternDetector

def test_pattern_detector_scenarios():
    db_dir = Path(__file__).parent.parent / "patterns" / "database"
    detector = PatternDetector(database_dir=db_dir)
    detector.initialize()
    
    # OTP Request Test
    otp_transcript = "Please tell me the verification code."
    otp_detections = detector.detect(otp_transcript)
    assert len(otp_detections) > 0
    assert any(d.intent == "OTP_REQUEST" for d in otp_detections)
    
    # Remote Access Test
    remote_transcript = "Install AnyDesk now."
    remote_detections = detector.detect(remote_transcript)
    assert len(remote_detections) > 0
    assert any(d.intent == "REMOTE_ACCESS" for d in remote_detections)
    
    # Banking blocked Test
    banking_transcript = "Your bank account has been blocked."
    banking_detections = detector.detect(banking_transcript)
    assert len(banking_detections) > 0
    assert any(d.intent == "BANKING_FRAUD" for d in banking_detections)
    
    # Clean text
    clean_transcript = "The weather is beautiful today."
    clean_detections = detector.detect(clean_transcript)
    assert len(clean_detections) == 0
