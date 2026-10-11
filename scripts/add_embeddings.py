# add_embeddings.py
"""
Script to add embeddings to products that were processed without embeddings.
Run this after the fast canonicalization is complete.
"""

import sys
import argparse
from loguru import logger
from src.canonicalizer import ProductCanonicalizer

def main():
    parser = argparse.ArgumentParser(description='Add embeddings to existing canonical products')
    parser.add_argument('--batch-size', type=int, default=10, 
                       help='Batch size for processing (default: 10)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of products to process (default: no limit)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        logger.remove()
        logger.add(sys.stdout, level="DEBUG")
    else:
        logger.remove()
        logger.add(sys.stdout, level="INFO")
    
    logger.info("Starting embedding generation for existing products")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info(f"Limit: {args.limit if args.limit else 'No limit'}")
    
    try:
        # Initialize canonicalizer with embeddings enabled
        canonicalizer = ProductCanonicalizer(skip_embeddings=False)
        
        # Get initial summary
        logger.info("Getting initial processing summary...")
        initial_summary = canonicalizer.get_processing_summary()
        logger.info(f"Initial state: {initial_summary}")
        
        initial_with_embeddings = initial_summary.get('products_with_embeddings', 0)
        products_without_embeddings = initial_summary.get('products_without_embeddings', 0)
        
        if products_without_embeddings == 0:
            logger.info("No products found without embeddings. All done!")
            return
        
        logger.info(f"Found {products_without_embeddings} products without embeddings")
        
        # Add embeddings to existing products
        canonicalizer.add_embeddings_to_existing_products(
            batch_size=args.batch_size,
            limit=args.limit
        )
        
        # Get final summary
        logger.info("Getting final processing summary...")
        final_summary = canonicalizer.get_processing_summary()
        logger.info(f"Final state: {final_summary}")
        
        # Calculate what was processed
        final_with_embeddings = final_summary.get('products_with_embeddings', 0)
        embeddings_added = final_with_embeddings - initial_with_embeddings
        
        logger.success(f"Embedding generation complete!")
        logger.success(f"Embeddings added this run: {embeddings_added}")
        logger.success(f"Total products with embeddings: {final_with_embeddings}")
        logger.success(f"Embedding coverage: {final_summary.get('embedding_coverage', '0%')}")
        
    except Exception as e:
        logger.error(f"Error during embedding generation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()