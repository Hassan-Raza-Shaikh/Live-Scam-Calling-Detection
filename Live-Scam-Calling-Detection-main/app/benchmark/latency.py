class LatencyProfiler:
    """Measures audio-to-alert processing latency."""
    def measure_latency_ms(self, start_time: float, end_time: float) -> float:
        return (end_time - start_time) * 1000.0
