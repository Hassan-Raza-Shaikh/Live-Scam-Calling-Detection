import asyncio
from app.conversation.state_machine import sentinel_app

async def test():
    state = {
        "session_id": "test1",
        "latest_transcript": "please transfer money to a safe account immediately",
        "transcripts": [], "fast_path_alert": False, "worker_results": {},
        "retrieved_patterns": [], "verified_organizations": [], "consensus_hypothesis": "",
        "overall_risk_score": 0.0, "risk_level": "LOW", "detected_tactics": [],
        "explanation": "", "recommended_action": "", "next_node": ""
    }
    result = await sentinel_app.ainvoke(state)
    print("RISK LEVEL:", result["risk_level"])
    print("SCORE:", result["overall_risk_score"])
    print("TACTICS:", result["detected_tactics"])

asyncio.run(test())