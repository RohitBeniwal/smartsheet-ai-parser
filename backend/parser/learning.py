"""
Self-learning system for the parser
Learns from user feedback and stores patterns in MongoDB
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ParserLearning:
    """Manages learning and storing new patterns"""
    
    def __init__(self, db):
        """
        Initialize learning system
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.collection = db.learned_patterns
    
    async def learn_pattern(self, column_name: str, standard_field: str, source_file: str = None) -> bool:
        """
        Learn a new pattern from user feedback
        
        Args:
            column_name: The actual column name found in Excel
            standard_field: The standard field it maps to
            source_file: Optional source file name for tracking
            
        Returns:
            True if pattern was learned (new), False if already known
        """
        column_lower = column_name.strip().lower()
        
        # Check if pattern already exists
        existing = await self.collection.find_one({
            'column_name': column_lower,
            'standard_field': standard_field
        })
        
        if existing:
            # Increment usage count
            await self.collection.update_one(
                {'_id': existing['_id']},
                {
                    '$inc': {'usage_count': 1},
                    '$set': {'last_seen': datetime.utcnow()}
                }
            )
            logger.info(f"Pattern already known: '{column_name}' → {standard_field}")
            return False
        
        # Learn new pattern
        pattern_doc = {
            'column_name': column_lower,
            'standard_field': standard_field,
            'learned_at': datetime.utcnow(),
            'last_seen': datetime.utcnow(),
            'usage_count': 1,
            'source_file': source_file,
            'confidence': 1.0  # User-confirmed patterns have high confidence
        }
        
        await self.collection.insert_one(pattern_doc)
        logger.info(f"Learned new pattern: '{column_name}' → {standard_field}")
        return True
    
    async def get_learned_patterns(self, standard_field: str = None) -> List[str]:
        """
        Get learned patterns for a field
        
        Args:
            standard_field: Optional field to filter by
            
        Returns:
            List of learned column names
        """
        query = {}
        if standard_field:
            query['standard_field'] = standard_field
        
        cursor = self.collection.find(query).sort('usage_count', -1)
        patterns = await cursor.to_list(length=None)
        
        return [p['column_name'] for p in patterns]
    
    async def get_all_learned_patterns(self) -> Dict[str, List[str]]:
        """
        Get all learned patterns grouped by standard field
        
        Returns:
            Dictionary mapping standard fields to lists of learned patterns
        """
        patterns = await self.collection.find().to_list(length=None)
        
        grouped = {}
        for pattern in patterns:
            field = pattern['standard_field']
            if field not in grouped:
                grouped[field] = []
            grouped[field].append(pattern['column_name'])
        
        return grouped
    
    async def merge_with_config(self, config_patterns: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        Merge learned patterns with config patterns
        
        Args:
            config_patterns: Patterns from config.py
            
        Returns:
            Combined patterns dictionary
        """
        learned = await self.get_all_learned_patterns()
        
        merged = {}
        for field_name, patterns in config_patterns.items():
            merged[field_name] = list(patterns)  # Copy original
            
            # Add learned patterns
            if field_name in learned:
                for learned_pattern in learned[field_name]:
                    if learned_pattern not in merged[field_name]:
                        merged[field_name].append(learned_pattern)
                        logger.debug(f"Added learned pattern: {learned_pattern} → {field_name}")
        
        return merged
    
    async def get_pattern_statistics(self) -> Dict[str, any]:
        """
        Get statistics about learned patterns
        
        Returns:
            Dictionary with statistics
        """
        total_patterns = await self.collection.count_documents({})
        
        pipeline = [
            {
                '$group': {
                    '_id': '$standard_field',
                    'count': {'$sum': 1},
                    'total_usage': {'$sum': '$usage_count'}
                }
            }
        ]
        
        by_field = await self.collection.aggregate(pipeline).to_list(length=None)
        
        return {
            'total_learned_patterns': total_patterns,
            'by_field': by_field,
            'last_updated': datetime.utcnow().isoformat()
        }
