"""
Main Excel parser - orchestrates header detection, column mapping, and data extraction
"""
import logging
from typing import Dict, List, Any, Optional
import pandas as pd
import openpyxl
from datetime import datetime
from .header_detector import HeaderDetector
from .column_mapper import ColumnMapper
from .data_extractor import DataExtractor
from .openai_enhancer import OpenAIEnhancer

logger = logging.getLogger(__name__)


class ExcelParser:
    """Main parser for production planning Excel files"""
    
    def __init__(self, enable_ai: bool = True):
        self.header_detector = HeaderDetector()
        self.column_mapper = ColumnMapper()
        self.data_extractor = DataExtractor()
        self.ai_enhancer = OpenAIEnhancer() if enable_ai else None
    
    def parse_file(self, file_path: str, filename: str = None) -> Dict[str, Any]:
        """
        Parse an Excel file and extract production items
        
        Args:
            file_path: Path to the Excel file
            filename: Original filename (for metadata)
            
        Returns:
            Dictionary with parsed items and metadata
        """
        logger.info(f"Starting to parse file: {file_path}")
        
        try:
            # Load the Excel file
            wb = openpyxl.load_workbook(file_path, data_only=True)
            ws = wb.active
            
            # Read into pandas for easier manipulation
            df = pd.read_excel(file_path, sheet_name=0, header=None)
            
            logger.info(f"Loaded sheet with {len(df)} rows and {len(df.columns)} columns")
            
            # Step 1: Detect milestone headers from first row
            first_row = df.iloc[0].values.tolist() if len(df) > 0 else []
            milestone_headers = self.header_detector.find_milestone_headers(first_row)
            logger.info(f"Detected {len(milestone_headers)} milestone sections: {list(milestone_headers.values())}")
            
            # Step 2: Detect the header row (column names)
            header_row_idx, headers = self.header_detector.detect_header_row(df)
            
            if header_row_idx is None:
                raise ValueError("Could not detect header row in Excel file")
            
            logger.info(f"Header row found at index {header_row_idx}")
            
            # Step 3: Map columns to standard field names
            field_map = self.column_mapper.map_columns(headers, milestone_headers)
            logger.info(f"Mapped {len(field_map)} fields")
            
            # Step 4: Extract data rows
            items = self.data_extractor.extract_rows(df, header_row_idx, field_map)
            
            # Step 5: Apply AI enhancements (if available)
            if self.ai_enhancer and self.ai_enhancer.enabled:
                try:
                    # Validate data with GPT
                    items = self.ai_enhancer.validate_data(items)
                    logger.info("AI validation applied")
                except Exception as e:
                    logger.warning(f"AI validation skipped: {e}")
            
            # Add metadata to each item
            for item in items:
                item['source_file'] = filename or file_path
                item['uploaded_at'] = datetime.utcnow()
                item['status'] = self._derive_status(item)
            
            # Generate AI summary (if available)
            summary = None
            if self.ai_enhancer and self.ai_enhancer.enabled:
                try:
                    summary = self.ai_enhancer.generate_summary(items, filename or file_path)
                except Exception as e:
                    logger.warning(f"AI summary skipped: {e}")
            
            result = {
                'success': True,
                'items': items,
                'total_items': len(items),
                'source_file': filename or file_path,
                'parsed_at': datetime.utcnow().isoformat(),
                'ai_summary': summary
            }
            
            logger.info(f"Successfully parsed {len(items)} items from {file_path}")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'items': [],
                'total_items': 0,
                'source_file': filename or file_path,
                'parsed_at': datetime.utcnow().isoformat()
            }
    
    def parse_bytes(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Parse Excel file from bytes (for uploaded files)
        
        Args:
            file_bytes: File content as bytes
            filename: Original filename
            
        Returns:
            Dictionary with parsed items and metadata
        """
        import tempfile
        import os
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            tmp_file.write(file_bytes)
            tmp_path = tmp_file.name
        
        try:
            result = self.parse_file(tmp_path, filename)
            return result
        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_path)
            except:
                pass
    
    @staticmethod
    def _derive_status(item: Dict[str, Any]) -> str:
        """
        Derive production status from milestone data
        
        Args:
            item: Production item dict
            
        Returns:
            Status string
        """
        milestones = item.get('milestones', {})
        
        if not milestones:
            return 'pending'
        
        # Count completed milestones (those with plan dates)
        completed_count = 0
        total_count = len(milestones)
        
        for milestone_data in milestones.values():
            if 'plan_date' in milestone_data or 'plan' in milestone_data:
                completed_count += 1
        
        # Determine status based on completion
        if completed_count == 0:
            return 'pending'
        elif completed_count < total_count:
            return 'in_production'
        else:
            return 'completed'
