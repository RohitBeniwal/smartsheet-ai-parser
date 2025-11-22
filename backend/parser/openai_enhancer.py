"""
OpenAI-powered enhancements for intelligent parsing
Falls back gracefully if OpenAI is unavailable
"""
import logging
import os
from typing import Dict, List, Optional, Any
from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenAIEnhancer:
    """OpenAI-powered intelligent enhancements with graceful fallback"""
    
    def __init__(self, api_key: str = None):
        """
        Initialize OpenAI client
        
        Args:
            api_key: OpenAI API key (uses env var if not provided)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.enabled = bool(self.api_key)
        
        if self.enabled:
            try:
                self.client = OpenAI(api_key=self.api_key)
                logger.info("OpenAI enhancements enabled")
            except Exception as e:
                logger.warning(f"OpenAI initialization failed: {e}. Continuing without AI enhancements.")
                self.enabled = False
                self.client = None
        else:
            self.client = None
            logger.info("OpenAI enhancements disabled (no API key)")
    
    def enhance_column_detection(self, unknown_columns: List[str], possible_fields: List[str]) -> Dict[str, str]:
        """
        Use GPT to identify unknown columns
        Falls back to empty dict if unavailable
        
        Args:
            unknown_columns: List of column names that couldn't be matched
            possible_fields: List of standard field names
            
        Returns:
            Dictionary mapping column names to standard fields
        """
        if not self.enabled or not unknown_columns:
            return {}
        
        try:
            prompt = f"""You are analyzing production planning spreadsheet columns.

Unknown columns: {', '.join(unknown_columns)}

Possible fields: {', '.join(possible_fields)}

For each unknown column, identify which field it represents. Respond in JSON format:
{{"column_name": "field_name"}}

If unclear, omit that column. Response:"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=150
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            import json
            mappings = json.loads(result_text)
            
            logger.info(f"GPT identified {len(mappings)} unknown columns")
            return mappings
            
        except Exception as e:
            logger.warning(f"GPT column detection failed: {e}. Using pattern matching only.")
            return {}
    
    def validate_data(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate data for anomalies using GPT
        Returns items with validation warnings added
        Falls back to no validation if unavailable
        
        Args:
            items: List of parsed production items
            
        Returns:
            Items with validation warnings (if any)
        """
        if not self.enabled or not items:
            return items
        
        try:
            # Sample first 3 items for validation
            sample = items[:3]
            
            prompt = f"""Analyze this production data for anomalies:

{sample}

Check for:
- Unusual quantities (too high/low)
- Invalid fabric types
- Outlier dates
- Inconsistent data

Respond with JSON array of warnings:
[{{"item_index": 0, "field": "quantity", "warning": "Suspiciously high"}}]

If no issues, return: []

Response:"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=200
            )
            
            import json
            warnings = json.loads(response.choices[0].message.content.strip())
            
            # Add warnings to items
            for warning in warnings:
                idx = warning.get('item_index', 0)
                if idx < len(items):
                    if '_validation' not in items[idx]:
                        items[idx]['_validation'] = []
                    items[idx]['_validation'].append({
                        'field': warning.get('field'),
                        'warning': warning.get('warning')
                    })
            
            logger.info(f"GPT validation found {len(warnings)} potential issues")
            return items
            
        except Exception as e:
            logger.warning(f"GPT validation failed: {e}. Skipping validation.")
            return items
    
    def generate_summary(self, items: List[Dict[str, Any]], filename: str) -> Optional[str]:
        """
        Generate intelligent summary of parsed data
        Returns None if unavailable
        
        Args:
            items: List of parsed items
            filename: Source filename
            
        Returns:
            Summary text or None
        """
        if not self.enabled or not items:
            return None
        
        try:
            # Create concise data summary
            summary_data = {
                'total_items': len(items),
                'filename': filename,
                'sample_items': items[:3],
                'statuses': self._get_status_distribution(items),
                'avg_quantity': self._get_avg_quantity(items)
            }
            
            prompt = f"""Generate a brief summary of this production planning data:

{summary_data}

Include:
- Total orders
- Key insights
- Any notable patterns or issues
- Brief overview

Keep it concise (3-4 sentences).

Summary:"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=150
            )
            
            summary = response.choices[0].message.content.strip()
            logger.info("GPT generated summary successfully")
            return summary
            
        except Exception as e:
            logger.warning(f"GPT summary generation failed: {e}")
            return None
    
    @staticmethod
    def _get_status_distribution(items: List[Dict]) -> Dict[str, int]:
        """Get count of items by status"""
        statuses = {}
        for item in items:
            status = item.get('status', 'unknown')
            statuses[status] = statuses.get(status, 0) + 1
        return statuses
    
    @staticmethod
    def _get_avg_quantity(items: List[Dict]) -> float:
        """Calculate average quantity"""
        quantities = [item.get('quantity', 0) for item in items if item.get('quantity')]
        return sum(quantities) / len(quantities) if quantities else 0
