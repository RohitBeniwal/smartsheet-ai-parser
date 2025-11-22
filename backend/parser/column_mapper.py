"""
Column mapping logic - maps detected headers to standard field names
"""
import logging
import re
from typing import Dict, List, Optional, Tuple
from fuzzywuzzy import fuzz
from .config import FIELD_PATTERNS, MILESTONE_KEYWORDS, MILESTONE_SUBFIELDS

logger = logging.getLogger(__name__)


def normalize_column_name(name: str) -> str:
    """
    Normalize column name for better matching
    
    Args:
        name: Column name to normalize
        
    Returns:
        Normalized column name
    """
    if not name or not isinstance(name, str):
        return ""
    
    # Convert to lowercase
    name = name.lower().strip()
    
    # Remove special characters except spaces and hyphens
    name = re.sub(r'[^\w\s-]', '', name)
    
    # Handle common abbreviations
    abbreviations = {
        ' no ': ' number ',
        ' qty ': ' quantity ',
        ' pt ': ' point ',
        ' amt ': ' amount ',
        ' req ': ' required ',
        ' spec ': ' specification ',
    }
    
    for abbr, full in abbreviations.items():
        name = name.replace(abbr, full)
    
    # Remove extra whitespace
    name = ' '.join(name.split())
    
    return name

# Confidence thresholds
EXACT_MATCH_CONFIDENCE = 1.0
FUZZY_MATCH_THRESHOLD = 85  # Minimum similarity score for fuzzy matching
HIGH_CONFIDENCE_THRESHOLD = 0.90
MEDIUM_CONFIDENCE_THRESHOLD = 0.75


class ColumnMapper:
    """Maps column headers to standard field names"""
    
    @staticmethod
    def map_columns(headers: List[str], milestone_headers: Dict[int, str] = None) -> Dict[str, any]:
        """
        Map column headers to standard field names with confidence scores
        
        Args:
            headers: List of header strings from the Excel file
            milestone_headers: Optional dict mapping column indices to milestone names
            
        Returns:
            Dictionary with mappings and metadata including confidence scores
        """
        field_map = {}
        confidence_scores = {}
        
        # Map basic fields with fuzzy matching
        for field_name, patterns in FIELD_PATTERNS.items():
            result = ColumnMapper._find_matching_column_with_confidence(headers, patterns)
            if result:
                col_idx, confidence, matched_pattern = result
                field_map[field_name] = col_idx
                confidence_scores[field_name] = {
                    'confidence': confidence,
                    'matched_pattern': matched_pattern,
                    'column_name': headers[col_idx]
                }
                
                confidence_level = "HIGH" if confidence > HIGH_CONFIDENCE_THRESHOLD else "MEDIUM" if confidence > MEDIUM_CONFIDENCE_THRESHOLD else "LOW"
                logger.debug(f"Mapped '{field_name}' to column {col_idx}: {headers[col_idx]} (confidence: {confidence:.2f} - {confidence_level})")
        
        # Map milestone fields
        if milestone_headers:
            milestone_map = ColumnMapper._map_milestone_columns(
                headers, milestone_headers
            )
            field_map['milestones'] = milestone_map
        
        # Store confidence metadata
        field_map['_confidence'] = confidence_scores
        
        return field_map
    
    @staticmethod
    def _find_matching_column_with_confidence(headers: List[str], patterns: List[str]) -> Optional[Tuple[int, float, str]]:
        """
        Find column index with confidence score using fuzzy matching
        
        Args:
            headers: List of header strings
            patterns: List of pattern strings to match against
            
        Returns:
            Tuple of (column_index, confidence, matched_pattern) or None
        """
        best_match = None
        best_confidence = 0
        best_pattern = None
        best_idx = None
        
        for idx, header in enumerate(headers):
            if header is None:
                continue
            
            # Normalize column name for better matching
            header_normalized = normalize_column_name(str(header))
            header_lower = header_normalized
            
            for pattern in patterns:
                pattern_normalized = normalize_column_name(pattern)
                pattern_lower = pattern_normalized
                
                # Check for exact match
                if pattern_lower == header_lower:
                    return (idx, EXACT_MATCH_CONFIDENCE, pattern)
                
                # Check for substring match
                if pattern_lower in header_lower:
                    confidence = 0.95  # High confidence for substring match
                    if confidence > best_confidence:
                        best_match = (idx, confidence, pattern)
                        best_confidence = confidence
                        best_idx = idx
                        best_pattern = pattern
                    continue
                
                # Use fuzzy matching for similarity
                similarity = fuzz.ratio(pattern_lower, header_lower)
                
                # Only consider if above threshold
                if similarity >= FUZZY_MATCH_THRESHOLD:
                    # Normalize to 0-1 range
                    confidence = similarity / 100.0
                    
                    if confidence > best_confidence:
                        best_match = (idx, confidence, pattern)
                        best_confidence = confidence
                        best_idx = idx
                        best_pattern = pattern
        
        return best_match
    
    @staticmethod
    def _find_matching_column(headers: List[str], patterns: List[str]) -> Optional[int]:
        """
        Find column index that matches any of the given patterns
        (Legacy method for backward compatibility)
        
        Args:
            headers: List of header strings
            patterns: List of pattern strings to match against
            
        Returns:
            Column index if found, None otherwise
        """
        result = ColumnMapper._find_matching_column_with_confidence(headers, patterns)
        if result:
            return result[0]  # Return just the index
        return None
    
    @staticmethod
    def _map_milestone_columns(headers: List[str], milestone_headers: Dict[int, str]) -> Dict[str, Dict[str, int]]:
        """
        Map milestone-related columns
        
        Args:
            headers: List of header strings
            milestone_headers: Dict mapping column indices to milestone names
            
        Returns:
            Nested dict: {milestone_name: {subfield_name: column_index}}
        """
        milestone_map = {}
        
        # For each detected milestone
        for milestone_start_idx, milestone_name in milestone_headers.items():
            milestone_fields = {}
            
            # Look at columns near this milestone header
            # Typically milestone columns are grouped together
            search_range = range(milestone_start_idx, min(milestone_start_idx + 6, len(headers)))
            
            for col_idx in search_range:
                if col_idx >= len(headers) or headers[col_idx] is None:
                    continue
                
                header_lower = str(headers[col_idx]).strip().lower()
                
                # Try to match subfield patterns
                for subfield_name, patterns in MILESTONE_SUBFIELDS.items():
                    if ColumnMapper._matches_any_pattern(header_lower, patterns):
                        milestone_fields[subfield_name] = col_idx
                        logger.debug(f"Milestone '{milestone_name}' - mapped '{subfield_name}' to column {col_idx}")
                        break
            
            if milestone_fields:
                milestone_map[milestone_name] = milestone_fields
        
        return milestone_map
    
    @staticmethod
    def _matches_any_pattern(text: str, patterns: List[str]) -> bool:
        """
        Check if text matches any of the given patterns
        
        Args:
            text: Text to check
            patterns: List of pattern strings
            
        Returns:
            True if any pattern matches
        """
        text_lower = text.lower()
        for pattern in patterns:
            pattern_lower = pattern.lower()
            if pattern_lower == text_lower or pattern_lower in text_lower:
                return True
        return False
