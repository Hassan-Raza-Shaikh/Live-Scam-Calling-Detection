import time
from typing import Optional, Dict, Any
from app.detection.models import DetectionReport
from app.detection.normalizer import Normalizer
from app.detection.registry import DetectorRegistry
from app.detection.pipeline import DetectionPipeline
from app.detection.detectors.pattern_detector import PatternDetector
from app.detection.detectors.regex_detector import RegexDetector
from app.detection.detectors.fuzzy_detector import FuzzyDetector
from app.detection.detectors.embedding_detector import EmbeddingDetector
from app.detection.detectors.llm_detector import LLMDetector
from app.detection.utils import get_current_timestamp

class DetectionEngine:
    """The primary public entry point for the Detection Framework.
    
    Coordinates text normalization, detector execution via the pipeline,
    and returns a structured DetectionReport containing all matched evidence.
    """
    
    def __init__(
        self,
        registry: Optional[DetectorRegistry] = None,
        pipeline: Optional[DetectionPipeline] = None,
        normalizer: Optional[Normalizer] = None,
        auto_initialize: bool = True
    ):
        """Initializes the engine, setting up detectors, normalizer, and registry.
        
        Args:
            registry: Optional custom DetectorRegistry. If None, a standard registry
                      with all default detectors registered is created.
            pipeline: Optional custom DetectionPipeline.
            normalizer: Optional custom Normalizer.
            auto_initialize: If True, calls initialize() on all registered detectors.
        """
        self._registry = registry or DetectorRegistry()
        self._pipeline = pipeline or DetectionPipeline()
        self._normalizer = normalizer or Normalizer()
        
        # Register default detectors if custom registry not provided
        if registry is None:
            self._register_default_detectors()
            
        if auto_initialize:
            self.initialize()

    def _register_default_detectors(self) -> None:
        """Instantiates and registers the default set of detectors."""
        self._registry.register(PatternDetector(priority=10))
        self._registry.register(RegexDetector(priority=20))
        self._registry.register(FuzzyDetector(priority=30))
        self._registry.register(EmbeddingDetector(priority=40))
        self._registry.register(LLMDetector(priority=50))

    def initialize(self) -> None:
        """Initializes all registered and enabled detectors."""
        for detector in self._registry.get_detectors():
            detector.initialize()

    def shutdown(self) -> None:
        """Shuts down all registered and enabled detectors to free up resources."""
        for detector in self._registry.get_detectors():
            detector.shutdown()

    def detect(self, transcript: str) -> DetectionReport:
        """Runs the detection pipeline on the input transcript text.
        
        Args:
            transcript: Raw transcript string.
            
        Returns:
            A structured DetectionReport dataclass.
        """
        start_time = time.perf_counter()
        request_timestamp = get_current_timestamp()
        
        # 1. Normalize the transcript for engine-level tracking
        normalized = self._normalizer.normalize(transcript)
        
        # 2. Gather active detectors from registry
        detectors = self._registry.get_detectors()
        
        # 3. Execute matching via the pipeline
        detections = self._pipeline.execute(normalized, detectors)
        
        # Calculate execution time in milliseconds
        end_time = time.perf_counter()
        processing_time_ms = (end_time - start_time) * 1000.0
        
        # Build detector versions dict (placeholder versions for now)
        detector_versions = {detector.name: "1.0.0" for detector in detectors}
        
        return DetectionReport(
            original_transcript=transcript,
            normalized_transcript=normalized,
            detections=detections,
            processing_time_ms=processing_time_ms,
            detector_versions=detector_versions,
            timestamp=request_timestamp,
            metadata={}
        )
