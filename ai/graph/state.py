from typing import TypedDict, List, Dict, Any, Optional

class GraphState(TypedDict):
    session_id: str
    transcripts: List[Dict[str, Any]]
    latest_transcript: str
    fast_path_alert: bool
    worker_results: Dict[str, Dict[str, Any]]
    retrieved_patterns: List[Dict[str, Any]]
    verified_organizations: List[Dict[str, Any]]
    consensus_hypothesis: str
    overall_risk_score: float
    risk_level: str
    detected_tactics: List[str]
    explanation: str
    recommended_action: str
    next_node: str
