from typing import List, Dict, Any, Optional, TypedDict
from pydantic import BaseModel, Field

class TranscriptSegment(BaseModel):
    id: str
    speaker: str = "CALLER"  # CALLER | RECEIVER | UNKNOWN
    text: str
    timestamp: float
    is_final: bool = True

class WorkerAnalysisResult(BaseModel):
    agent_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    score: float = Field(ge=0.0, le=1.0)
    detected_tactics: List[str] = Field(default_factory=list)
    reasoning: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SentinelState(BaseModel):
    session_id: str
    transcripts: List[TranscriptSegment] = Field(default_factory=list)
    latest_transcript: str = ""
    speaker_role: str = "CALLER"
    
    # Fast-Path Emergency Alert Flag
    fast_path_alert: bool = False
    fast_path_reason: Optional[str] = None
    
    # Worker Analysis Outputs
    worker_results: Dict[str, WorkerAnalysisResult] = Field(default_factory=dict)
    
    # RAG & Verification Context
    retrieved_patterns: List[Dict[str, Any]] = Field(default_factory=list)
    verified_organizations: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Supervisor Outputs & Final Decision
    consensus_hypothesis: str = ""
    overall_risk_score: float = 0.0
    risk_level: str = "LOW"  # LOW | MEDIUM | HIGH | CRITICAL
    detected_tactics: List[str] = Field(default_factory=list)
    explanation: str = ""
    recommended_action: str = ""
    next_node: str = "END"

class GraphState(TypedDict, total=False):
    session_id: str
    transcripts: List[Dict[str, Any]]
    latest_transcript: str
    speaker: str
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
