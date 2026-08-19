from typing import List
from app.detection.detectors.base import BaseDetectorImpl
from app.detection.models import Detection

class EmbeddingDetector(BaseDetectorImpl):
    """Placeholder implementation of a Sentence Embedding / Semantic Similarity Detector.
    
    Purpose:
        Perform semantic matching of transcript segments against scam intents
        using pre-calculated high-dimensional embeddings (e.g. via ONNX models).
        
    Input:
        Normalized or raw transcript text string.
        
    Output:
        List of Detection objects.
        
    Future extension points:
        - Integrate ONNX Runtime with a lightweight local sentence transformer (e.g. MiniLM).
        - Cache sentence vector computations to keep latency under 10ms.
        - Run cosine similarity lookups against target scam vector representations.
    """
    
    def __init__(self, priority: int = 40, enabled: bool = True):
        super().__init__(name="EmbeddingDetector", priority=priority, enabled=enabled)

    def detect(self, transcript: str) -> List[Detection]:
        """Runs embedding similarity detection (currently a placeholder returning empty results)."""
        return []
