import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class StartSessionRequest(BaseModel):
    user_id: str = "default_user"
    device_type: str = "desktop"

class StartSessionResponse(BaseModel):
    session_id: str
    status: str
    ws_endpoint: str

@router.post("/session/start", response_model=StartSessionResponse)
async def start_session(req: StartSessionRequest):
    session_id = f"sess_{uuid.uuid4().hex[:10]}"
    return StartSessionResponse(
        session_id=session_id,
        status="active",
        ws_endpoint=f"/ws/live/{session_id}"
    )

@router.post("/session/{session_id}/end")
async def end_session(session_id: str):
    return {"session_id": session_id, "status": "ended"}
