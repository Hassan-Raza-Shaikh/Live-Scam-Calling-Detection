import time

def get_current_timestamp() -> float:
    """Returns the current system epoch timestamp in seconds."""
    return time.time()

def format_relative_time(seconds: float) -> str:
    """Formats a relative duration (seconds) into MM:SS format.
    
    Example:
        4.5 -> "00:04"
        72.0 -> "01:12"
    """
    total_seconds = max(0, int(seconds))
    minutes = total_seconds // 60
    secs = total_seconds % 60
    return f"{minutes:02d}:{secs:02d}"
