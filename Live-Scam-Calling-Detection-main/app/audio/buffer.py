class AudioBuffer:
    """Buffers incoming audio data chunks before processing."""
    def __init__(self, max_size_bytes: int = 1024 * 1024):
        self.max_size = max_size_bytes
        self.buffer = bytearray()

    def push(self, data: bytes):
        self.buffer.extend(data)

    def pop(self, size: int) -> bytes:
        chunk = self.buffer[:size]
        del self.buffer[:size]
        return bytes(chunk)
