from typing import Optional, List, Dict
from app.detection.models import DetectionReport
from app.conversation.events import ConversationEvent
from app.conversation.state import ConversationState
from app.conversation.models import ConversationSnapshot, TimelineEntry, IntentStats
from app.conversation.interfaces import IMemoryManager, IStatisticsCalculator, IPhaseDetector
from app.conversation.memory import SlidingEventMemory
from app.conversation.statistics import StatisticsCalculator
from app.conversation.phases import HeuristicPhaseDetector
from app.conversation.snapshot import build_snapshot
from app.conversation.timeline import ConversationTimeline
from app.conversation.utils import get_current_timestamp

class ConversationManager:
    """Manages the lifecycle, state updates, memory, and analytics of a conversation.
    
    Coordinates the sliding memory window, stats updates, and phase evaluations.
    """
    
    def __init__(
        self,
        state: Optional[ConversationState] = None,
        memory: Optional[IMemoryManager] = None,
        statistics_calculator: Optional[IStatisticsCalculator] = None,
        phase_detector: Optional[IPhaseDetector] = None
    ) -> None:
        """Initializes the manager.
        
        Args:
            state: Pre-existing ConversationState or None (creates a new state).
            memory: Custom IMemoryManager implementation.
            statistics_calculator: Custom statistics calculator.
            phase_detector: Custom conversation phase detector.
        """
        self._state = state or ConversationState()
        self._memory = memory or SlidingEventMemory()
        self._statistics_calculator = statistics_calculator or StatisticsCalculator()
        self._phase_detector = phase_detector or HeuristicPhaseDetector()
        
        # We can construct the timeline from state.timeline if any entries exist
        self._timeline = ConversationTimeline()
        for entry in self._state.timeline:
            self._timeline.add_entry(entry.relative_time_seconds, entry.intent)

    @property
    def state(self) -> ConversationState:
        """Returns the internal mutable state. Kept for engine coordination."""
        return self._state

    def update(self, report: DetectionReport) -> ConversationSnapshot:
        """Processes a new DetectionReport, updates internal state, and returns a snapshot.
        
        Args:
            report: The DetectionReport containing raw text and parsed detections.
            
        Returns:
            An immutable ConversationSnapshot.
        """
        # Determine the update timestamp
        update_time = report.timestamp if report.timestamp > 0 else get_current_timestamp()
        
        # If it's the first update, initialize start_time to this update_time
        if self._state.transcript_count == 0:
            self._state.start_time = update_time

        # 1. Update general conversation state counters
        self._state.transcript_count += 1
        self._state.last_update_time = update_time
        self._state.elapsed_time = max(0.0, update_time - self._state.start_time)
        
        # 2. Insert new detections as ConversationEvents
        new_intents_seen: List[str] = []
        if report.detections:
            for detection in report.detections:
                event_time = detection.timestamp if detection.timestamp > 0 else update_time
                event = ConversationEvent(
                    timestamp=event_time,
                    intent=detection.intent,
                    confidence=detection.confidence,
                    weight=detection.weight,
                    matched_text=detection.matched_text,
                    detector_name=detection.detector_name,
                    matching_strategy=detection.matching_strategy,
                    source_file=detection.source_file,
                    transcript=report.original_transcript
                )
                
                # Add to memory (this automatically triggers capacity/age expiration)
                self._memory.insert(event)
                
                # Update detection count
                self._state.detection_count += 1
                
                # Update timeline
                relative_sec = max(0.0, event_time - self._state.start_time)
                self._timeline.add_entry(relative_sec, detection.intent)
                
                new_intents_seen.append(detection.intent)

        # 3. Trigger memory expiration based on current time (even if no detections occurred)
        self._memory.expire_old_events(update_time)
        
        # 4. Recalculate statistics on active events
        active_events = self._memory.get_events()
        
        stats = self._statistics_calculator.calculate(
            events=active_events,
            start_time=self._state.start_time,
            current_time=update_time
        )
        
        intent_summary = self._statistics_calculator.calculate_intent_summary(
            events=active_events,
            current_time=update_time
        )
        
        # 5. Sync computed statistics to state
        self._state.stats = stats
        self._state.dominant_intent = stats.dominant_intent
        self._state.average_confidence = stats.average_confidence
        self._state.highest_confidence = stats.highest_confidence
        
        if new_intents_seen:
            self._state.latest_intent = new_intents_seen[-1]
            
        # Update state intent counts from active summary
        self._state.intent_counts = {
            intent: summary.count for intent, summary in intent_summary.items()
        }
        
        # Update timeline reference in state
        self._state.timeline = self._timeline.get_entries()
        
        # Update recent events list in state (keep last 10)
        self._state.recent_events = self._memory.get_recent_events(limit=10)
        
        # 6. Evaluate phase transitions
        self._state.phase = self._phase_detector.detect_phase(
            current_phase=self._state.phase,
            events=active_events,
            intent_stats=intent_summary
        )
        
        # 7. Construct and return the immutable snapshot
        return build_snapshot(self._state, intent_summary)
