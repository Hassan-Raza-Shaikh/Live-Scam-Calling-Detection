import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass(frozen=True)
class IntentMetadata:
    """Metadata representing a specific scam intent, its priority, category, weight, and settings."""
    intent: str
    description: str
    category: str
    weight: int
    priority: str
    enable_fuzzy: bool = False
    enable_embeddings: bool = False

@dataclass
class PatternRule:
    """Compiled rule mapping an intent to its exact phrases, patterns, and regexes."""
    intent: str
    phrases: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    regex: List[str] = field(default_factory=list)
    # Compiled regular expressions for runtime execution
    compiled_phrases: List[re.Pattern] = field(default_factory=list)
    compiled_patterns: List[re.Pattern] = field(default_factory=list)
    compiled_regexes: List[re.Pattern] = field(default_factory=list)


@dataclass
class PatternDatabase:
    """Collection of loaded pattern rules and their corresponding intent metadata."""
    rules: Dict[str, PatternRule] = field(default_factory=dict)
    intents: Dict[str, IntentMetadata] = field(default_factory=dict)
    source_files: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Detection:
    """Represents a single detection result with matching metadata, rules, and confidence levels."""
    intent: str
    matched_text: str
    matched_rule: str
    confidence: float
    weight: int
    detector_name: str
    matching_strategy: str  # 'phrase', 'wildcard', 'regex', etc.
    start_index: int
    end_index: int
    source_file: str
    timestamp: float

@dataclass(frozen=True)
class DetectionReport:
    """Result returned by the Detection Engine, containing all details of the detection session."""
    original_transcript: str
    normalized_transcript: str
    detections: List[Detection] = field(default_factory=list)
    processing_time_ms: float = 0.0
    detector_versions: Dict[str, str] = field(default_factory=dict)
    timestamp: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
