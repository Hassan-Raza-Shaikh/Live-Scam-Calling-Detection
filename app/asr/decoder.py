import numpy as np
try:
    import sherpa_onnx
except ImportError:
    sherpa_onnx = None
from app.utils.logger import get_logger

logger = get_logger(__name__)

class ASRStreamDecoder:
    """
    Manages a single online recognition stream, feeding audio waveform
    and extracting progressive transcripts.
    """
    
    def __init__(self, recognizer: "Any", sample_rate: int = 16000):
        """
        Initialize the decoder stream wrapper.

        Args:
            recognizer: The initialized OnlineRecognizer instance.
            sample_rate: Expected sample rate of input audio (default 16000).
        """
        self.recognizer = recognizer
        self.sample_rate = sample_rate
        self.stream = self.recognizer.create_stream()
        self.last_text = ""

    def decode_chunk(self, samples: np.ndarray) -> tuple[str, bool]:
        """
        Accepts raw float32 mono audio chunk and decodes it.

        Args:
            samples: 1D numpy array of float32 samples.

        Returns:
            A tuple of (decoded_text, is_endpoint).
        """
        if samples.ndim != 1:
            raise ValueError("Input audio samples must be a 1D array.")

        # Feed audio into stream
        self.stream.accept_waveform(self.sample_rate, samples)

        # Decode available frames
        while self.recognizer.is_ready(self.stream):
            self.recognizer.decode_stream(self.stream)

        # Get decoded text result
        result = self.recognizer.get_result(self.stream)
        if isinstance(result, str):
            text = result.strip()
        elif hasattr(result, "text"):
            text = result.text.strip() if result.text else ""
        else:
            text = str(result).strip() if result else ""

        # Check endpoint detection
        is_endpoint = self.recognizer.is_endpoint(self.stream)
        if is_endpoint:
            logger.info("✓ Endpoint detected")
            final_text = text
            self.reset_stream()
            return final_text, True

        self.last_text = text
        return text, False

    def reset_stream(self):
        """
        Resets the internal stream decoder state.
        """
        self.recognizer.reset(self.stream)
        logger.info("✓ Decoder reset")
        self.last_text = ""
