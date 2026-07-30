from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    project_name: str = "Sentinel AI"
    environment: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"
    secret_key: str = "default-secret-key-change-in-prod"
    
    # LLM Settings
    openai_api_key: str = ""
    llm_provider: str = "openai"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
