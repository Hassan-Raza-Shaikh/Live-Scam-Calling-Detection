import pydantic_settings

class GraphConfig(pydantic_settings.BaseSettings):
    max_worker_concurrency: int = 5
    fast_path_threshold: float = 0.85
    risk_high_threshold: float = 0.75
    risk_medium_threshold: float = 0.45

graph_config = GraphConfig()
