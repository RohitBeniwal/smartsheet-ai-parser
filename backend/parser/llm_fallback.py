"""
Optional LLM fallback for ambiguous column mapping
Only used when pattern matching confidence is below threshold
"""
import logging
import os
from typing import Optional, List
import anthropic

logger = logging.getLogger(__name__)


class LLMFallback:
    """Uses LLM to resolve ambiguous column mappings"""
    
    def __init__(self, api_key: str = None):
        """
        Initialize LLM client
        
        Args:
            api_key: Anthropic API key (optional, uses env var if not provided)
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.enabled = bool(self.api_key)
        
        if self.enabled:
            self.client = anthropic.Anthropic(api_key=self.api_key)
            logger.info("LLM fallback enabled")
        else:
            self.client = None
            logger.info("LLM fallback disabled (no API key)")
    
    def identify_column(self, column_name: str, possible_fields: List[str]) -> Optional[dict]:
        """
        Use LLM to identify what a column represents
        
        Args:
            column_name: The actual column header text
            possible_fields: List of possible standard field names
            
        Returns:
            Dict with 'field' and 'confidence', or None if API fails
        """
        if not self.enabled:
            logger.warning("LLM fallback called but not enabled")
            return None
        
        try:
            prompt = f"""You are analyzing a production planning spreadsheet column header.

Column header: "{column_name}"

Possible fields it could represent:
{chr(10).join(f"- {field}" for field in possible_fields)}

Based on the column header text, which field does it most likely represent?
Respond with ONLY the field name from the list above, or "unknown" if truly ambiguous.

Field:"""

            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=50,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Extract response
            response_text = message.content[0].text.strip().lower()
            
            # Parse response
            for field in possible_fields:
                if field.lower() in response_text:
                    logger.info(f"LLM identified '{column_name}' as '{field}'")
                    return {
                        'field': field,
                        'confidence': 0.85,  # LLM suggestions get medium-high confidence
                        'method': 'llm'
                    }
            
            logger.warning(f"LLM could not identify '{column_name}'")
            return None
            
        except Exception as e:
            logger.error(f"LLM fallback error: {e}")
            return None
    
    def batch_identify_columns(self, column_names: List[str], possible_fields: List[str]) -> Dict[str, Optional[dict]]:
        """
        Identify multiple columns in one call (more efficient)
        
        Args:
            column_names: List of column headers to identify
            possible_fields: List of possible standard field names
            
        Returns:
            Dictionary mapping column names to identification results
        """
        if not self.enabled:
            return {name: None for name in column_names}
        
        try:
            prompt = f"""You are analyzing production planning spreadsheet column headers.

Possible standard fields:
{chr(10).join(f"- {field}" for field in possible_fields)}

For each column header below, identify which standard field it represents.
Respond in the format: "column_name -> field_name" (one per line)

Column headers:
{chr(10).join(f'{i+1}. "{name}"' for i, name in enumerate(column_names))}

Mappings:"""

            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=200,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text.strip()
            
            # Parse response
            results = {}
            for line in response_text.split('\n'):
                if '->' in line:
                    parts = line.split('->')
                    if len(parts) == 2:
                        col = parts[0].strip().strip('"').strip("'").strip('1234567890. ')
                        field = parts[1].strip().lower()
                        
                        if field in [f.lower() for f in possible_fields]:
                            results[col] = {
                                'field': field,
                                'confidence': 0.85,
                                'method': 'llm_batch'
                            }
            
            logger.info(f"LLM batch identified {len(results)}/{len(column_names)} columns")
            return results
            
        except Exception as e:
            logger.error(f"LLM batch fallback error: {e}")
            return {name: None for name in column_names}
