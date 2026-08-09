from typing import List
from app.detection.interfaces import BaseDetector
from app.detection.models import Detection

class BaseDetectorImpl(BaseDetector):
    """Common implementation of the BaseDetector interface.
    
    Provides standard attributes and default empty lifecycle hooks.
    """
    
    def __init__(self, name: str, priority: int, enabled: bool = True):
        self._name = name
        self._priority = priority
        self._enabled = enabled

    def initialize(self) -> None:
        """Placeholder for initialization logic."""
        pass

    def shutdown(self) -> None:
        """Placeholder for shutdown cleanup logic."""
        pass

    @property
    def name(self) -> str:
        return self._name

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def enabled(self) -> bool:
        return self._enabled
