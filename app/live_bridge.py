import asyncio
import json
import websockets
import app.asr.decoder as decoder_module
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Inspect class/function from app.asr.decoder dynamically
DecoderClass = getattr(
    decoder_module,
    'StreamingASRDecoder',
    getattr(decoder_module, 'AudioDecoder', None)
)

async def run_live_bridge(session_id: str):
    uri = f"ws://localhost:8000/ws/live/{session_id}"
    logger.info(f"Connecting to WebSocket: {uri}")

    async with websockets.connect(uri) as websocket:
        logger.info("Connected to WebSocket backend successfully.")

        async def send_transcript(text: str):
            if text and text.strip():
                payload = {"transcript": text.strip()}
                await websocket.send(json.dumps(payload))
                logger.info(f"[Bridge -> WS] Sent: '{text.strip()}'")

        # If decoder supports callback setup
        if DecoderClass:
            loop = asyncio.get_running_loop()

            def on_text_callback(text: str):
                asyncio.run_coroutine_threadsafe(send_transcript(text), loop)

            try:
                decoder_instance = DecoderClass(on_transcript=on_text_callback)
            except TypeError:
                decoder_instance = DecoderClass()

            if hasattr(decoder_instance, 'start_listening'):
                await decoder_instance.start_listening()
            elif hasattr(decoder_instance, 'start'):
                await decoder_instance.start()
            else:
                logger.error("Decoder class found, but missing start method.")
        else:
            logger.error("No valid decoder class found in app.asr.decoder.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m app.live_bridge <session_id>")
        sys.exit(1)

    session_id = sys.argv[1]
    asyncio.run(run_live_bridge(session_id))