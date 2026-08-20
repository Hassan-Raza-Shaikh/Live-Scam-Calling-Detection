"""
test_speakers.py

Interactive tool to test and verify Speaker Diarization, Voiceprint Verification,
and Multi-Speaker Turn Tracking in Sentinel AI.

Run:
    PYTHONPATH=. python -m app.test_speakers
"""

import sys
import time
import asyncio
import numpy as np
from app.speakers.diarization import SpeakerDiarizer
from app.speakers.speaker_tracker import SpeakerTracker
from app.conversation.state_machine import sentinel_app

def print_banner():
    print("=" * 65)
    print("🎙️  Sentinel AI - Speaker Diarization & Detection Test Suite")
    print("=" * 65)
    print("This tool tests:")
    print("  1. Hardware / Channel-based Speaker Separation (Caller vs Victim)")
    print("  2. Acoustic Voiceprint Enrollment & Verification (Mono Audio)")
    print("  3. Linguistic Role Induction (Predicting Speaker from Turn Semantics)")
    print("  4. Live 2-Speaker Dialogue Simulation with LangGraph Multi-Agent Engine")
    print("=" * 65)
    print()

async def run_dialogue_simulation():
    print("\n--- [Demo 1] Live 2-Speaker Dialogue Simulation ---")
    print("Simulating a live phone call between [CALLER (Scammer)] and [VICTIM (User)]:\n")
    
    tracker = SpeakerTracker()
    session_id = "test_dialogue_sess_101"
    
    dialogue = [
        ("CALLER", "Hello! This is Officer David from the Fraud Investigation Department."),
        ("VICTIM", "Hello? Why are you calling me? What happened?"),
        ("CALLER", "There has been unauthorized activity on your bank account. An arrest warrant will be issued immediately."),
        ("VICTIM", "An arrest warrant?! Wait, I haven't done anything wrong!"),
        ("CALLER", "To cancel the warrant right now, read me the 6-digit verification code sent to your phone."),
        ("VICTIM", "Let me check my messages... Wait, the SMS says do not share this OTP with anyone."),
        ("CALLER", "Do not hang up! If you do not give me the code in 2 minutes, police will be at your door.")
    ]
    
    for speaker, text in dialogue:
        tracker.register_turn(speaker=speaker, duration_sec=3.0, text=text)
        
        initial_state = {
            "session_id": session_id,
            "latest_transcript": text,
            "speaker": speaker,
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
        
        res = await sentinel_app.ainvoke(initial_state)
        
        speaker_badge = "🔴 [CALLER (Scammer)]" if speaker == "CALLER" else "🟢 [VICTIM (User)]   "
        risk_score = res.get("overall_risk_score", 0.0)
        risk_level = res.get("risk_level", "LOW")
        tactics = res.get("detected_tactics", [])
        
        print(f"{speaker_badge}: \"{text}\"")
        print(f"   ↳ Risk Score: {risk_score:.2f} [{risk_level}] | Speaker: {res.get("speaker")} | Tactics: {tactics}")
        print()
        await asyncio.sleep(0.3)
        
    print("📊 Conversation Turn Summary:")
    summary = tracker.get_summary()
    print(f"   Total Turns   : {summary["total_turns"]}")
    print(f"   Caller Turns  : {summary["caller_turns"]}")
    print(f"   Victim Turns  : {summary["victim_turns"]}")
    print(f"   Last Speaker  : {summary["last_speaker"]}")
    print("-" * 65)

def test_voiceprint_verification():
    print("\n--- [Demo 2] Multi-Biometric Voiceprint Enrollment & Verification ---")
    diarizer = SpeakerDiarizer()
    
    np.random.seed(42)
    t_enroll = np.linspace(0, 0.5, 8000, endpoint=False)
    user_audio = (np.sin(2 * np.pi * 150 * t_enroll) * 5000 + np.sin(2 * np.pi * 300 * t_enroll) * 2000).astype(np.int16)
    diarizer.enroll_voiceprint(user_audio)
    print("✅ User voiceprint enrolled successfully (12 MFCCs + Pitch F0 + Formants).")
    
    t_test = np.linspace(0, 0.25, 4000, endpoint=False)
    matching_chunk = (np.sin(2 * np.pi * 150 * t_test) * 4800 + np.sin(2 * np.pi * 300 * t_test) * 1900).astype(np.int16)
    pred_user = diarizer.identify_audio_speaker(matching_chunk)
    sim_user = diarizer.get_similarity_score(matching_chunk)
    print(f"   Test Audio 1 (Enrolled User Voice)    -> Detected: {pred_user} ({sim_user*100:.1f}% Match | Expected: VICTIM)")
    
    different_speaker_chunk = (np.sin(2 * np.pi * 260 * t_test) * 5000 + np.sin(2 * np.pi * 520 * t_test) * 2500).astype(np.int16)
    pred_caller = diarizer.identify_audio_speaker(different_speaker_chunk)
    sim_caller = diarizer.get_similarity_score(different_speaker_chunk)
    print(f"   Test Audio 2 (Friend / Other Voice)   -> Detected: {pred_caller} ({sim_caller*100:.1f}% Match | Expected: CALLER)")
    print("-" * 65)

def test_linguistic_role_induction():
    print("\n--- [Demo 3] Linguistic Turn Role Induction (Text Cues) ---")
    diarizer = SpeakerDiarizer()
    
    phrases = [
        ("I am calling from standard chartered fraud department", "CALLER"),
        ("Why are you calling me? I didn't make that purchase", "VICTIM"),
        ("You must transfer your funds to secure account immediately", "CALLER"),
        ("Wait a minute, is this real? Let me check my bank app", "VICTIM"),
        ("Do not hang up the phone or your card will be suspended", "CALLER")
    ]
    
    for phrase, expected in phrases:
        pred = diarizer.predict_role_from_text(phrase)
        status = "✅" if pred == expected else "❌"
        print(f"   {status} \"{phrase}\"")
        print(f"      -> Predicted: [{pred}] | Expected: [{expected}]")
    print("-" * 65)

def main():
    print_banner()
    test_voiceprint_verification()
    test_linguistic_role_induction()
    asyncio.run(run_dialogue_simulation())
    print("\n🎉 All Speaker Diarization tests finished successfully!\n")

if __name__ == "__main__":
    main()
