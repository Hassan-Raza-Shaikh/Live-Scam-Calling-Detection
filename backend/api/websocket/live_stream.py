import json
import base64
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ai.graph.sentinel_graph import sentinel_app
from ai.agents.workers.otp_detection_agent import OTPDetectionAgent

router = APIRouter()
otp_agent = OTPDetectionAgent()

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_json(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_text(json.dumps(message))

manager = ConnectionManager()

@router.websocket("/ws/live/{session_id}")
async def websocket_live_stream(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            transcript_text = payload.get("transcript", "")
            
            # Fast-path check
            fast_path_result = otp_agent.analyze(transcript_text)
            fast_path_alert = fast_path_result.score >= 0.85
            
            # Run LangGraph deep supervisor analysis
            initial_state = {
                "session_id": session_id,
                "latest_transcript": transcript_text,
                "transcripts": [],
                "fast_path_alert": fast_path_alert,
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
            
            # Send real-time response payload back to client React/Electron app
            response = {
                "type": "threat_update",
                "session_id": session_id,
                "risk_score": final_state.get("overall_risk_score", 0.0),
                "risk_level": final_state.get("risk_level", "LOW"),
                "fast_path_alert": fast_path_alert,
                "latest_transcript": final_state.get("latest_transcript"),
                "detected_tactics": final_state.get("detected_tactics", []),
                "explanation": final_state.get("explanation"),
                "recommended_action": final_state.get("recommended_action")
            }
            
            await manager.send_json(session_id, response)
            
    except WebSocketDisconnect:
        manager.disconnect(session_id)
