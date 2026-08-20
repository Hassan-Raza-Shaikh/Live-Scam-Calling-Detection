from typing import List, Dict, Any

class SpeakerTracker:
    """Tracks active speaking turns, speaker transition timeline, and speaking durations."""
    
    def __init__(self):
        self.turns: List[Dict[str, Any]] = []
        self.speaker_durations: Dict[str, float] = {"CALLER": 0.0, "VICTIM": 0.0}
        self.turn_counts: Dict[str, int] = {"CALLER": 0, "VICTIM": 0}
        self.last_speaker: str = "CALLER"

    def register_turn(self, speaker: str, duration_sec: float = 1.0, text: str = ""):
        speaker_upper = speaker.upper()
        if speaker_upper not in self.speaker_durations:
            self.speaker_durations[speaker_upper] = 0.0
            self.turn_counts[speaker_upper] = 0
            
        self.speaker_durations[speaker_upper] += duration_sec
        self.turn_counts[speaker_upper] += 1
        self.last_speaker = speaker_upper
        
        self.turns.append({
            "speaker": speaker_upper,
            "duration": duration_sec,
            "text": text,
            "turn_index": len(self.turns) + 1
        })

    def get_summary(self) -> Dict[str, Any]:
        total_turns = sum(self.turn_counts.values())
        return {
            "total_turns": total_turns,
            "caller_turns": self.turn_counts.get("CALLER", 0),
            "victim_turns": self.turn_counts.get("VICTIM", 0),
            "speaker_durations": self.speaker_durations,
            "last_speaker": self.last_speaker
        }
