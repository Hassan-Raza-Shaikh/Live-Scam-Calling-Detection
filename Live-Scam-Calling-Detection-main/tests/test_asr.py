import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from app.asr.sherpa import ASRService, ASRInitializationError

def test_asr_service_missing_model_raises_exception():
    """Verify ASRService raises ASRInitializationError when model files do not exist."""
    with patch("os.path.exists", return_value=False):
        with pytest.raises(ASRInitializationError) as exc_info:
            ASRService()
        assert "Missing required model files" in str(exc_info.value)

@patch("os.path.exists", return_value=True)
@patch("sherpa_onnx.OnlineRecognizer.from_transducer")
def test_asr_service_mock_successful_decoding(mock_from_transducer, mock_exists):
    """Test ASRService logic flow using mocked recognizer and stream."""
    # 1. Setup mock recognizer and stream
    mock_recognizer = MagicMock()
    mock_stream = MagicMock()
    mock_from_transducer.return_value = mock_recognizer
    mock_recognizer.create_stream.return_value = mock_stream
    
    # Mock recognizer results
    mock_recognizer.is_ready.side_effect = [True, False]  # One decode loop
    mock_result = MagicMock()
    mock_result.text = "hello sir"
    mock_recognizer.get_result.return_value = mock_result
    mock_recognizer.is_endpoint.return_value = False

    # 2. Instantiate and process
    service = ASRService()
    samples = np.zeros(16000, dtype=np.float32)
    transcript = service.process_audio(samples)

    # 3. Assertions
    assert transcript == "hello sir"
    mock_stream.accept_waveform.assert_called_once()
    mock_recognizer.decode_stream.assert_called_once_with(mock_stream)
    mock_recognizer.reset.assert_not_called()

@patch("os.path.exists", return_value=True)
@patch("sherpa_onnx.OnlineRecognizer.from_transducer")
def test_asr_service_endpoint_detection_resets_stream(mock_from_transducer, mock_exists):
    """Test that stream is reset when endpoint is detected."""
    # 1. Setup mock recognizer and stream
    mock_recognizer = MagicMock()
    mock_stream = MagicMock()
    mock_from_transducer.return_value = mock_recognizer
    mock_recognizer.create_stream.return_value = mock_stream
    
    # Mock recognizer results
    mock_recognizer.is_ready.side_effect = [True, False]
    mock_result = MagicMock()
    mock_result.text = "hello sir this is your bank"
    mock_recognizer.get_result.return_value = mock_result
    mock_recognizer.is_endpoint.return_value = True

    # 2. Instantiate and process
    service = ASRService()
    samples = np.zeros(16000, dtype=np.float32)
    transcript = service.process_audio(samples)

    # 3. Assertions
    assert transcript == "hello sir this is your bank"
    mock_recognizer.reset.assert_called_once_with(mock_stream)
