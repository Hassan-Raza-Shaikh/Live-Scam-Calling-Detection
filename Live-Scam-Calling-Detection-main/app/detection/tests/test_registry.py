import threading
from app.detection.registry import DetectorRegistry
from app.detection.detectors.regex_detector import RegexDetector
from app.detection.detectors.fuzzy_detector import FuzzyDetector

def test_registry_registration_and_priority():
    registry = DetectorRegistry()
    
    detector_high = RegexDetector(priority=10)
    detector_low = FuzzyDetector(priority=50)
    
    registry.register(detector_low)
    registry.register(detector_high)
    
    detectors = registry.get_detectors()
    assert len(detectors) == 2
    # Verify priority sorting (lowest priority number runs first)
    assert detectors[0].priority == 10
    assert detectors[1].priority == 50

def test_registry_unregister():
    registry = DetectorRegistry()
    detector = RegexDetector(priority=10)
    
    registry.register(detector)
    assert len(registry.get_detectors()) == 1
    
    registry.unregister(detector.name)
    assert len(registry.get_detectors()) == 0

def test_registry_thread_safety():
    registry = DetectorRegistry()
    
    def register_worker(i: int):
        detector = RegexDetector(priority=i)
        # Force a unique name to register multiple
        detector._name = f"RegexDetector_{i}"
        registry.register(detector)
        
    threads = []
    for i in range(100):
        t = threading.Thread(target=register_worker, args=(i,))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    assert len(registry.get_detectors()) == 100
