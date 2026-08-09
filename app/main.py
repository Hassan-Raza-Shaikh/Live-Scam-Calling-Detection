import uvicorn
from app.config import settings

def main():
    uvicorn.run(
        "app.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development"
    )

if __name__ == "__main__":
    main()
