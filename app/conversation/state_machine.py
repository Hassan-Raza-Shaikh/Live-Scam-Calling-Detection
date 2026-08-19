from typing import Dict, Any
from langgraph.graph import StateGraph, END
from app.conversation.context import GraphState
from app.preprocessing.cleaner import PIIMasker
from app.detection.engine import DetectionEngine
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Built ONCE when the app starts — loads all 8 YAML scam-pattern files
_detection_engine = DetectionEngine()

async def workflow_supervisor_node(state: GraphState) -> GraphState:
    """Entry node: Preprocesses incoming transcript and routes to supervisor workflow."""
    raw_text = state.get("latest_transcript", "")
    masked_text = PIIMasker.mask(raw_text)
    state["latest_transcript"] = masked_text
    state["next_node"] = "memory_supervisor"
    return state

async def memory_supervisor_node(state: GraphState) -> GraphState:
    """Manages transcript history and appends latest masked segment."""
    transcripts = state.get("transcripts", [])
    transcripts.append({"text": state.get("latest_transcript"), "role": "CALLER"})
    state["transcripts"] = transcripts
    state["next_node"] = "workers_execution"
    return state

async def workers_execution_node(state: GraphState) -> GraphState:
    """Runs the REAL 8-category scam pattern detector on the latest transcript."""
    text = state.get("latest_transcript", "")
    worker_results = state.get("worker_results", {})

    report = _detection_engine.detect(text)

    # DEBUG LINE — watch your terminal when you send a phrase.
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
            "matched_phrases": matched_words
        }
    else:
        worker_results["pattern_detection_agent"] = {
            "agent_name": "pattern_detection_agent",
            "score": 0.0,
            "confidence": 0.9,
            "detected_tactics": [],
            "matched_phrases": []
        }

    state["worker_results"] = worker_results
    return state

async def consensus_supervisor_node(state: GraphState) -> GraphState:
    """Aggregates worker signals into a coherent hypothesis."""
    results = state.get("worker_results", {})
    max_score = max([res.get("score", 0.0) for res in results.values()], default=0.0)

    tactics = []
    for res in results.values():
        tactics.extend(res.get("detected_tactics", []))

    state["detected_tactics"] = list(set(tactics))
    state["consensus_hypothesis"] = f"Multi-worker consensus calculated max risk score of {max_score:.2f}."
    return state

async def decision_supervisor_node(state: GraphState) -> GraphState:
    """Calculates final risk score, risk level, and generates user guidance."""
    results = state.get("worker_results", {})
    scores = [res.get("score", 0.0) for res in results.values()]
    avg_score = sum(scores) / len(scores) if scores else 0.0
    max_score = max(scores, default=0.0)

    final_score = (max_score * 0.7) + (avg_score * 0.3)
    state["overall_risk_score"] = round(final_score, 2)

    tactics_str = ", ".join(state.get("detected_tactics", [])) or "none"

    if final_score >= 0.75:
        state["risk_level"] = "CRITICAL" if final_score >= 0.90 else "HIGH"
        state["explanation"] = f"High probability scam call detected. Tactics identified: {tactics_str}."
        state["recommended_action"] = "DO NOT SHARE CODES OR TRANSFER MONEY. HANG UP IMMEDIATELY AND CALL OFFICIAL BANK NUMBER."
    elif final_score >= 0.45:
        state["risk_level"] = "MEDIUM"
        state["explanation"] = f"Suspicious requests detected during call. Tactics identified: {tactics_str}."
        state["recommended_action"] = "Verify caller identity before sharing any personal or financial information."
    else:
        state["risk_level"] = "LOW"
        state["explanation"] = "No scam indicators currently detected."
        state["recommended_action"] = "No action required."

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