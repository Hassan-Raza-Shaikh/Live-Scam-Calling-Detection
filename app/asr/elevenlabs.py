import json
import base64
import asyncio
import websockets
from typing import AsyncGenerator
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

class ElevenLabsScribeClient:
    """
    WebSocket client for ElevenLabs Scribe v2 Realtime STT.
    Expects 16kHz Mono PCM audio chunks.
    """
    def __init__(self, api_key: str = None):
        # Fallback to a dummy key if not provided to allow testing the pipeline
        self.api_key = api_key or getattr(settings, "elevenlabs_api_key", "dummy_key")
        
        self.ws_url = "wss://api.elevenlabs.io/v1/speech-to-text/realtime?model_id=scribe_v2_realtime&audio_format=pcm_16000"
        self.ws = None

    async def connect(self):
        logger.info(f"Connecting to ElevenLabs Scribe v2 at {self.ws_url.split('?')[0]}")
        try:
            self.ws = await websockets.connect(
                self.ws_url,
                additional_headers={"xi-api-key": self.api_key}
            )
        except Exception as e:
            logger.error(f"Failed to connect to ElevenLabs: {e}")
            self.ws = None

    async def send_audio(self, pcm_base64_chunk: str):
        """Sends a base64 encoded PCM chunk to Scribe v2"""
        if not self.ws:
            return
            
        try:
            payload = {
                "message_type": "input_audio_chunk",
                "audio_base_64": pcm_base64_chunk
            }
            await self.ws.send(json.dumps(payload))
        except Exception as e:
            logger.error(f"Error sending audio to Scribe v2: {e}")

    async def receive_transcripts(self) -> AsyncGenerator[str, None]:
        """Continuously yields transcribed text from ElevenLabs"""
        if not self.ws:
            return

        try:
            async for message in self.ws:
                data = json.loads(message)
                
                msg_type = data.get("message_type", "")
                
                # Only trigger LangGraph on final or committed transcripts to avoid rate limits / spam
                if msg_type in ("final_transcript", "committed_transcript"):
                    text = data.get("text", "").strip()
                    if text:
                        yield text
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("ElevenLabs Scribe v2 connection closed.")
        except Exception as e:
            logger.error(f"Error receiving transcript from Scribe v2: {e}")

    async def close(self):
        if self.ws:
            try:
                # Optional: Send a manual commit or flush if needed by the API before closing
                await self.ws.send(json.dumps({"message_type": "input_audio_chunk", "audio_base_64": "", "commit": True}))
                await self.ws.close()
            except:
                pass
            self.ws = None
