from typing import List
from app.detection.interfaces import BaseDetector
from app.detection.models import Detection

class DetectionPipeline:
    """Executes a list of detectors against a transcript.
    
    Currently processes detectors sequentially, but is designed to support
    parallel/concurrent execution in the future without changing the public interface.
    """
    
    def execute(self, transcript: str, detectors: List[BaseDetector]) -> List[Detection]:
        """Runs the registered detectors on the transcript.
        
        Args:
            transcript: Input transcript text.
            detectors: List of BaseDetector objects to execute.
            
        Returns:
            A combined list of Detections from all executed detectors.
        """
        all_detections: List[Detection] = []
        
        # Sequentially iterate through detectors.
        # This can be refactored to thread pools (e.g. concurrent.futures.ThreadPoolExecutor)
        # for parallel execution later without changing this method signature or the engine interface.
        for detector in detectors:
            try:
                detections = detector.detect(transcript)
                all_detections.extend(detections)
            except Exception as e:
                # Log or handle detector-specific errors here without failing the entire pipeline
                import logging
                logging.getLogger("detection.pipeline").error(
                    f"Detector '{detector.name}' failed during execution: {str(e)}", 
                    exc_info=True
                )
                
        return all_detections
