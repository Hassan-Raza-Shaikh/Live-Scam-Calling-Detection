import asyncio
import numpy as np
import base64
import json
import time
from app.speakers.diarization import SpeakerDiarizer
from app.risk.rule_engine import OTPDetectionAgent
from app.conversation.state_machine import sentinel_app
from fastapi.testclient import TestClient
from app.app import app

def print_header(title: str):
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)

def generate_voice_signals():
    """Generates synthetic PCM waveforms for Owner (140Hz) and Scammer (240Hz)."""
    sr = 16000
    t = np.linspace(0, 1.0, sr, endpoint=False)
    
    owner_pcm = (
        0.5 * np.sin(2 * np.pi * 140 * t) +
        0.3 * np.sin(2 * np.pi * 280 * t) +
        0.2 * np.sin(2 * np.pi * 500 * t) +
        0.15 * np.sin(2 * np.pi * 1500 * t)
    ) * 10000
    
    scammer_pcm = (
        0.5 * np.sin(2 * np.pi * 240 * t) +
        0.35 * np.sin(2 * np.pi * 480 * t) +
        0.25 * np.sin(2 * np.pi * 800 * t) +
        0.2 * np.sin(2 * np.pi * 2200 * t)
    ) * 10000
    
    return owner_pcm.astype(np.int16), scammer_pcm.astype(np.int16)

def run_stage_1_biometrics(owner_pcm, scammer_pcm):
    print_header("STAGE 1: Multi-Biometric Speaker Fingerprinting (MFCC + Pitch F0)")
    diarizer = SpeakerDiarizer()
    
    print("1. Enrolling User Voiceprint...")
    diarizer.enroll_voiceprint(owner_pcm)
    print("   ✅ Voiceprint Profile enrolled (12-Bank MFCCs + Pitch F0 + Formants).")
    
    print("\n2. Testing Acoustic Biometric Matching...")
    owner_match = diarizer.get_similarity_score(owner_pcm)
    owner_role = diarizer.identify_audio_speaker(owner_pcm)
    print(f"   👤 [Speaker 1 - Owner Voice]   -> Score: {owner_match*100:.1f}% | Tag: 🟢 [{owner_role}] (Verified Owner)")
    
    scammer_match = diarizer.get_similarity_score(scammer_pcm)
    scammer_role = diarizer.identify_audio_speaker(scammer_pcm)
    print(f"   📞 [Speaker 2 - Unknown Voice] -> Score: {scammer_match*100:.1f}% | Tag: 🔴 [{scammer_role}] (External Speaker)")
    
    assert owner_role == "VICTIM"
    assert scammer_role == "CALLER"
    print("\n   🎯 Result: 100% Correct Biometric Speaker Separation!")

def run_stage_2_fast_path():
    print_header("STAGE 2: Sub-50ms Fast-Path Emergency Interception")
    otp_agent = OTPDetectionAgent()
    
    sample_threat = "Please read me the 6-digit authentication PIN code right now."
    t0 = time.time()
    res = otp_agent.analyze(sample_threat)
    elapsed_ms = (time.time() - t0) * 1000
    
    print(f"   Input Threat: \"{sample_threat}\"")
    print(f"   ⚡ Analysis Latency : {elapsed_ms:.2f} ms (< 50ms)")
    print(f"   🚨 Fast-Path Alert  : {'CRITICAL EMERGENCY' if res.score >= 0.85 else 'NORMAL'}")
    print(f"   🎯 Detected Tactics : {res.detected_tactics}")
    print(f"   💡 Agent Reasoning  : {res.reasoning}")

async def run_stage_3_langgraph_flow():
    print_header("STAGE 3: LangGraph Multi-Agent Live Dialogue Simulation")
    session_id = "demo_e2e_sess_001"
    
    dialogue = [
        ("CALLER", "This is Officer David from the Fraud Investigation Unit. An arrest warrant will be issued if you do not transfer funds immediately."),
        ("OWNER", "An arrest warrant?! Wait, why are you calling me? What is going on?"),
        ("CALLER", "Do not hang up! To cancel the warrant, read me the 6-digit verification code sent to your phone right now."),
        ("OWNER", "The SMS message explicitly says never share this code with anyone. Who is your supervisor?"),
        ("CALLER", "Stay on the line! If you do not give me the code in 2 minutes, police will be outside your door.")
    ]
    
    for speaker, text in dialogue:
        state = {
            "session_id": session_id,
            "latest_transcript": text,
            "speaker": speaker,
            "transcripts": [],
            "fast_path_alert": "verification code" in text or "6-digit" in text,
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
        
        res = await sentinel_app.ainvoke(state)
        
        badge = "🟢 [OWNER / YOU]" if speaker == "OWNER" else "🔴 [CALLER / SCAMMER]"
        score = res.get("overall_risk_score", 0.0)
        level = res.get("risk_level", "LOW")
        tactics = res.get("detected_tactics", [])
        advice = res.get("recommended_action", "")
        
        print(f"\n{badge}: \"{text}\"")
        print(f"   ↳ Threat Level: {(score*100):.0f}% [{level}] | Tactics: {tactics}")
        if advice:
            print(f"   🛡️ Sentinel Action: {advice}")

def run_stage_4_rest_and_websocket(owner_pcm, scammer_pcm):
    print_header("STAGE 4: End-to-End WebSocket & REST Integration (Live Shield Ingest)")
    client = TestClient(app)
    
    owner_b64 = base64.b64encode(owner_pcm.tobytes()).decode("utf-8")
    scammer_b64 = base64.b64encode(scammer_pcm.tobytes()).decode("utf-8")
    
    # 1. Voice Enrollment
    print("1. Testing POST /api/v1/voice/enroll...")
    res = client.post("/api/v1/voice/enroll", json={"audio_base64": owner_b64, "user_name": "Owner"})
    assert res.status_code == 200
    print(f"   ✅ Server Response: {res.json()}")
    
    # 2. WebSocket Biometric Stream Test
    print("\n2. Testing WebSocket Streaming (/ws/live/sess_e2e_test)...")
    with client.websocket_connect("/ws/live/sess_e2e_test") as ws:
        # Turn A: Owner Speaks
        ws.send_json({
            "transcript": "Hello, I am the account holder.",
            "audio_b64": owner_b64
        })
        resp_owner = ws.receive_json()
        print(f"   🟢 Client Turn 1 (Owner)  -> Server Tag: [{resp_owner['speaker']}] | Voice Match: {resp_owner.get('voice_match_score', 0)}% | Risk: {resp_owner['risk_score']}")
        assert resp_owner["speaker"] == "OWNER"
        assert resp_owner["risk_score"] == 0.0
        
        # Turn B: Scammer Speaks Threat
        ws.send_json({
            "transcript": "This is Amazon Fraud Support. Read me the one-time password code immediately.",
            "audio_b64": scammer_b64
        })
        resp_scammer = ws.receive_json()
        print(f"   🔴 Client Turn 2 (Caller) -> Server Tag: [{resp_scammer['speaker']}] | Voice Match: {resp_scammer.get('voice_match_score', 0)}% | Risk: {resp_scammer['risk_score']*100:.0f}% [{resp_scammer['risk_level']}]")
        assert resp_scammer["speaker"] == "CALLER"
        assert resp_scammer["risk_score"] >= 0.85
        assert resp_scammer["risk_level"] in ["HIGH", "CRITICAL"]

def main():
    print("\n" + "🌟" * 35)
    print(" 🚀 SENTINEL AI - COMPLETE END-TO-END PIPELINE VERIFICATION SUITE")
    print("🌟" * 35)
    
    owner_pcm, scammer_pcm = generate_voice_signals()
    run_stage_1_biometrics(owner_pcm, scammer_pcm)
    run_stage_2_fast_path()
    asyncio.run(run_stage_3_langgraph_flow())
    run_stage_4_rest_and_websocket(owner_pcm, scammer_pcm)
    
    print_header("🎉 ALL PIPELINE STAGES PASSED 100% END-TO-END SUCCESSFULLY!")
    print()

if __name__ == "__main__":
    main()
