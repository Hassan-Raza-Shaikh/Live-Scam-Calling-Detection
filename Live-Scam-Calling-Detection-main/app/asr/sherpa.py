import os
import numpy as np
try:
    import sherpa_onnx
except ImportError:
    sherpa_onnx = None
from app.config import settings
from app.utils.logger import get_logger
from app.asr.decoder import ASRStreamDecoder

logger = get_logger(__name__)

class ASRInitializationError(Exception):
    """Raised when the ASR engine or its models fail to initialize."""
    pass

class ASRService:
    """
    Production-quality streaming ASR Service using the Sherpa-ONNX Python API.
    Provides simple interface to process live PCM audio chunks and retrieve transcripts.
    """

    def __init__(self):
        self._recognizer = None
        self._decoder = None
        self._initialized = False
        self._initialize_recognizer()

    def _initialize_recognizer(self):
        """
        Initializes the OnlineRecognizer and Decoder stream.
        Raises:
            ASRInitializationError if model files are missing or initialization fails.
        """
        if sherpa_onnx is None:
            raise ASRInitializationError(
                "sherpa-onnx is not installed. Please activate the virtual environment (.venv) or run: pip install sherpa-onnx"
            )
        encoder = settings.asr_encoder_path
        decoder = settings.asr_decoder_path
        joiner = settings.asr_joiner_path
        tokens = settings.asr_tokens_path

        # Validate that paths exist
        missing_files = []
        for filepath, name in [
            (encoder, "Encoder Model"),
            (decoder, "Decoder Model"),
            (joiner, "Joiner Model"),
            (tokens, "Tokens File")
        ]:
            if not filepath:
                missing_files.append(f"{name}: path not specified")
            elif not os.path.exists(filepath):
                missing_files.append(f"{name}: not found at '{filepath}'")

        if missing_files:
            error_msg = "; ".join(missing_files)
            logger.error(f"✕ Model loading failed: {error_msg}")
            raise ASRInitializationError(f"Missing required model files: {error_msg}")

        try:
            logger.info("Initializing OnlineRecognizer from transducer model...")
            self._recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
                tokens=tokens,
                encoder=encoder,
                decoder=decoder,
                joiner=joiner,
                num_threads=settings.asr_num_threads,
                sample_rate=settings.asr_sample_rate,
                feature_dim=settings.asr_feature_dim,
                enable_endpoint_detection=settings.asr_enable_endpoint,
                decoding_method=settings.asr_decoding_method,
                provider="cpu"
            )
            self._decoder = ASRStreamDecoder(self._recognizer, sample_rate=settings.asr_sample_rate)
            self._initialized = True
            logger.info("✓ Model loaded")
            logger.info("✓ Recognizer initialized")
        except Exception as e:
            logger.error(f"✕ Recognizer initialization failure: {e}")
            raise ASRInitializationError(f"Recognizer failed to initialize: {e}")

    def process_audio(self, samples: np.ndarray) -> str:
        """
        Accept one chunk of float32 PCM audio, decodes it, and returns the transcript.

        Args:
            samples: 1D numpy array of float32 PCM audio (16 kHz, mono).

        Returns:
            The progressive/partial text transcript.
        """
        if not self._initialized:
            raise RuntimeError("ASRService is not initialized.")

        if not isinstance(samples, np.ndarray):
            raise ValueError("Audio samples must be a numpy.ndarray.")

        if samples.dtype != np.float32:
            raise ValueError("Audio samples must be float32.")

        # Decode the chunk and check for endpoints
        text, is_endpoint = self._decoder.decode_chunk(samples)
        return text

    def reset(self):
        """
        Resets the underlying decoder stream.
        """
        if self._decoder:
            self._decoder.reset_stream()
