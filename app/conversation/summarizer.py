from app.conversation.interfaces import ISummarizer
from app.conversation.models import ConversationSnapshot

class StructuredSummarizer(ISummarizer):
    """Generates structured, human-readable text summaries from a ConversationSnapshot.
    
    This operates deterministically without calling LLMs or external services.
    """
    
    def summarize(self, snapshot: ConversationSnapshot) -> str:
        """Constructs a formatted summary string.
        
        Args:
            snapshot: An immutable ConversationSnapshot.
            
        Returns:
            A formatted multi-line summary string.
        """
        lines = [
            "Conversation Summary",
            f"Call ID: {snapshot.call_id}",
            f"Phase: {snapshot.phase}",
            f"Duration: {int(snapshot.duration)} seconds",
            f"Dominant Intent: {snapshot.stats.dominant_intent}"
        ]
        
        lines.append("Intent Counts:")
        if snapshot.intent_summary:
            # Sort intent stats by count descending
            sorted_intents = sorted(
                snapshot.intent_summary.values(),
                key=lambda x: x.count,
                reverse=True
            )
            for item in sorted_intents:
                lines.append(f"  {item.intent}: {item.count}")
        else:
            lines.append("  (No intents detected)")
            
        lines.append(f"Highest Confidence: {snapshot.stats.highest_confidence:.2f}")
        
        lines.append("Recent Timeline:")
        if snapshot.timeline:
            for entry in snapshot.timeline[-5:]:
                lines.append(f"  {entry.formatted_time} -> {entry.intent}")
        else:
            lines.append("  (Timeline is empty)")
            
        return "\n".join(lines)
