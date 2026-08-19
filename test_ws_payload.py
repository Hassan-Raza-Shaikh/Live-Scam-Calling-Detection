import asyncio
import websockets
import json

async def test():
    async with websockets.connect("ws://127.0.0.1:8000/ws/live/sess_test") as ws:
        print("Connected!")
        payload = json.dumps({"audio_b64": "A" * 11000})
        await ws.send(payload)
        print("Sent payload!")
        try:
            response = await asyncio.wait_for(ws.recv(), timeout=2.0)
            print("Received:", response)
        except asyncio.TimeoutError:
            print("Timeout waiting for response (expected if no text is transcribed)")
        except websockets.exceptions.ConnectionClosed as e:
            print(f"Connection closed by server! {e.code} {e.reason}")

asyncio.run(test())
