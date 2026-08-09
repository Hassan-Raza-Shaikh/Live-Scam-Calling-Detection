from app.benchmark.latency import LatencyProfiler
from app.benchmark.cpu import CPUTracker
from app.benchmark.memory import MemoryProfiler

class MainProfiler:
    """Consolidates latency, CPU, and memory profiles."""
    def __init__(self):
        self.latency = LatencyProfiler()
        self.cpu = CPUTracker()
        self.memory = MemoryProfiler()
