from typing import Dict, Any
from langgraph.graph import StateGraph, END
from app.conversation.context import GraphState
from app.preprocessing.cleaner import PIIMasker

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
    """Executes parallel worker detection analysis (OTP, Scam, Urgency, Org Lookup)."""
    text = state.get("latest_transcript", "").lower()
    worker_results = state.get("worker_results", {})
    
    # 1. OTP Detector Worker
    otp_detected = any(k in text for k in ["verification code", "6-digit code", "otp", "code sent to your phone"])
    worker_results["otp_detection_agent"] = {
        "agent_name": "otp_detection_agent",
        "score": 0.95 if otp_detected else 0.0,
        "confidence": 0.9,
        "detected_tactics": ["OTP_DEMAND"] if otp_detected else []
    }
    
    # 2. Banking / Scam Detection Worker
    scam_detected = any(k in text for k in ["fraud department", "transfer money", "safe account", "account freeze", "microsoft support"])
    worker_results["scam_detection_agent"] = {
        "agent_name": "scam_detection_agent",
        "score": 0.90 if scam_detected else 0.0,
        "confidence": 0.85,
        "detected_tactics": ["IMPERSONATION_BANK", "FUNDS_TRANSFER_DEMAND"] if scam_detected else []
    }
    
    # 3. Urgency Worker
    urgency_detected = any(k in text for k in ["immediately", "right now", "within 5 minutes", "police warrant"])
    worker_results["urgency_detection_agent"] = {
        "agent_name": "urgency_detection_agent",
        "score": 0.85 if urgency_detected else 0.1,
        "confidence": 0.8,
        "detected_tactics": ["HIGH_PRESSURE_URGENCY"] if urgency_detected else []
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
    
    # Weighted calculation
    final_score = (max_score * 0.7) + (avg_score * 0.3)
    state["overall_risk_score"] = round(final_score, 2)
    
    if final_score >= 0.75:
        state["risk_level"] = "CRITICAL" if final_score >= 0.90 else "HIGH"
        state["explanation"] = "High probability scam call detected! Caller is using high urgency or demanding verification credentials."
        state["recommended_action"] = "DO NOT SHARE CODES OR TRANSFER MONEY. HANG UP IMMEDIATELY AND CALL OFFICIAL BANK NUMBER."
    elif final_score >= 0.45:
        state["risk_level"] = "MEDIUM"
        state["explanation"] = "Suspicious requests detected during call. Exercise caution."
        state["recommended_action"] = "Verify caller identity before sharing any personal or financial information."
    else:
        state["risk_level"] = "LOW"
        state["explanation"] = "No scam indicators currently detected."
        state["recommended_action"] = "No action required."

    return state

def build_sentinel_graph():
    """Builds and compiles the Sentinel AI LangGraph Supervisor-Worker state machine."""
    workflow = StateGraph(GraphState)
    
    # Add Nodes
    workflow.add_node("workflow_supervisor", workflow_supervisor_node)
    workflow.add_node("memory_supervisor", memory_supervisor_node)
    workflow.add_node("workers_execution", workers_execution_node)
    workflow.add_node("consensus_supervisor", consensus_supervisor_node)
    workflow.add_node("decision_supervisor", decision_supervisor_node)
    
    # Define Edges
    workflow.set_entry_point("workflow_supervisor")
    workflow.add_edge("workflow_supervisor", "memory_supervisor")
    workflow.add_edge("memory_supervisor", "workers_execution")
    workflow.add_edge("workers_execution", "consensus_supervisor")
    workflow.add_edge("consensus_supervisor", "decision_supervisor")
    workflow.add_edge("decision_supervisor", END)
    
    return workflow.compile()

# Global compiled sentinel graph instance
sentinel_app = build_sentinel_graph()
