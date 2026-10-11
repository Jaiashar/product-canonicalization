# scripts/setup_tables.py
#!/usr/bin/env python3
"""
Setup script to create the FinalProductsTable
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.aws_client import AWSClient
from config.settings import settings
from loguru import logger

def setup_tables():
    """Create the FinalProductsTable if it doesn't exist"""
    logger.info("Setting up DynamoDB tables...")
    
    aws_client = AWSClient()
    
    # Define the schema for FinalProductsTable
    key_schema = [
        {'AttributeName': 'product_id', 'KeyType': 'HASH'}
    ]
    
    attribute_definitions = [
        {'AttributeName': 'product_id', 'AttributeType': 'S'}
    ]
    
    # Create the table
    success = aws_client.create_table_if_not_exists(
        table_name=settings.FINAL_TABLE_NAME,
        key_schema=key_schema,
        attribute_definitions=attribute_definitions
    )
    
    if success:
        logger.info(f"✅ FinalProductsTable setup complete")
        
        # Test table access
        final_table = aws_client.get_table(settings.FINAL_TABLE_NAME)
        source_table = aws_client.get_table(settings.SOURCE_TABLE_NAME)
        
        logger.info(f"📊 {settings.SOURCE_TABLE_NAME} item count: {source_table.item_count}")
        logger.info(f"📊 {settings.FINAL_TABLE_NAME} item count: {final_table.item_count}")
    else:
        logger.error("❌ Failed to setup tables")
        return False
    
    return True

if __name__ == "__main__":
    # Configure logging
    logger.add(settings.LOG_FILE, rotation="10 MB")
    
    setup_tables()