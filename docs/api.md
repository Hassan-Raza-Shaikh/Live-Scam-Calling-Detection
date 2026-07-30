# Sentinel AI API & WebSocket Specifications

## 1. REST Endpoints

### `GET /api/v1/health`
Health check endpoint returning system status and model readiness.

### `POST /api/v1/session/start`
Starts a new live scam detection session.
- **Request**: `{ "user_id": "usr_123", "device_type": "desktop" }`
- **Response**: `{ "session_id": "sess_987", "status": "active", "created_at": "2026-07-30T11:00:00Z" }`

### `POST /api/v1/session/end`
Ends an active session and returns the session transcript summary.

### `POST /api/v1/analyze/transcript`
Direct text analysis endpoint for off-line transcript evaluation.

---

## 2. Real-Time WebSocket Protocol

### Connection: `ws://localhost:8000/ws/live/{session_id}`

#### Client $\rightarrow$ Server: Audio Chunk Payload
```json
{
  "type": "audio_chunk",
  "timestamp": 1785324000,
  "data": "base64_encoded_pcm_audio_data",
  "sample_rate": 16000
}
```

#### Server $\rightarrow$ Client: Real-Time Threat Update
```json
{
  "type": "threat_update",
  "session_id": "sess_987",
  "risk_score": 0.88,
  "risk_level": "HIGH",
  "fast_path_alert": true,
  "latest_transcript": "We are calling from your bank. Provide the 6-digit code sent to your phone immediately.",
  "speaker": "CALLER",
  "detected_tactics": ["OTP_DEMAND", "AUTHORITY_IMPERSONATION", "URGENCY"],
  "explanation": "Caller is demanding a 6-digit OTP claiming to be your bank.",
  "recommended_action": "HANG UP IMMEDIATELY. NEVER SHARE OTP CODES."
}
```
