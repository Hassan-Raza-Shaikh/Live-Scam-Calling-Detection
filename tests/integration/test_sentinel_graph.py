import pytest
from ai.graph.sentinel_graph import sentinel_app

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
