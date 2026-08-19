import threading
from typing import List, Dict
from app.detection.interfaces import BaseDetector

class DetectorRegistry:
    """Thread-safe registry for managing and retrieving active detectors.
    
    Detectors are sorted and returned according to their execution priority.
    """
    
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._detectors: Dict[str, BaseDetector] = {}

    def register(self, detector: BaseDetector) -> None:
        """Registers a detector. Overwrites if a detector with the same name exists.
        
        Args:
            detector: An instance of BaseDetector.
        """
        with self._lock:
            self._detectors[detector.name] = detector

    def unregister(self, name: str) -> None:
        """Removes a detector from the registry by its name.
        
        Args:
            name: The name of the detector to remove.
        """
        with self._lock:
            self._detectors.pop(name, None)

    def get_detectors(self) -> List[BaseDetector]:
        """Returns all registered detectors sorted by priority (lowest runs first).
        
        Only returns detectors where enabled is True.
        
        Returns:
            A sorted list of active BaseDetector instances.
        """
        with self._lock:
            active_detectors = [d for d in self._detectors.values() if d.enabled]
            return sorted(active_detectors, key=lambda d: d.priority)
