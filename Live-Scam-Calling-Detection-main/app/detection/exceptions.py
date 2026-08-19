class DetectionError(Exception):
    """Base exception class for all Detection Framework errors."""
    pass

class PatternLoadError(DetectionError):
    """Raised when patterns database YAML files fail to locate, load, or validate."""
    pass

class NormalizationError(DetectionError):
    """Raised when normalizer encounters invalid encoding or input issues."""
    pass
