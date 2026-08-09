import re
from typing import Pattern

class PatternCompiler:
    """Compiles wildcard patterns, exact phrases, and raw regexes into Python re.Pattern objects at startup."""
    
    @staticmethod
    def compile_phrase(phrase: str) -> re.Pattern:
        """Compiles an exact phrase into a regex using word boundaries to prevent partial matches.
        
        For example, 'otp' should match 'otp', but not 'hotpot'.
        
        Args:
            phrase: The exact phrase string.
            
        Returns:
            A compiled re.Pattern object.
        """
        normalized_phrase = phrase.strip().lower()
        escaped = re.escape(normalized_phrase)
        
        # Add word boundaries only if the boundary characters are alphanumeric
        start_boundary = r"\b" if escaped and escaped[0].isalnum() else ""
        end_boundary = r"\b" if escaped and escaped[-1].isalnum() else ""
        
        return re.compile(f"{start_boundary}{escaped}{end_boundary}")

    @staticmethod
    def compile_wildcard(wildcard_pattern: str) -> re.Pattern:
        """Compiles a wildcard pattern (e.g. 'tell me * code') into a compiled regex object.
        
        Replaces '*' with a non-greedy match (.*?) and adds appropriate boundaries.
        
        Args:
            wildcard_pattern: The wildcard pattern string.
            
        Returns:
            A compiled re.Pattern object.
        """
        normalized_pattern = wildcard_pattern.strip().lower()
        
        # Split by wildcards and escape each literal segment
        parts = normalized_pattern.split("*")
        escaped_parts = [re.escape(part) for part in parts]
        
        # Rejoin using a non-greedy wildcard pattern that matches any characters
        regex_str = ".*?".join(escaped_parts)
        
        start_boundary = r"\b" if regex_str and regex_str[0].isalnum() else ""
        end_boundary = r"\b" if regex_str and regex_str[-1].isalnum() else ""
        
        return re.compile(f"{start_boundary}{regex_str}{end_boundary}")

    @staticmethod
    def compile_regex(regex_str: str) -> re.Pattern:
        """Compiles a standard regex string.
        
        Args:
            regex_str: The regex pattern string.
            
        Returns:
            A compiled re.Pattern object.
        """
        # Compiling without case-sensitivity flags since transcripts are pre-normalized/lowercased,
        # but compiling with flags can be a fallback for safety.
        return re.compile(regex_str)
