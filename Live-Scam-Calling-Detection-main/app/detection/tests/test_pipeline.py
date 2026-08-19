from app.detection.pipeline import DetectionPipeline
from app.detection.detectors.regex_detector import RegexDetector
from app.detection.detectors.fuzzy_detector import FuzzyDetector
from app.detection.models import Detection
from app.detection.utils import get_current_timestamp

class MockDetector(RegexDetector):
    def __init__(self, name: str, detections: list):
        super().__init__(priority=1)
        self._name = name
        self.detections = detections
        
    def detect(self, transcript: str):
        return self.detections

def test_pipeline_execution():
    pipeline = DetectionPipeline()
    
    det1 = Detection(
        intent="TEST1",
        matched_text="match1",
        matched_rule="rule1",
        confidence=1.0,
        weight=10,
        detector_name="Mock1",
        matching_strategy="phrase",
        start_index=0,
        end_index=6,
        source_file="mock.yaml",
        timestamp=get_current_timestamp()
    )
    
    det2 = Detection(
        intent="TEST2",
        matched_text="match2",
        matched_rule="rule2",
        confidence=1.0,
        weight=20,
        detector_name="Mock2",
        matching_strategy="regex",
        start_index=8,
        end_index=14,
        source_file="mock.yaml",
        timestamp=get_current_timestamp()
    )
    
    mock1 = MockDetector("Mock1", [det1])
    mock2 = MockDetector("Mock2", [det2])
    
    results = pipeline.execute("dummy transcript", [mock1, mock2])
    
    assert len(results) == 2
    assert results[0] == det1
    assert results[1] == det2
