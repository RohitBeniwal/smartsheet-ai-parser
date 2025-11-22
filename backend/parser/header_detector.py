"""
Header detection logic for Excel files
"""
import logging
from typing import List, Tuple, Optional
import pandas as pd
from .config import HEADER_KEYWORDS, MAX_HEADER_SEARCH_ROWS, MIN_HEADER_CELLS

logger = logging.getLogger(__name__)


class HeaderDetector:
    """Detects header rows in Excel sheets"""
    
    @staticmethod
    def detect_header_row(df: pd.DataFrame) -> Tuple[Optional[int], Optional[List[str]]]:
        """
        Detect which row contains the column headers
        
        Args:
            df: DataFrame loaded from Excel
            
        Returns:
            Tuple of (header_row_index, header_values)
            Returns (None, None) if no header found
        """
        max_rows = min(MAX_HEADER_SEARCH_ROWS, len(df))
        
        best_row_idx = None
        best_score = 0
        best_headers = None
        
        for row_idx in range(max_rows):
            row_values = df.iloc[row_idx].values
            
            # Skip empty rows
            non_empty_count = sum(1 for val in row_values if pd.notna(val) and str(val).strip())
            if non_empty_count == 0:
                continue
            
            # Skip title rows (first cell has content, but most others are empty)
            if non_empty_count <= 2:
                continue
            
            # Check if this row looks like a header
            score = HeaderDetector._score_header_row(row_values)
            
            logger.debug(f"Row {row_idx} header score: {score} (non-empty: {non_empty_count})")
            
            # Track the row with the highest score
            if score > best_score:
                best_score = score
                best_row_idx = row_idx
                best_headers = [str(val).strip() if pd.notna(val) else None 
                              for val in row_values]
        
        # Return the best match if score is high enough
        if best_row_idx is not None and best_score >= MIN_HEADER_CELLS:
            logger.info(f"Header row detected at index {best_row_idx} with score {best_score}")
            return best_row_idx, best_headers
        
        logger.warning("No clear header row detected")
        return None, None
    
    @staticmethod
    def _score_header_row(row_values: List) -> int:
        """
        Score a row based on how likely it is to be a header
        
        Args:
            row_values: List of values in the row
            
        Returns:
            Score (higher = more likely to be header)
        """
        score = 0
        
        for val in row_values:
            if pd.isna(val) or val is None or str(val).strip() == "":
                continue
            
            val_str = str(val).strip().lower()
            
            # Check if value looks like a header keyword
            for keyword in HEADER_KEYWORDS:
                if keyword in val_str:
                    score += 1
                    break
            
            # Check if value is text (not a number or date-like)
            # Headers are usually text, not numeric data
            if not HeaderDetector._looks_like_data(val_str):
                score += 0.5
        
        return score
    
    @staticmethod
    def _looks_like_data(val_str: str) -> bool:
        """
        Check if value looks like data (number, date) rather than header
        
        Args:
            val_str: String value to check
            
        Returns:
            True if looks like data, False if looks like header text
        """
        # Check if it's primarily numeric
        if val_str.replace(".", "").replace("-", "").replace("/", "").isdigit():
            return True
        
        # Very short strings might be data codes
        if len(val_str) <= 3 and val_str.isupper():
            return True
        
        return False
    
    @staticmethod
    def find_milestone_headers(first_row: List) -> dict:
        """
        Find milestone section headers from the first row
        
        Args:
            first_row: Values from the first row of the sheet
            
        Returns:
            Dictionary mapping column indices to milestone names
        """
        milestones = {}
        
        for idx, val in enumerate(first_row):
            if pd.notna(val) and val:
                val_str = str(val).strip().lower()
                # Check if this looks like a milestone header
                if any(keyword in val_str for keyword in 
                       ["fabric", "cutting", "sewing", "vap", "feeding", 
                        "embroidery", "finishing", "size set"]):
                    milestones[idx] = val_str
        
        return milestones
