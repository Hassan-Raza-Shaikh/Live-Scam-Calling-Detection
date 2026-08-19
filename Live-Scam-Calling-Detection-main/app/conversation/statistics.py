from typing import List, Dict
from collections import Counter
from app.conversation.interfaces import IStatisticsCalculator
from app.conversation.events import ConversationEvent
from app.conversation.models import ConversationStats, IntentStats

class StatisticsCalculator(IStatisticsCalculator):
    """Calculates real-time aggregations and per-intent metrics for a conversation.
    
    Provides highly efficient statistics extraction on top of the active rolling event window.
    """
    
    def calculate(
        self, 
        events: List[ConversationEvent], 
        start_time: float, 
        current_time: float
    ) -> ConversationStats:
        """Calculates global session-level metrics.
        
        Args:
            events: List of non-expired ConversationEvents.
            start_time: Call start epoch timestamp.
            current_time: Current epoch timestamp.
            
        Returns:
            A ConversationStats dataclass instance.
        """
        duration = max(0.0, current_time - start_time)
        total = len(events)
        
        if not events:
            return ConversationStats(
                total_detections=0,
                unique_intents=0,
                dominant_intent="NONE",
                detection_frequency=0.0,
                average_confidence=0.0,
                highest_confidence=0.0,
                conversation_duration=duration,
                time_since_last_detection=0.0,
                detection_rate_per_minute=0.0
            )
            
        # Group and count intents
        intent_counts = Counter(e.intent for e in events)
        unique_intents = len(intent_counts)
        
        # Resolve dominant intent (highest frequency, tie-break by most recent detection)
        def dominant_key(intent: str) -> tuple:
            count = intent_counts[intent]
            latest_t = max(e.timestamp for e in events if e.intent == intent)
            return (count, latest_t)
            
        dominant_intent = max(intent_counts.keys(), key=dominant_key)
        
        # Calculate confidences
        confidences = [e.confidence for e in events]
        avg_conf = sum(confidences) / len(confidences)
        max_conf = max(confidences)
        
        # Calculate rates
        det_freq = total / duration if duration > 0.0 else 0.0
        det_rate_min = det_freq * 60.0
        
        # Time since last detection
        latest_event_time = max(e.timestamp for e in events)
        time_since_last = max(0.0, current_time - latest_event_time)
        
        return ConversationStats(
            total_detections=total,
            unique_intents=unique_intents,
            dominant_intent=dominant_intent,
            detection_frequency=det_freq,
            average_confidence=avg_conf,
            highest_confidence=max_conf,
            conversation_duration=duration,
            time_since_last_detection=time_since_last,
            detection_rate_per_minute=det_rate_min
        )

    def calculate_intent_summary(
        self, 
        events: List[ConversationEvent], 
        current_time: float
    ) -> Dict[str, IntentStats]:
        """Aggregates metrics for each unique scam intent present in the window.
        
        Args:
            events: List of non-expired ConversationEvents.
            current_time: Current epoch timestamp.
            
        Returns:
            A dictionary mapping intent strings to IntentStats dataclass instances.
        """
        summary: Dict[str, IntentStats] = {}
        if not events:
            return summary
            
        # Group events by intent
        by_intent: Dict[str, List[ConversationEvent]] = {}
        for e in events:
            by_intent.setdefault(e.intent, []).append(e)
            
        for intent, intent_events in by_intent.items():
            count = len(intent_events)
            confs = [e.confidence for e in intent_events]
            avg_conf = sum(confs) / count
            max_conf = max(confs)
            latest_t = max(e.timestamp for e in intent_events)
            weight_sum = sum(e.weight for e in intent_events)
            time_since_last = max(0.0, current_time - latest_t)
            
            summary[intent] = IntentStats(
                intent=intent,
                count=count,
                average_confidence=avg_conf,
                highest_confidence=max_conf,
                latest_timestamp=latest_t,
                weight_sum=weight_sum,
                time_since_last_seen=time_since_last
            )
            
        return summary
