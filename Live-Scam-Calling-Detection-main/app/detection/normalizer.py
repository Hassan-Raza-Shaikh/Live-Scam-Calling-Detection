import re
import unicodedata
from app.detection.exceptions import NormalizationError

class Normalizer:
    """Dedicated text normalizer to clean and standardize transcripts.
    
    Performs lowercasing, unicode normalization, trimming, collapsing repeated
    whitespace, and optional punctuation removal.
    """
    
    def __init__(self, remove_punctuation: bool = True):
        self.remove_punctuation = remove_punctuation
        # Matches standard ASCII punctuation characters
        self._punctuation_pattern = re.compile(r'[!"#$%&\'()*+,\-./:;<=>?@\[\\\]^_`{|}~]')
        # Matches any sequence of whitespace characters
        self._whitespace_pattern = re.compile(r'\s+')

    def normalize(self, text: str) -> str:
        """Standardizes the input text by applying normalization steps.
        
        Args:
            text: The raw string to normalize.
            
        Returns:
            The normalized string.
            
        Raises:
            NormalizationError: If the input is not a string.
        """
        if not isinstance(text, str):
            raise NormalizationError(f"Input transcript must be a string, got {type(text)}")
        
        try:
            # 1. Unicode Normalization (NFKC)
            normalized = unicodedata.normalize('NFKC', text)
            
            # 2. Lowercase
            normalized = normalized.lower()
            
            # 3. Optional Punctuation Removal
            if self.remove_punctuation:
                normalized = self._punctuation_pattern.sub(' ', normalized)
                
            # 4. Collapse repeated whitespace and Trim
            normalized = self._whitespace_pattern.sub(' ', normalized).strip()
            
            return normalized
        except Exception as e:
            raise NormalizationError(f"Failed to normalize text: {str(e)}") from e
