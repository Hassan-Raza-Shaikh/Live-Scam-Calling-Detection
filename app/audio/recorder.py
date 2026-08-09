import queue
import sounddevice as sd
import numpy as np

class AudioRecorder:
    """Handles local microphone or system audio capture."""
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.q = queue.Queue()

    def stream(self):
        """
        Yields audio chunks from the microphone as 1D float32 numpy arrays.
        """
        def callback(indata, frames, time_info, status):
            self.q.put(indata.copy())

        # Use a block size of 1024 samples for low latency (~64ms chunks at 16kHz)
        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype='float32',
            blocksize=1024,
            callback=callback
        ):
            while True:
                chunk = self.q.get()
                # Squeeze to convert from (blocksize, 1) to 1D array (blocksize,)
                yield chunk.squeeze()

    def start_recording(self):
        pass

    def stop_recording(self):
        pass
