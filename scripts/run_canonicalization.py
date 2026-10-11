#!/usr/bin/env python3
"""
Main script to run the product canonicalization process
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.canonicalizer import ProductCanonicalizer
from config.settings import settings
from loguru import logger

def main():
    """Run the canonicalization process"""
    # Configure logging
    logger.add(settings.LOG_FILE, rotation="10 MB", level=settings.LOG_LEVEL)
    
    logger.info("🚀 Starting product canonicalization process")
    
    # Initialize canonicalizer
    canonicalizer = ProductCanonicalizer()
    
    # Run the process
    try:
        canonicalizer.run_canonicalization(batch_size=settings.BATCH_SIZE)
        logger.info("✅ Canonicalization process completed")
    except Exception as e:
        logger.error(f"❌ Canonicalization process failed: {e}")
        return False
    
    # Get summary
    summary = canonicalizer.get_processing_summary()
    logger.info(f"📊 Processing Summary: {summary}")
    
    return True

if __name__ == "__main__":
    main()