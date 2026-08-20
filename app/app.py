import uuid
import json
import base64
import asyncio
from typing import Optional, Dict, Any, List
import numpy as np
from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.config import settings
from app.conversation.state_machine import sentinel_app
from app.risk.rule_engine import OTPDetectionAgent
from app.asr.elevenlabs import ElevenLabsScribeClient
from app.speakers.diarization import SpeakerDiarizer

FAST_PATH_HIGH_RISK = [
    "verification code", "one-time password", "otp", "6-digit code", 
    "pin number", "read me the code", "security code", "passcode"
]

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
diarizer = SpeakerDiarizer()

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
    
    # State tracking across the live conversation session
    session_cumulative_risk: float = 0.0
    session_transcripts: List[Dict[str, Any]] = []
    
    async def process_transcript(transcript: str, speaker: Optional[str] = None, similarity_pct: int = 0):
        nonlocal session_cumulative_risk, session_transcripts
        if not transcript or not transcript.strip():
            return
        try:
            # FAST PATH: Check high risk phrases
            fast_path_alert = any(phrase in transcript.lower() for phrase in FAST_PATH_HIGH_RISK)
            
            # Determine speaker role (Owner / Victim vs Caller)
            resolved_speaker = speaker if speaker else "CALLER"
            if resolved_speaker in ("VICTIM", "USER"):
                resolved_speaker = "OWNER"

            initial_state = {
                "session_id": session_id,
                "latest_transcript": transcript,
                "speaker": resolved_speaker,
                "transcripts": list(session_transcripts),
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
            turn_risk = float(final_state.get("overall_risk_score", 0.0))
            
            # Dynamic Total Threat Score Tracking (Turns UP on threats, Turns DOWN on neutral/safe turns)
            text_lower = transcript.lower()
            if resolved_speaker == "OWNER":
                # Check for active resistance / refusal from owner (e.g. "no", "hanging up", "will call my bank")
                is_resisting = any(w in text_lower for w in ["never share", "hang up", "hanging up", "who is your supervisor", "calling my bank", "not giving", "refuse", "fake", "scam", "report you", "calling police"])
                if is_resisting:
                    session_cumulative_risk = max(0.0, session_cumulative_risk * 0.65)
                else:
                    # Natural cool-down on regular owner responses
                    session_cumulative_risk = max(0.0, session_cumulative_risk * 0.85)
            else:
                # CALLER speaking
                if turn_risk >= 0.40 or fast_path_alert:
                    # Escalating threat: ramp up rapidly
                    session_cumulative_risk = max(session_cumulative_risk * 0.60 + turn_risk * 0.60, turn_risk)
                    session_cumulative_risk = min(1.0, session_cumulative_risk)
                else:
                    # Caller says harmless/neutral phrase: decay threat score smoothly
                    session_cumulative_risk = max(0.0, session_cumulative_risk * 0.80)
            
            # Resolve dynamic session risk level
            total_risk = round(session_cumulative_risk, 2)
            if total_risk >= 0.85:
                session_level = "CRITICAL"
            elif total_risk >= 0.70:
                session_level = "HIGH"
            elif total_risk >= 0.45:
                session_level = "MEDIUM"
            else:
                session_level = "LOW"
                
            # Append turn to session memory
            session_transcripts.append({
                "speaker": resolved_speaker,
                "text": transcript,
                "risk": turn_risk,
                "cumulative_risk": total_risk
            })
            
            # Send real-time response payload back to client React/Electron app
            response = {
                "type": "threat_update",
                "session_id": session_id,
                "speaker": resolved_speaker,
                "voice_match_score": similarity_pct,
                "risk_score": total_risk,
                "turn_risk_score": turn_risk,
                "risk_level": session_level,
                "fast_path_alert": fast_path_alert,
                "latest_transcript": final_state.get("latest_transcript"),
                "detected_tactics": final_state.get("detected_tactics", []),
                "explanation": final_state.get("explanation"),
                "recommended_action": final_state.get("recommended_action")
            }
            
            await manager.send_json(session_id, response)
        except Exception as e:
            print(f"Error in process_transcript: {e}")

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
                # Path 1: Client sends text (and optional audio chunk for biometric verification)
                speaker_tag = payload.get("speaker") or payload.get("role")
                similarity_pct = 0
                
                if "audio_b64" in payload and payload["audio_b64"]:
                    try:
                        raw_pcm = base64.b64decode(payload["audio_b64"])
                        pcm_samples = np.frombuffer(raw_pcm, dtype=np.int16)
                        if len(pcm_samples) >= 512 and diarizer.enrolled_voiceprint is not None:
                            detected_role = diarizer.identify_audio_speaker(pcm_samples)
                            similarity_pct = int(diarizer.get_similarity_score(pcm_samples) * 100)
                            speaker_tag = "OWNER" if detected_role == "VICTIM" else "CALLER"
                    except Exception as e:
                        print(f"Error evaluating voiceprint: {e}")
                        
                await process_transcript(payload["transcript"], speaker=speaker_tag, similarity_pct=similarity_pct)
                
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


from fastapi import UploadFile, File, Form
import base64
import numpy as np
import io
import wave
from app.speakers.diarization import SpeakerDiarizer

# Shared Speaker Diarizer for voiceprint enrollment
diarizer = SpeakerDiarizer()

# Lazy loaded ASR Service
_asr_service = None

def get_asr_service():
    global _asr_service
    if _asr_service is None:
        try:
            from app.asr.sherpa import ASRService
            _asr_service = ASRService()
        except Exception as e:
            print(f"Warning: ASRService could not be initialized: {e}")
            _asr_service = None
    return _asr_service

class EnrollVoiceRequest(BaseModel):
    audio_base64: str = ""
    user_name: str = "Owner"

class EnrollVoiceResponse(BaseModel):
    status: str
    message: str
    is_enrolled: bool

api_router = APIRouter(prefix="/api/v1")

@api_router.post("/voice/enroll", response_model=EnrollVoiceResponse, tags=["Voice Enrollment"])
async def enroll_voice(req: EnrollVoiceRequest):
    """Enrolls user's voiceprint from base64 PCM / audio samples."""
    try:
        raw_bytes = base64.b64decode(req.audio_base64)
        pcm_samples = np.frombuffer(raw_bytes, dtype=np.int16)
        if len(pcm_samples) < 1600:
            return EnrollVoiceResponse(
                status="error",
                message="Audio sample too short. Please speak for at least 1-2 seconds.",
                is_enrolled=diarizer.enrolled_voiceprint is not None
            )
        diarizer.enroll_voiceprint(pcm_samples)
        return EnrollVoiceResponse(
            status="success",
            message=f"Voiceprint for {req.user_name} successfully enrolled!",
            is_enrolled=True
        )
    except Exception as e:
        return EnrollVoiceResponse(
            status="error",
            message=f"Failed to enroll voice: {str(e)}",
            is_enrolled=diarizer.enrolled_voiceprint is not None
        )

@api_router.get("/voice/status", tags=["Voice Enrollment"])
async def voice_status():
    """Checks if a user voice profile is enrolled."""
    return {
        "is_enrolled": diarizer.enrolled_voiceprint is not None,
        "features_dim": len(diarizer.enrolled_voiceprint) if diarizer.enrolled_voiceprint is not None else 0
    }

class AudioAnalyzeRequest(BaseModel):
    audio_base64: str
    filename: str = "recording.wav"

@api_router.post("/audio/analyze", tags=["Audio Analysis"])
async def analyze_audio_file(req: AudioAnalyzeRequest):
    """Uploads and analyzes an audio recording (base64 WAV or PCM) directly."""
    try:
        contents = base64.b64decode(req.audio_base64)
        
        # Try decoding as WAV
        try:
            with wave.open(io.BytesIO(contents), "rb") as wf:
                framerate = wf.getframerate()
                frames = wf.readframes(wf.getnframes())
                pcm_samples = np.frombuffer(frames, dtype=np.int16)
        except Exception:
            # Fallback to raw int16 PCM
            pcm_samples = np.frombuffer(contents, dtype=np.int16)

        if len(pcm_samples) == 0:
            raise HTTPException(status_code=400, detail="Empty audio data provided")

        # 1. Identify speaker (User vs Caller)
        speaker = diarizer.identify_audio_speaker(pcm_samples)
        
        # 2. Transcribe using local Sherpa ASR
        asr = get_asr_service()
        if asr:
            float_samples = pcm_samples.astype(np.float32) / 32768.0
            transcript_text = asr.process_audio(float_samples).strip()
        else:
            transcript_text = "Audio file processed. ASR engine offline."

        if not transcript_text:
            transcript_text = "(Audio analyzed - speech detected)"

        # 3. Evaluate threat via LangGraph supervisor
        initial_state = {
            "session_id": f"upload_{uuid.uuid4().hex[:8]}",
            "latest_transcript": transcript_text,
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
        
        final_state = await sentinel_app.ainvoke(initial_state)

        return {
            "status": "success",
            "filename": req.filename,
            "speaker": speaker,
            "transcript": transcript_text,
            "risk_score": final_state.get("overall_risk_score", 0.0),
            "risk_level": final_state.get("risk_level", "LOW"),
            "fast_path_alert": final_state.get("fast_path_alert", False),
            "detected_tactics": final_state.get("detected_tactics", []),
            "explanation": final_state.get("explanation"),
            "recommended_action": final_state.get("recommended_action")
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Audio analysis failed: {str(e)}")

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