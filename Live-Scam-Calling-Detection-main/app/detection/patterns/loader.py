import os
import yaml
from pathlib import Path
from typing import Dict, Optional, Union
from app.detection.exceptions import PatternLoadError
from app.detection.models import PatternDatabase, PatternRule, IntentMetadata
from app.detection.patterns.compiler import PatternCompiler
from app.utils.logger import get_logger

logger = get_logger("detection.pattern_loader")

class PatternLoader:
    """Discovers, validates, compiles, and caches YAML pattern files."""
    
    def __init__(self, database_dir: Union[str, Path]):
        self.database_dir = Path(database_dir)
        self._cache: Optional[PatternDatabase] = None

    def load(self, force_reload: bool = False) -> PatternDatabase:
        """Loads and compiles pattern rules from YAML files in the database directory.
        
        Args:
            force_reload: If True, ignores the internal cache and reloads.
            
        Returns:
            The populated PatternDatabase object.
            
        Raises:
            PatternLoadError: If schema validation, file reading, or compilation fails.
        """
        if self._cache is not None and not force_reload:
            return self._cache

        if not self.database_dir.exists() or not self.database_dir.is_dir():
            raise PatternLoadError(f"Database directory does not exist or is not a directory: {self.database_dir}")

        rules: Dict[str, PatternRule] = {}
        intents: Dict[str, IntentMetadata] = {}
        source_files: Dict[str, str] = {}

        yaml_files = list(self.database_dir.glob("*.yaml")) + list(self.database_dir.glob("*.yml"))
        
        for file_path in yaml_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                
                if not data:
                    logger.warning(f"Empty pattern database file skipped: {file_path}")
                    continue
                
                self._validate_schema(data, file_path)
                
                intent = data["intent"]
                description = data["description"]
                category = data["category"]
                weight = int(data["weight"])
                priority = data["priority"]
                
                future_config = data.get("future", {})
                enable_fuzzy = future_config.get("enable_fuzzy", False)
                enable_embeddings = future_config.get("enable_embeddings", False)
                
                phrases = data.get("phrases", [])
                patterns = data.get("patterns", [])
                regex_strings = data.get("regex", [])
                
                # Compile all rules using PatternCompiler
                compiled_phrases = [PatternCompiler.compile_phrase(p) for p in phrases]
                compiled_patterns = [PatternCompiler.compile_wildcard(p) for p in patterns]
                compiled_regexes = [PatternCompiler.compile_regex(r) for r in regex_strings]
                
                intent_metadata = IntentMetadata(
                    intent=intent,
                    description=description,
                    category=category,
                    weight=weight,
                    priority=priority,
                    enable_fuzzy=enable_fuzzy,
                    enable_embeddings=enable_embeddings
                )
                
                pattern_rule = PatternRule(
                    intent=intent,
                    phrases=phrases,
                    patterns=patterns,
                    regex=regex_strings,
                    compiled_phrases=compiled_phrases,
                    compiled_patterns=compiled_patterns,
                    compiled_regexes=compiled_regexes
                )
                
                intents[intent] = intent_metadata
                rules[intent] = pattern_rule
                source_files[intent] = file_path.name
                
            except Exception as e:
                if isinstance(e, PatternLoadError):
                    raise e
                raise PatternLoadError(f"Error loading schema from {file_path}: {str(e)}") from e

        self._cache = PatternDatabase(rules=rules, intents=intents, source_files=source_files)
        return self._cache

    def _validate_schema(self, data: dict, file_path: Path) -> None:
        """Validates that a dictionary parsed from YAML meets framework requirements.
        
        Args:
            data: Parsed dictionary from YAML.
            file_path: Location of the YAML file for logging/errors.
            
        Raises:
            PatternLoadError: If required fields are missing or have invalid types.
        """
        if not isinstance(data, dict):
            raise PatternLoadError(f"Pattern schema must be a dictionary in file: {file_path}")

        required_fields = ["intent", "description", "category", "weight", "priority"]
        for field_name in required_fields:
            if field_name not in data:
                raise PatternLoadError(f"Missing required field '{field_name}' in file: {file_path}")
        
        # Validate data types
        if not isinstance(data["intent"], str) or not data["intent"]:
            raise PatternLoadError(f"Field 'intent' must be a non-empty string in file: {file_path}")
        
        if not isinstance(data["description"], str):
            raise PatternLoadError(f"Field 'description' must be a string in file: {file_path}")
            
        if not isinstance(data["category"], str):
            raise PatternLoadError(f"Field 'category' must be a string in file: {file_path}")
            
        try:
            int(data["weight"])
        except (ValueError, TypeError) as e:
            raise PatternLoadError(f"Field 'weight' must be an integer, got {data['weight']} in file: {file_path}") from e
            
        if not isinstance(data["priority"], str) or data["priority"] not in ("low", "medium", "high"):
            raise PatternLoadError(f"Field 'priority' must be 'low', 'medium', or 'high', got '{data['priority']}' in file: {file_path}")
            
        # Verify optional lists
        for list_field in ("phrases", "patterns", "regex"):
            if list_field in data:
                if not isinstance(data[list_field], list):
                    raise PatternLoadError(f"Optional field '{list_field}' must be a list in file: {file_path}")
                for idx, item in enumerate(data[list_field]):
                    if not isinstance(item, str):
                        raise PatternLoadError(f"Item at index {idx} in field '{list_field}' must be a string in file: {file_path}")
