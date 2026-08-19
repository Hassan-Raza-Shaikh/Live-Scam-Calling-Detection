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
        
        self.ws_url = "wss://api.elevenlabs.io/v1/speech-to-text/realtime"
        self.ws = None

    async def connect(self):
        logger.info(f"Connecting to ElevenLabs Scribe v2 at {self.ws_url}")
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
                "audio": pcm_base64_chunk
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
                
                # Check for transcript text in the Scribe v2 payload
                if "text" in data and data["text"]:
                    yield data["text"]
                elif "transcript" in data and data["transcript"]:
                    yield data["transcript"]
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("ElevenLabs Scribe v2 connection closed.")
        except Exception as e:
            logger.error(f"Error receiving transcript from Scribe v2: {e}")

    async def close(self):
        if self.ws:
            # Send EOS (End of Stream) if the API requires it
            try:
                await self.ws.send(json.dumps({"audio": ""})) 
                await self.ws.close()
            except:
                pass
            self.ws = None
