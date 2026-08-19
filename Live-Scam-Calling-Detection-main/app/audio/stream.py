class AudioStream:
    """Manages raw audio input streams."""
    def __init__(self, chunk_size: int = 1024):
        self.chunk_size = chunk_size

    def read_chunk(self) -> bytes:
        return b""
