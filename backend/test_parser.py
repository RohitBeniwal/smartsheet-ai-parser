"""
Test script for the Excel parser
"""
import sys
import logging
from parser import ExcelParser

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_parse_file(file_path):
    """Test parsing a single file"""
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing: {file_path}")
    logger.info(f"{'='*60}")
    
    parser = ExcelParser()
    result = parser.parse_file(file_path)
    
    if result['success']:
        logger.info(f"✓ Successfully parsed {result['total_items']} items")
        
        # Show sample items
        for i, item in enumerate(result['items'][:3], 1):
            logger.info(f"\nItem {i}:")
            logger.info(f"  Order: {item.get('order_number', 'N/A')}")
            logger.info(f"  Style: {item.get('style', 'N/A')}")
            logger.info(f"  Fabric: {item.get('fabric', 'N/A')}")
            logger.info(f"  Color: {item.get('color', 'N/A')}")
            logger.info(f"  Quantity: {item.get('quantity', 'N/A')}")
            logger.info(f"  Status: {item.get('status', 'N/A')}")
            
            milestones = item.get('milestones', {})
            if milestones:
                logger.info(f"  Milestones: {list(milestones.keys())}")
        
        return True
    else:
        logger.error(f"✗ Failed to parse: {result.get('error', 'Unknown error')}")
        return False

def main():
    """Test all sample files"""
    test_files = [
        '../data/tna-uno.xlsx',
        '../data/tna-dos.xlsx',
        '../data/tna-tres.xlsx'
    ]
    
    results = []
    for file_path in test_files:
        success = test_parse_file(file_path)
        results.append((file_path, success))
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")
    
    for file_path, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        logger.info(f"{status} - {file_path}")
    
    all_passed = all(success for _, success in results)
    if all_passed:
        logger.info("\n✓ All tests passed!")
        sys.exit(0)
    else:
        logger.error("\n✗ Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
