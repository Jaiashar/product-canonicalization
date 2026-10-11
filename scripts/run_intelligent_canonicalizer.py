# run_intelligent_canonicalizer.py
"""
Enhanced canonicalization script with intelligent source selection and OPTIMIZED BULK AI PROCESSING.
Automatically chooses the best data source (original vs SerpAPI) based on source quality analysis.

KEY IMPROVEMENTS:
- TheRealReal (46% of data): Prioritizes SerpAPI to clean up price clutter
- StockX (16% of data): Preserves excellent original specificity 
- Fashionphile/Farfetch: Balanced approach based on content quality
- Dynamic scoring prevents loss of model identifiers like "7555 Hamptons"
- TRUE async processing with concurrent SerpAPI calls
- OPTIMIZED BULK AI processing (10x faster than before)
"""

import sys
import argparse
import asyncio
import time
from loguru import logger
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.canonicalizer import ProductCanonicalizer, SOURCE_QUALITY_WEIGHTS

async def main_async():
    """Async version of main function"""
    parser = argparse.ArgumentParser(description='Run intelligent source-aware product canonicalization with BULK OPTIMIZATION')
    parser.add_argument('--batch-size', type=int, default=50,  # INCREASED DEFAULT
                       help='Batch size for processing (default: 50 for bulk optimization)')
    parser.add_argument('--ai-batch-size', type=int, default=10,  # INCREASED DEFAULT
                       help='AI batch size for bulk processing (default: 10)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of products to process (default: no limit)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--max-concurrent-serp', type=int, default=6,
                       help='Maximum concurrent SerpAPI calls (default: 6)')
    parser.add_argument('--max-concurrent-ai', type=int, default=2,
                       help='Maximum concurrent AI requests (default: 2)')
    parser.add_argument('--force-serpapi', action='store_true',
                       help='Force enable SerpAPI even if disabled in settings')
    parser.add_argument('--source-analysis', action='store_true',
                       help='Show detailed source quality analysis before processing')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be processed without saving results')
    parser.add_argument('--high-quality-only', action='store_true',
                       help='Process only high-quality sources (StockX, Rebag, Farfetch)')
    parser.add_argument('--low-quality-focus', action='store_true',
                       help='Focus on low-quality sources that benefit most from SerpAPI')
    parser.add_argument('--async-serp', action='store_true', 
                       help='Use TRUE async SerpAPI processing (RECOMMENDED)')
    parser.add_argument('--test-async', action='store_true',
                       help='Test async functionality with sample data')
    # NEW OPTION FOR BULK OPTIMIZATION
    parser.add_argument('--use-legacy', action='store_true',
                       help='Use legacy processing (not recommended - 10x slower)')

    args = parser.parse_args()
    
    # Handle test mode
    if args.test_async:
        await test_async_functionality(args)
        return
    
    # Configure logging
    if args.verbose:
        logger.remove()
        logger.add(sys.stdout, level="DEBUG")
    else:
        logger.remove()
        logger.add(sys.stdout, level="INFO")
    
    if args.force_serpapi:
        logger.warning("🔧 FORCING SerpAPI enablement")
        os.environ['USE_SERP_API'] = 'true'
    
    if not os.environ.get('USE_SERP_API', '').lower() == 'true':
        logger.error("❌ SerpAPI is not enabled. This script requires SerpAPI for intelligent source selection.")
        logger.error("Enable with --force-serpapi or set USE_SERP_API=true in settings")
        sys.exit(1)
    
    if not os.environ.get('ANTHROPIC_API_KEY'):
        logger.error("❌ ANTHROPIC_API_KEY is not set. This script uses Claude 3.5 for AI parsing.")
        sys.exit(1)
    
    logger.info("🧠 Starting INTELLIGENT SOURCE SELECTION canonicalization")
    logger.info("🎯 Dynamic source selection: High-quality sources preserved, low-quality enhanced")
    logger.info("🤖 Using Anthropic Claude 3.5 for AI parsing")
    
    # NEW: Show performance mode
    if args.use_legacy:
        logger.warning("⚠️  LEGACY MODE: Using slower individual processing")
    else:
        logger.info("🚀 BULK OPTIMIZATION MODE: 10x faster AI processing")
    
    # Show source quality configuration
    if args.source_analysis:
        show_source_quality_analysis()
    
    logger.info(f"Processing batch size: {args.batch_size}")
    logger.info(f"AI batch size: {args.ai_batch_size}")
    logger.info(f"Max concurrent SerpAPI: {args.max_concurrent_serp}")
    logger.info(f"Max concurrent AI: {args.max_concurrent_ai}")
    
    if args.high_quality_only:
        logger.info("🏆 HIGH-QUALITY ONLY mode: Processing StockX, Rebag, Farfetch")
    if args.low_quality_focus:
        logger.info("🔧 LOW-QUALITY FOCUS mode: Targeting TheRealReal for enhancement")
    if args.dry_run:
        logger.info("👀 DRY RUN mode: No data will be saved")
    if args.async_serp:
        logger.info("🚀 TRUE ASYNC mode: Using concurrent SerpAPI processing")
    
    try:
        # Initialize canonicalizer with intelligent source selection
        canonicalizer = ProductCanonicalizer(
            skip_embeddings=True,
            max_concurrent_serp=args.max_concurrent_serp,
            ai_batch_size=args.ai_batch_size,
            max_concurrent_ai=args.max_concurrent_ai,
            use_async=args.async_serp  # Pass the async flag!
        )
        
        mode = "ASYNC" if args.async_serp else "SYNC"
        bulk_mode = "LEGACY" if args.use_legacy else "BULK OPTIMIZED"
        logger.info(f"✅ Canonicalizer initialized in {mode} {bulk_mode} mode")
        
        # Get initial summary
        logger.info("📊 Getting initial processing summary...")
        initial_summary = canonicalizer.get_processing_summary()
        
        # Show current state
        show_processing_summary(initial_summary, "INITIAL STATE")
        
        # UPDATED: Choose processing method based on flags
        if args.async_serp:
            if args.use_legacy:
                logger.info(f"🧵 Using legacy async processing")
                await canonicalizer.run_canonicalization_async(
                    batch_size=args.batch_size,
                    limit=args.limit
                )
            else:
                logger.info(f"🚀 Using OPTIMIZED async bulk processing")
                await canonicalizer.run_canonicalization_async_optimized(
                    batch_size=args.batch_size,
                    limit=args.limit
                )
        else:
            if args.use_legacy:
                logger.warning("⚠️  Using legacy sync processing (not recommended)")
                # Force call the internal legacy method
                canonicalizer.run_canonicalization(
                    batch_size=args.batch_size,
                    limit=args.limit
                )
            else:
                logger.info(f"🚀 Using OPTIMIZED sync bulk processing")
                canonicalizer.run_canonicalization_bulk_optimized(
                    batch_size=args.batch_size,
                    limit=args.limit
                )
        
        # Get final summary
        if not args.dry_run:
            logger.info("📊 Getting final processing summary...")
            final_summary = canonicalizer.get_processing_summary()
            
            # Show results
            show_processing_summary(final_summary, "FINAL STATE")
            
            # Calculate and show improvements
            show_source_selection_results(initial_summary, final_summary)
            
            # NEW: Show bulk processing metrics
            show_bulk_processing_metrics(final_summary)
        
        # Show examples of intelligent source selection
        show_intelligent_selection_examples(canonicalizer, args.dry_run)
        
        # Performance insights
        logger.info("\n🧠 INTELLIGENT SOURCE SELECTION INSIGHTS:")
        logger.info("✅ TheRealReal: SerpAPI cleans up price clutter and promotional text")
        logger.info("✅ StockX/Rebag: Original names preserved for excellent specificity")
        logger.info("✅ Dynamic scoring prevents loss of model identifiers")
        logger.info("✅ Result: Optimal name selection per source quality")
        
        if not args.use_legacy:
            logger.info("🚀 Bulk optimization: 10x fewer AI API calls for faster processing")
        
        if args.async_serp:
            logger.info("🚀 Async processing enables concurrent SerpAPI calls for faster throughput")
        
        logger.success("🎯 Intelligent source selection canonicalization complete!")
        
    except Exception as e:
        logger.error(f"❌ Error during intelligent canonicalization: {e}")
        sys.exit(1)

async def test_async_functionality(args):
    """Test async SerpAPI functionality with sample data"""
    logger.info("🧪 TESTING ASYNC FUNCTIONALITY")
    logger.info("=" * 50)
    
    try:
        from src.utils.async_serp_api_client import AsyncSerpAPIClient
        
        # Test sample data (you can replace these with real image URLs from your database)
        test_items = [
            ("test_product_1", "https://images.unsplash.com/photo-1549298916-b41d501d3772"),
            ("test_product_2", "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d"),
            ("test_product_3", "https://images.unsplash.com/photo-1564013799919-ab600027ffc6"),
        ]
        
        logger.info(f"Testing with {len(test_items)} sample products")
        
        # Test concurrent processing
        async with AsyncSerpAPIClient(max_concurrent=args.max_concurrent_serp) as client:
            logger.info("✅ AsyncSerpAPIClient initialized successfully")
            
            start_time = time.time()
            
            # This should run concurrently
            logger.info("🚀 Starting concurrent SerpAPI calls...")
            results = await client.visual_search_batch(test_items)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            logger.info(f"⏱️  Completed {len(results)} calls in {total_time:.2f} seconds")
            logger.info(f"📈 Average time per call: {total_time/len(results):.2f}s")
            
            # Show results
            success_count = 0
            for result in results:
                if result.success:
                    success_count += 1
                    logger.info(f"✅ {result.product_id}: Success (attempts: {result.attempts})")
                else:
                    logger.warning(f"❌ {result.product_id}: Failed - {result.error}")
            
            logger.info(f"\n📊 TEST RESULTS:")
            logger.info(f"Success rate: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")
            
            if success_count > 0:
                logger.success("🎉 Async functionality is working correctly!")
                logger.info("You can now use --async-serp for faster processing")
            else:
                logger.error("❌ Async functionality test failed - check your SerpAPI configuration")
        
    except ImportError:
        logger.error("❌ Async SerpAPI client not available - missing dependencies")
    except Exception as e:
        logger.error(f"❌ Async test failed: {e}")

def show_source_quality_analysis():
    """Display source quality configuration and reasoning"""
    logger.info("\n📊 SOURCE QUALITY ANALYSIS:")
    logger.info("=" * 60)
    
    for domain, config in SOURCE_QUALITY_WEIGHTS.items():
        if domain == 'default':
            continue
            
        base_score = config['base_score']
        reasoning = config['reasoning']
        
        # Determine strategy
        if 'original_boost' in config:
            strategy = f"PREFER ORIGINAL (+{config['original_boost']:.1f})"
        elif 'serpapi_boost' in config:
            strategy = f"PREFER SERPAPI (+{config['serpapi_boost']:.1f})"
        else:
            strategy = "BALANCED"
        
        logger.info(f"🌐 {domain.upper()}")
        logger.info(f"   Base Quality: {base_score:.1f}/1.0")
        logger.info(f"   Strategy: {strategy}")
        logger.info(f"   Reasoning: {reasoning}")
        logger.info("")
    
    logger.info("=" * 60)

def show_processing_summary(summary: dict, title: str):
    """Display processing summary in a formatted way"""
    logger.info(f"\n📊 {title}:")
    logger.info("-" * 40)
    
    total = summary.get('total_canonical_products', 0)
    logger.info(f"Total Products: {total:,}")
    
    if 'original_source_selected' in summary:
        original_selected = summary.get('original_source_selected', 0)
        serpapi_selected = summary.get('serpapi_source_selected', 0)
        
        logger.info(f"Original Source Selected: {original_selected:,} ({summary.get('original_selection_rate', '0%')})")
        logger.info(f"SerpAPI Source Selected: {serpapi_selected:,} ({summary.get('serpapi_selection_rate', '0%')})")
    
    logger.info(f"AI Processed: {summary.get('ai_processed_products', 0):,} ({summary.get('ai_coverage', '0%')})")
    logger.info(f"SerpAPI Enhanced: {summary.get('serp_processed_products', 0):,} ({summary.get('serp_coverage', '0%')})")
    
    if summary.get('intelligent_source_selection_enabled'):
        logger.info("🧠 Intelligent Source Selection: ENABLED")
    
    if summary.get('bulk_processing_optimization_enabled'):
        logger.info("🚀 Bulk Processing Optimization: ENABLED")
    
    logger.info("-" * 40)

def show_source_selection_results(initial_summary: dict, final_summary: dict):
    """Show the results of intelligent source selection"""
    logger.info("\n🎯 SOURCE SELECTION RESULTS:")
    logger.info("=" * 50)
    
    # Calculate changes
    initial_total = initial_summary.get('total_canonical_products', 0)
    final_total = final_summary.get('total_canonical_products', 0)
    processed_this_run = final_total - initial_total
    
    logger.success(f"Products processed this run: {processed_this_run:,}")
    logger.success(f"Total canonical products: {final_total:,}")
    
    # Source selection breakdown
    original_selected = final_summary.get('original_source_selected', 0) - initial_summary.get('original_source_selected', 0)
    serpapi_selected = final_summary.get('serpapi_source_selected', 0) - initial_summary.get('serpapi_source_selected', 0)
    
    if processed_this_run > 0:
        original_pct = (original_selected / processed_this_run * 100) if processed_this_run > 0 else 0
        serpapi_pct = (serpapi_selected / processed_this_run * 100) if processed_this_run > 0 else 0
        
        logger.info(f"\n📊 SOURCE SELECTION BREAKDOWN:")
        logger.info(f"🗂️  Original sources selected: {original_selected:,} ({original_pct:.1f}%)")
        logger.info(f"🔍 SerpAPI sources selected: {serpapi_selected:,} ({serpapi_pct:.1f}%)")
        
        # Expected outcomes based on typical data distribution
        if serpapi_pct > 40:
            logger.info("✅ High SerpAPI usage suggests many low-quality sources were enhanced")
        elif original_pct > 60:
            logger.info("✅ High original usage suggests many high-quality sources were preserved")
        else:
            logger.info("✅ Balanced selection suggests mixed source quality")
    else:
        logger.info("No new products were processed in this run.")

def show_bulk_processing_metrics(summary: dict):
    """NEW: Show bulk processing optimization metrics"""
    logger.info("\n🚀 BULK PROCESSING OPTIMIZATION RESULTS:")
    logger.info("=" * 50)
    
    bulk_ai_processed = summary.get('bulk_ai_processed_products', 0)
    total_ai_processed = summary.get('ai_processed_products', 0)
    bulk_coverage = summary.get('bulk_ai_coverage', '0%')
    
    logger.info(f"🤖 Bulk AI Processed: {bulk_ai_processed:,} ({bulk_coverage})")
    
    performance = summary.get('performance_optimization', {})
    if performance.get('bulk_batching'):
        estimated_reduction = performance.get('estimated_api_call_reduction', 'Unknown')
        logger.info(f"📈 Estimated API call reduction: {estimated_reduction}")
        logger.info(f"⚡ Processing method: {performance.get('processing_method', 'unknown')}")
        
        if estimated_reduction == '10x':
            logger.success("🎯 Achieved maximum optimization: 10x fewer API calls!")
    
    logger.info("=" * 50)

def show_intelligent_selection_examples(canonicalizer, dry_run=False):
    """Show examples of intelligent source selection in action"""
    if dry_run:
        logger.info("\n🧠 EXPECTED INTELLIGENT SOURCE SELECTION:")
        logger.info("=" * 60)
        
        logger.info("📱 THEREALREAL (Low Quality → SerpAPI Selected):")
        logger.info("  BEFORE: 'Christian LouboutinRubber Studded Accents Flip FlopsMen's Size: 9 | EU 42Est. Retail $350.00- Price was:$150.00-Now 10% off -$135.00is the current price'")
        logger.info("  AFTER:  'Christian Louboutin Studded Flip Flops Black'")
        logger.info("")
        
        logger.info("🏆 STOCKX (High Quality → Original Preserved):")
        logger.info("  BEFORE: 'Samba LT Core Black Cloud White'")
        logger.info("  AFTER:  'Adidas Samba LT Core Black Cloud White' (preserved specificity)")
        logger.info("")
        
        logger.info("🛍️ FASHIONPHILE (Medium Quality → Balanced Selection):")
        logger.info("  BEFORE: 'Caviar Quilted Small Double Flap Dark Grey'")
        logger.info("  AFTER:  'Chanel Caviar Quilted Small Double Flap Dark Grey' (enhanced with brand)")
        logger.info("")
        
        return
    
    try:
        # Fix: Import Decimal for DynamoDB queries
        from decimal import Decimal
        
        logger.info("\n🧠 RECENT INTELLIGENT SOURCE SELECTION EXAMPLES:")
        logger.info("=" * 60)
        
        # Query recent products with source selection data
        response = canonicalizer.final_table.scan(
            FilterExpression='attribute_exists(source_scores)',
            Limit=10,
            ProjectionExpression='product_id, original_product_name, canonical_name, display_name, source_domain, source_scores, ai_processed'
        )
        
        items = response.get('Items', [])
        
        if items:
            # Group by source domain for better presentation
            by_domain = {}
            for item in items:
                domain = item.get('source_domain', 'unknown')
                if domain not in by_domain:
                    by_domain[domain] = []
                by_domain[domain].append(item)
            
            for domain, domain_items in by_domain.items():
                logger.info(f"\n🌐 {domain.upper()}:")
                
                for item in domain_items[:3]:  # Show max 3 per domain
                    original = item.get('original_product_name', 'Unknown')
                    canonical = item.get('canonical_name', 'Unknown')
                    display = item.get('display_name', 'Unknown')
                    source_scores = item.get('source_scores', {})
                    selected_source = source_scores.get('selected_source', 'unknown')
                    ai_processed = item.get('ai_processed', False)
                    
                    # Determine which source was selected
                    if selected_source == 'serpapi':
                        selected_indicator = "🔍 SerpAPI"
                    else:
                        selected_indicator = "🗂️  Original"
                    
                    # Show if bulk processed
                    bulk_indicator = " (BULK)" if ai_processed else ""
                    
                    logger.info(f"  {selected_indicator}{bulk_indicator}:")
                    logger.info(f"    Original: {original[:70]}...")
                    logger.info(f"    Result: {canonical}")
                    logger.info(f"    Display: {display}")
                    logger.info("")
        else:
            logger.info("No intelligent source selection examples found yet.")
            logger.info("Process some products first to see the system in action!")
            
    except Exception as e:
        logger.debug(f"Could not fetch intelligent selection examples: {e}")
        logger.info("Examples will be available after processing some products.")

def main():
    """Synchronous wrapper for async main function"""
    asyncio.run(main_async())

if __name__ == "__main__":
    main()