class SpeakerDiarizer:
    """Distinguishes between CALLER (scammer) and RECEIVER (victim) channels."""
    
    def process_frame(self, audio_data: bytes, channel: int = 0) -> str:
        # Channel 0 is remote caller, Channel 1 is local user mic
        return "CALLER" if channel == 0 else "RECEIVER"
