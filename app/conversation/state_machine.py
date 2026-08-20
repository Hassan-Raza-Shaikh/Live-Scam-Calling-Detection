from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from app.conversation.context import GraphState
from app.preprocessing.cleaner import PIIMasker
from app.detection.engine import DetectionEngine
from app.risk.rule_engine import EmotionalManipulationAgent, SocialEngineeringPredictorAgent
from app.speakers.diarization import SpeakerDiarizer
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Specialized Multi-Agent Workers & Speaker Diarizer
_detection_engine = DetectionEngine()
_emotional_agent = EmotionalManipulationAgent()
_predictor_agent = SocialEngineeringPredictorAgent()
_speaker_diarizer = SpeakerDiarizer()

async def workflow_supervisor_node(state: GraphState) -> GraphState:
    """Entry node: Preprocesses incoming transcript, determines speaker role, and routes to supervisor workflow."""
    raw_text = state.get("latest_transcript", "")
    masked_text = PIIMasker.mask(raw_text)
    state["latest_transcript"] = masked_text
    
    # Identify or preserve speaker role (CALLER vs VICTIM)
    speaker = state.get("speaker")
    if not speaker:
        speaker = _speaker_diarizer.predict_role_from_text(raw_text)
        state["speaker"] = speaker
        
    state["next_node"] = "memory_supervisor"
    return state

async def memory_supervisor_node(state: GraphState) -> GraphState:
    """Manages transcript history and appends latest masked segment with speaker role."""
    transcripts = state.get("transcripts", [])
    speaker = state.get("speaker", "CALLER")
    transcripts.append({"text": state.get("latest_transcript"), "role": speaker})
    state["transcripts"] = transcripts
    state["next_node"] = "workers_execution"
    return state

async def workers_execution_node(state: GraphState) -> GraphState:
    """Executes multi-agent specialized workers concurrently across patterns, emotions, and predictions."""
    text = state.get("latest_transcript", "")
    transcripts = state.get("transcripts", [])
    worker_results = state.get("worker_results", {})

    # Worker 1: 8-Category Pattern Detection Engine
    report = _detection_engine.detect(text)
    logger.info(f"[DetectionEngine] text='{text}' -> Detections found: {len(report.detections)}")

    if report.detections:
        best_weight = max(d.weight for d in report.detections)
        score = min(1.0, best_weight / 40.0)
        tactics = sorted(set(d.intent for d in report.detections))
        matched_words = sorted(set(d.matched_text for d in report.detections))

        worker_results["pattern_detection_agent"] = {
            "agent_name": "pattern_detection_agent",
            "score": score,
            "confidence": 0.9,
            "detected_tactics": tactics,
            "matched_phrases": matched_words,
            "reasoning": f"Identified signature phrases: {matched_words[:3]}"
        }
    else:
        worker_results["pattern_detection_agent"] = {
            "agent_name": "pattern_detection_agent",
            "score": 0.0,
            "confidence": 0.9,
            "detected_tactics": [],
            "matched_phrases": [],
            "reasoning": "No signature pattern hits."
        }

    # Worker 2: Emotional & Psychological Manipulation Detector
    emo_res = _emotional_agent.analyze(text)
    worker_results["emotional_manipulation_agent"] = {
        "agent_name": emo_res.agent_name,
        "score": emo_res.score,
        "confidence": emo_res.confidence,
        "detected_tactics": emo_res.detected_tactics,
        "reasoning": emo_res.reasoning
    }

    # Worker 3: Social Engineering Trajectory Predictor
    pred_res = _predictor_agent.analyze(text, transcripts)
    worker_results["social_engineering_predictor"] = {
        "agent_name": pred_res.agent_name,
        "score": pred_res.score,
        "confidence": pred_res.confidence,
        "detected_tactics": pred_res.detected_tactics,
        "reasoning": pred_res.reasoning
    }

    state["worker_results"] = worker_results
    return state

async def consensus_supervisor_node(state: GraphState) -> GraphState:
    """Aggregates worker signals into a multi-agent consensus hypothesis."""
    results = state.get("worker_results", {})
    all_scores = [res.get("score", 0.0) for res in results.values()]
    max_score = max(all_scores, default=0.0)

    tactics = []
    reasonings = []
    for name, res in results.items():
        tactics.extend(res.get("detected_tactics", []))
        r = res.get("reasoning", "")
        if r and "No " not in r and "Normal " not in r:
            reasonings.append(r)

    state["detected_tactics"] = sorted(list(set(tactics)))
    state["consensus_hypothesis"] = " | ".join(reasonings) if reasonings else "Normal conversation with no elevated threat flags."
    return state

async def decision_supervisor_node(state: GraphState) -> GraphState:
    """Calculates final risk score, risk level, and generates actionable user safety guidance."""
    results = state.get("worker_results", {})
    scores = [res.get("score", 0.0) for res in results.values() if res.get("score", 0.0) > 0.0]

    if scores:
        max_score = max(scores)
        avg_score = sum(scores) / len(scores)
        final_score = (max_score * 0.75) + (avg_score * 0.25)
    else:
        final_score = 0.0

    speaker = state.get("speaker", "CALLER")
    tactics_str = ", ".join(state.get("detected_tactics", [])) or "none"
    consensus = state.get("consensus_hypothesis", "")

    # If the speaker is the legitimate user (Owner / Victim), do not attribute caller scam threat to them
    if speaker in ("OWNER", "VICTIM", "USER"):
        state["overall_risk_score"] = 0.0
        state["risk_level"] = "LOW"
        state["explanation"] = f"🟢 User (Owner) speaking: Sentinel AI is shielding your call."
        state["recommended_action"] = "Stay alert. Never read OTP codes, PINs, or download remote access tools for the caller."
        return state

    state["overall_risk_score"] = round(final_score, 2)

    if final_score >= 0.75:
        state["risk_level"] = "CRITICAL" if final_score >= 0.90 else "HIGH"
        state["explanation"] = f"Multi-Agent Threat Alert: {consensus}"
        state["recommended_action"] = "DO NOT SHARE CODES OR TRANSFER MONEY. HANG UP IMMEDIATELY AND CALL OFFICIAL BANK NUMBER."
    elif final_score >= 0.45:
        state["risk_level"] = "MEDIUM"
        state["explanation"] = f"Suspicious Activity Detected: {consensus}"
        state["recommended_action"] = "Verify caller identity before sharing any personal or financial information."
    else:
        state["risk_level"] = "LOW"
        state["explanation"] = "No scam indicators or psychological manipulation currently detected."
        state["recommended_action"] = "Monitoring active. Speak normally into your microphone."

    return state

def build_sentinel_graph():
    """Builds and compiles the Sentinel AI LangGraph Supervisor-Worker state machine."""
    workflow = StateGraph(GraphState)

    workflow.add_node("workflow_supervisor", workflow_supervisor_node)
    workflow.add_node("memory_supervisor", memory_supervisor_node)
    workflow.add_node("workers_execution", workers_execution_node)
    workflow.add_node("consensus_supervisor", consensus_supervisor_node)
    workflow.add_node("decision_supervisor", decision_supervisor_node)

    workflow.set_entry_point("workflow_supervisor")
    workflow.add_edge("workflow_supervisor", "memory_supervisor")
    workflow.add_edge("memory_supervisor", "workers_execution")
    workflow.add_edge("workers_execution", "consensus_supervisor")
    workflow.add_edge("consensus_supervisor", "decision_supervisor")
    workflow.add_edge("decision_supervisor", END)

    return workflow.compile()


sentinel_app = build_sentinel_graph()