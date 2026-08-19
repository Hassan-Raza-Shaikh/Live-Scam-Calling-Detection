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
    elevenlabs_api_key: str = ""
    llm_provider: str = "openai"
    
    # ASR Settings
    asr_encoder_path: str = "models/sherpa/encoder-epoch-99-avg-1-chunk-16-left-128.onnx"
    asr_decoder_path: str = "models/sherpa/decoder-epoch-99-avg-1-chunk-16-left-128.onnx"
    asr_joiner_path: str = "models/sherpa/joiner-epoch-99-avg-1-chunk-16-left-128.onnx"
    asr_tokens_path: str = "models/sherpa/tokens.txt"
    asr_num_threads: int = 2
    asr_sample_rate: int = 16000
    asr_feature_dim: int = 80
    asr_decoding_method: str = "greedy_search"
    asr_enable_endpoint: bool = True
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
