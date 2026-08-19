import pytest
from app.detection.normalizer import Normalizer
from app.detection.exceptions import NormalizationError

def test_normalizer_basic():
    normalizer = Normalizer(remove_punctuation=True)
    
    # Lowercase & trim
    assert normalizer.normalize("  HELLO WORLD  ") == "hello world"
    
    # Collapse repeated whitespace
    assert normalizer.normalize("hello    world  again") == "hello world again"
    
    # Unicode normalization
    # NFKC normalizes characters like standard full-width form or specific symbols
    assert normalizer.normalize("Ｈｅｌｌｏ Ｗｏｒｌｄ") == "hello world"
    
    # Punctuation removal
    assert normalizer.normalize("hello, world! how's it going?") == "hello world how s it going"

def test_normalizer_keep_punctuation():
    normalizer = Normalizer(remove_punctuation=False)
    assert normalizer.normalize("hello, world!") == "hello, world!"

def test_normalizer_invalid_input():
    normalizer = Normalizer()
    with pytest.raises(NormalizationError):
        normalizer.normalize(123)  # type: ignore
