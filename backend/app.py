from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.api.routes import session_routes
from backend.api.websocket import live_stream

app = FastAPI(
    title=settings.project_name,
    version="0.1.0",
    description="Real-time Live Scam Calling Detection & Defense API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routes
app.include_router(session_routes.router, prefix="/api/v1", tags=["Session"])
app.include_router(live_stream.router, tags=["WebSocket"])

@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    return {
        "status": "online",
        "version": "0.1.0",
        "environment": settings.environment
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host=settings.api_host, port=settings.api_port, reload=True)
