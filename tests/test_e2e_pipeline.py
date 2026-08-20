import pytest
import numpy as np
import base64
import json
from fastapi.testclient import TestClient
from app.app import app
from app.speakers.diarization import SpeakerDiarizer
from app.conversation.state_machine import sentinel_app
from app.risk.rule_engine import OTPDetectionAgent, EmotionalManipulationAgent, SocialEngineeringPredictorAgent

@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.fixture
def synthetic_audio_data():
    """Generates distinct synthetic audio samples for Owner and Scammer."""
    sr = 16000
    t = np.linspace(0, 1.0, sr, endpoint=False)
    
    # Owner: 140 Hz base pitch + harmonic formants
    owner_audio = (
        0.5 * np.sin(2 * np.pi * 140 * t) +
        0.3 * np.sin(2 * np.pi * 280 * t) +
        0.2 * np.sin(2 * np.pi * 500 * t) +
        0.15 * np.sin(2 * np.pi * 1500 * t)
    ) * 10000
    
    # Caller / Scammer: 240 Hz base pitch + high-frequency harmonics
    caller_audio = (
        0.5 * np.sin(2 * np.pi * 240 * t) +
        0.35 * np.sin(2 * np.pi * 480 * t) +
        0.25 * np.sin(2 * np.pi * 800 * t) +
        0.2 * np.sin(2 * np.pi * 2200 * t)
    ) * 10000
    
    return {
        "owner_pcm": owner_audio.astype(np.int16),
        "caller_pcm": caller_audio.astype(np.int16)
    }

# ---------------------------------------------------------------------------
# Stage 1: Multi-Biometric Diarization Verification
# ---------------------------------------------------------------------------
def test_e2e_speaker_biometrics(synthetic_audio_data):
    diarizer = SpeakerDiarizer()
    owner_pcm = synthetic_audio_data["owner_pcm"]
    caller_pcm = synthetic_audio_data["caller_pcm"]
    
    # 1. Enroll Owner Voiceprint
    diarizer.enroll_voiceprint(owner_pcm)
    assert diarizer.enrolled_voiceprint is not None
    
    # 2. Verify Owner Identification & High Match Score
    owner_role = diarizer.identify_audio_speaker(owner_pcm, threshold=0.75)
    owner_sim = diarizer.get_similarity_score(owner_pcm)
    assert owner_role == "VICTIM"  # VICTIM / OWNER
    assert owner_sim >= 0.85
    
    # 3. Verify Caller / Unknown Speaker Separation
    caller_role = diarizer.identify_audio_speaker(caller_pcm, threshold=0.75)
    caller_sim = diarizer.get_similarity_score(caller_pcm)
    assert caller_role == "CALLER"
    assert caller_sim < 0.75

# ---------------------------------------------------------------------------
# Stage 2: Sub-50ms Fast-Path Emergency Interception
# ---------------------------------------------------------------------------
def test_e2e_fast_path_detection():
    otp_agent = OTPDetectionAgent()
    
    # Critical OTP phishing demand
    urgent_demand = "Please read me the 6-digit verification code sent to your phone right now."
    res = otp_agent.analyze(urgent_demand)
    assert res.score >= 0.90
    assert "OTP_DEMAND" in res.detected_tactics
    
    # Benign conversation
    benign_text = "Hello, how is the weather today?"
    res_benign = otp_agent.analyze(benign_text)
    assert res_benign.score == 0.0

# ---------------------------------------------------------------------------
# Stage 3: LangGraph Multi-Agent Conversation State Machine Flow
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_e2e_langgraph_multi_agent_conversation_flow():
    session_id = "e2e_test_session_99"
    
    # Turn 1: CALLER establishes high threat
    turn1_state = {
        "session_id": session_id,
        "latest_transcript": "This is Officer David from the Fraud Department. An arrest warrant will be issued if you do not transfer funds.",
        "speaker": "CALLER",
        "transcripts": [],
        "fast_path_alert": False,
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
    res1 = await sentinel_app.ainvoke(turn1_state)
    assert res1["overall_risk_score"] >= 0.85
    assert res1["risk_level"] in ["HIGH", "CRITICAL"]
    assert res1["speaker"] == "CALLER"
    assert len(res1["detected_tactics"]) > 0
    assert len(res1["recommended_action"]) > 0
    
    # Turn 2: OWNER speaks inquiry (Must NOT be flagged as scammer)
    turn2_state = {
        "session_id": session_id,
        "latest_transcript": "Why are you calling me? What code are you talking about?",
        "speaker": "OWNER",
        "transcripts": [],
        "fast_path_alert": False,
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
    res2 = await sentinel_app.ainvoke(turn2_state)
    assert res2["overall_risk_score"] == 0.0
    assert res2["risk_level"] == "LOW"
    assert "User (Owner) speaking" in res2["explanation"]

    # Turn 3: CALLER executes critical OTP & isolation demand
    turn3_state = {
        "session_id": session_id,
        "latest_transcript": "Do not hang up! Read me the one-time password code on your screen in 2 minutes.",
        "speaker": "CALLER",
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
    res3 = await sentinel_app.ainvoke(turn3_state)
    assert res3["overall_risk_score"] >= 0.90
    assert res3["risk_level"] == "CRITICAL"
    assert "OTP_DEMAND" in res3["detected_tactics"] or "HIGH_PRESSURE_URGENCY" in res3["detected_tactics"]

# ---------------------------------------------------------------------------
# Stage 4: REST API & Live WebSocket Client Integration
# ---------------------------------------------------------------------------
def test_e2e_rest_and_websocket_pipeline(test_client, synthetic_audio_data):
    owner_pcm = synthetic_audio_data["owner_pcm"]
    owner_b64 = base64.b64encode(owner_pcm.tobytes()).decode("utf-8")
    
    # 1. Test Voice Enrollment REST Endpoint
    enroll_resp = test_client.post(
        "/api/v1/voice/enroll",
        json={"audio_base64": owner_b64, "user_name": "TestOwner"}
    )
    assert enroll_resp.status_code == 200
    enroll_data = enroll_resp.json()
    assert enroll_data["status"] == "success"
    assert enroll_data["is_enrolled"] is True
    
    # 2. Test Voice Status REST Endpoint
    status_resp = test_client.get("/api/v1/voice/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["is_enrolled"] is True
    
    # 3. Test Live WebSocket Stream with Bidirectional Turn Ingestion
    session_id = "test_live_ws_session_88"
    with test_client.websocket_connect(f"/ws/live/{session_id}") as websocket:
        # Send Owner Turn with Audio
        websocket.send_json({
            "transcript": "Hello, this is my phone. Who is calling?",
            "audio_b64": owner_b64
        })
        msg1 = websocket.receive_json()
        assert msg1["type"] == "threat_update"
        assert msg1["speaker"] == "OWNER"
        assert msg1["risk_score"] == 0.0
        assert msg1["voice_match_score"] >= 75
        
        # Send Caller Threat Turn
        caller_pcm = synthetic_audio_data["caller_pcm"]
        caller_b64 = base64.b64encode(caller_pcm.tobytes()).decode("utf-8")
        websocket.send_json({
            "transcript": "This is Bank of America fraud division. Confirm your 6-digit PIN immediately.",
            "audio_b64": caller_b64
        })
        msg2 = websocket.receive_json()
        assert msg2["type"] == "threat_update"
        assert msg2["speaker"] == "CALLER"
        assert msg2["risk_score"] >= 0.85
        assert msg2["risk_level"] in ["HIGH", "CRITICAL"]
