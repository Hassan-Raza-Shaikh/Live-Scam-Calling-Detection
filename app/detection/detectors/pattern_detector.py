import os
from pathlib import Path
from typing import List, Optional, Union
from app.detection.detectors.base import BaseDetectorImpl
from app.detection.models import Detection, PatternDatabase
from app.detection.normalizer import Normalizer
from app.detection.patterns.loader import PatternLoader
from app.detection.patterns.matcher import PatternMatcher

class PatternDetector(BaseDetectorImpl):
    """Specific detector implementation that performs pattern matching against loaded rules.
    
    This is the only functional detector out of the box. It loads the YAML pattern database,
    normalizes the incoming transcript, and uses PatternMatcher to find exact phrases,
    wildcards, and regex rules.
    
    Purpose: Low-latency signature-based scam detection.
    Input: Normalized or raw transcript string.
    Output: List of Detection objects.
    Future extension points:
        - Add multi-language pattern file loading.
        - Add priority-based pattern short-circuiting.
    """
    
    def __init__(
        self,
        database_dir: Optional[Union[str, Path]] = None,
        loader: Optional[PatternLoader] = None,
        matcher: Optional[PatternMatcher] = None,
        normalizer: Optional[Normalizer] = None,
        priority: int = 10,
        enabled: bool = True
    ):
        super().__init__(name="PatternDetector", priority=priority, enabled=enabled)
        
        # Determine database directory path
        if database_dir is None:
            self._database_dir = Path(__file__).parent.parent / "patterns" / "database"
        else:
            self._database_dir = Path(database_dir)
            
        # Setup helpers (supporting dependency injection)
        self._loader = loader or PatternLoader(self._database_dir)
        self._matcher = matcher or PatternMatcher()
        self._normalizer = normalizer or Normalizer()
        
        self._database: Optional[PatternDatabase] = None

    def initialize(self) -> None:
        """Loads and compiles pattern database rules during startup."""
        self._database = self._loader.load(force_reload=True)

    def detect(self, transcript: str) -> List[Detection]:
        """Runs exact phrase, wildcard, and regex matching on normalized transcript text.
        
        Args:
            transcript: Raw transcript text input.
            
        Returns:
            A list of Detection dataclasses representing matched evidence.
        """
        if not self.enabled:
            return []
            
        if self._database is None:
            # Lazy initialize if initialize was not called explicitly
            self.initialize()
            
        # Normalize incoming transcript
        normalized_transcript = self._normalizer.normalize(transcript)
        if not normalized_transcript:
            return []
            
        # Execute matching
        return self._matcher.match(
            normalized_text=normalized_transcript,
            database=self._database,
            source_files=self._database.source_files,
            detector_name=self.name
        )

    def shutdown(self) -> None:
        """Cleans up internal references."""
        self._database = None
