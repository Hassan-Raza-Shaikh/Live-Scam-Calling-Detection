import uuid
import json
import asyncio
from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.config import settings
from app.conversation.state_machine import sentinel_app
from app.risk.rule_engine import OTPDetectionAgent
from app.asr.elevenlabs import ElevenLabsScribeClient

app = FastAPI(
    title=settings.project_name,
    version="0.1.0",
    description="Real-time Live Scam Calling Detection & Defense API (Reorganized)"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OTP Agent for fast-path check
otp_agent = OTPDetectionAgent()

class ConnectionManager:
    """
    Holds a LIST of connections per session_id.
    This lets live_bridge.py and the React browser tab both join the same session.
    """
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(session_id, []).append(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket):
        conns = self.active_connections.get(session_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if session_id in self.active_connections and not self.active_connections[session_id]:
            del self.active_connections[session_id]

    async def send_json(self, session_id: str, message: dict):
        for ws in list(self.active_connections.get(session_id, [])):
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                pass

manager = ConnectionManager()

@app.websocket("/ws/live/{session_id}")
async def websocket_live_stream(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)
    elevenlabs_client = None
    
    async def process_transcript(transcript_text: str):
        if not transcript_text:
            return
            
        print(f"🎙️ [WebSocket Ingest] sess={session_id} transcript='{transcript_text}'")
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

    async def listen_to_elevenlabs(client: ElevenLabsScribeClient):
        async for text in client.receive_transcripts():
            await process_transcript(text)
            
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                continue
            
            if "transcript" in payload:
                # Path 1: Client sends text directly (Web Speech API)
                await process_transcript(payload["transcript"])
                
            elif "audio_b64" in payload:
                # Path 2: Client sends audio for Scribe v2
                if elevenlabs_client is None:
                    elevenlabs_client = ElevenLabsScribeClient()
                    await elevenlabs_client.connect()
                    if elevenlabs_client.ws:
                        asyncio.create_task(listen_to_elevenlabs(elevenlabs_client))
                
                await elevenlabs_client.send_audio(payload["audio_b64"])
                
    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)
        if elevenlabs_client:
            await elevenlabs_client.close()
    except Exception as e:
        import traceback
        traceback.print_exc()
        manager.disconnect(session_id, websocket)
        if elevenlabs_client:
            await elevenlabs_client.close()

# Pydantic Schemas for Session Routes
class StartSessionRequest(BaseModel):
    user_id: str = "default_user"
    device_type: str = "desktop"

class StartSessionResponse(BaseModel):
    session_id: str
    status: str
    ws_endpoint: str


api_router = APIRouter(prefix="/api/v1")

@api_router.post("/session/start", response_model=StartSessionResponse, tags=["Session"])
async def start_session(req: StartSessionRequest):
    session_id = f"sess_{uuid.uuid4().hex[:10]}"
    return StartSessionResponse(
        session_id=session_id,
        status="active",
        ws_endpoint=f"/ws/live/{session_id}"
    )

@api_router.post("/session/{session_id}/end", tags=["Session"])
async def end_session(session_id: str):
    return {"session_id": session_id, "status": "ended"}

@api_router.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "online",
        "version": "0.1.0",
        "environment": settings.environment
    }


app.include_router(api_router)