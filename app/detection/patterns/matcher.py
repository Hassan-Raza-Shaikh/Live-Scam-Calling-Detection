from typing import List, Dict
from app.detection.models import PatternDatabase, Detection
from app.detection.utils import get_current_timestamp

class PatternMatcher:
    """Performs exact phrase matching, wildcard matching, and regex matching.
    
    Reuses compiled regex objects in PatternDatabase to minimize latency.
    """
    
    def match(
        self, 
        normalized_text: str, 
        database: PatternDatabase, 
        source_files: Dict[str, str],
        detector_name: str = "PatternDetector"
    ) -> List[Detection]:
        """Matches normalized text against the pattern database.
        
        Args:
            normalized_text: Normalized transcript string.
            database: Preloaded and precompiled PatternDatabase.
            source_files: Dictionary mapping intent to source filename.
            detector_name: Name of the detector running this matcher.
            
        Returns:
            A list of Detection dataclass objects.
        """
        detections: List[Detection] = []
        if not normalized_text:
            return detections

        for intent, rule in database.rules.items():
            metadata = database.intents.get(intent)
            weight = metadata.weight if metadata else 0
            source_file = source_files.get(intent, "unknown.yaml")

            # 1. Exact phrase matching (using compiled re.Pattern)
            for idx, compiled_phrase in enumerate(rule.compiled_phrases):
                phrase_str = rule.phrases[idx]
                for match_obj in compiled_phrase.finditer(normalized_text):
                    detections.append(
                        Detection(
                            intent=intent,
                            matched_text=match_obj.group(0),
                            matched_rule=phrase_str,
                            confidence=1.0,
                            weight=weight,
                            detector_name=detector_name,
                            matching_strategy="phrase",
                            start_index=match_obj.start(),
                            end_index=match_obj.end(),
                            source_file=source_file,
                            timestamp=get_current_timestamp()
                        )
                    )

            # 2. Wildcard matching (using compiled re.Pattern)
            for idx, compiled_wildcard in enumerate(rule.compiled_patterns):
                pattern_str = rule.patterns[idx]
                for match_obj in compiled_wildcard.finditer(normalized_text):
                    detections.append(
                        Detection(
                            intent=intent,
                            matched_text=match_obj.group(0),
                            matched_rule=pattern_str,
                            confidence=1.0,
                            weight=weight,
                            detector_name=detector_name,
                            matching_strategy="wildcard",
                            start_index=match_obj.start(),
                            end_index=match_obj.end(),
                            source_file=source_file,
                            timestamp=get_current_timestamp()
                        )
                    )

            # 3. Regex matching (using compiled re.Pattern)
            for idx, compiled_regex in enumerate(rule.compiled_regexes):
                regex_str = rule.regex[idx]
                for match_obj in compiled_regex.finditer(normalized_text):
                    detections.append(
                        Detection(
                            intent=intent,
                            matched_text=match_obj.group(0),
                            matched_rule=regex_str,
                            confidence=1.0,
                            weight=weight,
                            detector_name=detector_name,
                            matching_strategy="regex",
                            start_index=match_obj.start(),
                            end_index=match_obj.end(),
                            source_file=source_file,
                            timestamp=get_current_timestamp()
                        )
                    )

        return detections
