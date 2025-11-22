"""
Data extraction and normalization logic
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
from dateutil import parser as date_parser
from .config import DATE_FORMATS

logger = logging.getLogger(__name__)


class DataExtractor:
    """Extracts and normalizes data from Excel rows"""
    
    @staticmethod
    def extract_rows(df: pd.DataFrame, header_row_idx: int, field_map: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract data rows from DataFrame
        
        Args:
            df: DataFrame loaded from Excel
            header_row_idx: Index of the header row
            field_map: Dictionary mapping standard field names to column indices
            
        Returns:
            List of dictionaries, each representing a production item
        """
        items = []
        
        # Start from row after header
        data_start_idx = header_row_idx + 1
        
        for row_idx in range(data_start_idx, len(df)):
            row_values = df.iloc[row_idx].values
            
            # Skip empty rows
            if DataExtractor._is_empty_row(row_values):
                continue
            
            # Extract item data
            item = DataExtractor._extract_item(row_values, field_map)
            
            if item:
                items.append(item)
                logger.debug(f"Extracted item from row {row_idx}: {item.get('order_number', 'N/A')}")
        
        logger.info(f"Extracted {len(items)} production items")
        return items
    
    @staticmethod
    def _is_empty_row(row_values: List) -> bool:
        """Check if a row is empty or contains only None/NaN values"""
        return all(pd.isna(val) or val is None or str(val).strip() == "" 
                  for val in row_values)
    
    @staticmethod
    def _extract_item(row_values: List, field_map: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract a single production item from a row
        
        Args:
            row_values: List of values from the row
            field_map: Dictionary mapping field names to column indices
            
        Returns:
            Dictionary with extracted data, or None if row is invalid
        """
        item = {}
        
        # Extract basic fields
        for field_name, col_idx in field_map.items():
            if field_name == 'milestones' or field_name == '_confidence':
                continue  # Handle milestones separately and skip metadata
            
            if col_idx < len(row_values):
                value = row_values[col_idx]
                
                # Normalize the value
                if pd.notna(value) and value is not None:
                    if field_name == 'shipping_date':
                        item[field_name] = DataExtractor._parse_date(value)
                    elif field_name == 'quantity':
                        item[field_name] = DataExtractor._parse_number(value)
                    else:
                        item[field_name] = str(value).strip()
        
        # Extract milestone data
        if 'milestones' in field_map:
            milestones = DataExtractor._extract_milestones(
                row_values, field_map['milestones']
            )
            if milestones:
                item['milestones'] = milestones
        
        # Only return item if it has at least order_number or style
        if 'order_number' in item or 'style' in item:
            return item
        
        return None
    
    @staticmethod
    def _extract_milestones(row_values: List, milestone_map: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, Any]]:
        """
        Extract milestone data from a row
        
        Args:
            row_values: List of values from the row
            milestone_map: Nested dict mapping milestone names to field indices
            
        Returns:
            Dictionary with milestone data
        """
        milestones = {}
        
        for milestone_name, fields in milestone_map.items():
            milestone_data = {}
            
            for field_name, col_idx in fields.items():
                if col_idx < len(row_values):
                    value = row_values[col_idx]
                    
                    if pd.notna(value) and value is not None and str(value).strip():
                        # Parse based on field type
                        if 'date' in field_name:
                            parsed_value = DataExtractor._parse_date(value)
                        elif 'qty' in field_name or 'quantity' in field_name or 'weight' in field_name:
                            parsed_value = DataExtractor._parse_number(value)
                        else:
                            parsed_value = str(value).strip()
                        
                        if parsed_value is not None:
                            milestone_data[field_name] = parsed_value
            
            if milestone_data:
                milestones[milestone_name] = milestone_data
        
        return milestones
    
    @staticmethod
    def _parse_date(value: Any) -> Optional[str]:
        """
        Parse a date value into ISO format string
        
        Args:
            value: Date value (can be string, datetime, etc.)
            
        Returns:
            ISO format date string (YYYY-MM-DD) or None if parsing fails
        """
        if pd.isna(value) or value is None:
            return None
        
        # If already a datetime
        if isinstance(value, (datetime, pd.Timestamp)):
            return value.strftime('%Y-%m-%d')
        
        # Try to parse as string
        value_str = str(value).strip()
        if not value_str:
            return None
        
        # Try dateutil parser first (handles many formats)
        try:
            parsed_date = date_parser.parse(value_str, dayfirst=True)
            return parsed_date.strftime('%Y-%m-%d')
        except:
            pass
        
        # Try specific formats
        for fmt in DATE_FORMATS:
            try:
                parsed_date = datetime.strptime(value_str, fmt)
                return parsed_date.strftime('%Y-%m-%d')
            except:
                continue
        
        logger.warning(f"Could not parse date: {value_str}")
        return value_str  # Return original if can't parse
    
    @staticmethod
    def _parse_number(value: Any) -> Optional[float]:
        """
        Parse a numeric value
        
        Args:
            value: Numeric value (can be string, int, float, etc.)
            
        Returns:
            Float value or None if parsing fails
        """
        if pd.isna(value) or value is None:
            return None
        
        # If already a number
        if isinstance(value, (int, float)):
            return float(value)
        
        # Try to parse as string
        value_str = str(value).strip()
        if not value_str:
            return None
        
        try:
            # Remove common non-numeric characters
            cleaned = value_str.replace(',', '').replace(' ', '')
            return float(cleaned)
        except:
            logger.warning(f"Could not parse number: {value_str}")
            return None
