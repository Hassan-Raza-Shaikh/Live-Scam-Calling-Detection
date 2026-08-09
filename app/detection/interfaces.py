from abc import ABC, abstractmethod
from typing import List
from app.detection.models import Detection

class BaseDetector(ABC):
    """Abstract base class representing a single scam detector module.
    
    All specific detectors (Pattern, Regex, Fuzzy, Embeddings, LLM) must inherit
    from this class and implement its interface.
    """
    
    @abstractmethod
    def initialize(self) -> None:
        """Runs initialization tasks (e.g. loading configuration, compiling patterns)."""
        pass

    @abstractmethod
    def detect(self, transcript: str) -> List[Detection]:
        """Runs detection logic on the provided transcript.
        
        Args:
            transcript: The input (normalized or raw) transcript text.
            
        Returns:
            A list of Detection dataclass objects containing matched rules, locations, etc.
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Cleanup detector resources (e.g. database connections, file handles)."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the detector (used in logs and reports)."""
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        """Execution priority of the detector. Lower priority runs first."""
        pass

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """True if the detector is enabled and should participate in the pipeline."""
        pass
