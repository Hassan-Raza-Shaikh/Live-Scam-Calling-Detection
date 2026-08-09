import pytest
from app.preprocessing.cleaner import PIIMasker
from app.conversation.state_machine import sentinel_app

def test_card_and_otp_redaction():
    raw = "My card number is 4532-1234-5678-9012 and my code is 123456."
    masked = PIIMasker.mask(raw)
    assert "4532" not in masked
    assert "[CARD_NUMBER_REDACTED]" in masked
    assert "[6-DIGIT_CODE]" in masked

@pytest.mark.asyncio
async def test_sentinel_graph_execution(sample_scam_transcript):
    initial_state = {
        "session_id": "test_sess_001",
        "latest_transcript": sample_scam_transcript,
        "transcripts": [],
        "fast_path_alert": True,
        "worker_results": {},
        "retrieved_patterns": [],
        "verified_organizations": [],
        "consensus_hypothesis": "",
        "overall_risk_score": 0.0,
        "risk_level": "LOW",
        "detected_tactics": [],
        "explanation": "",
        "recommended_action": "",
        "next_node": ""
    }
    
    final_state = await sentinel_app.ainvoke(initial_state)
    assert final_state["overall_risk_score"] > 0.5
    assert final_state["risk_level"] in ["HIGH", "CRITICAL"]
