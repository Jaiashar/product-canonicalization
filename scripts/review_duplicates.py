# scripts/review_duplicates.py
#!/usr/bin/env python3
"""
Script to review and manage duplicate products
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.duplicate_reviewer import DuplicateReviewer
from config.settings import settings
from loguru import logger

def main():
    """Main duplicate review interface"""
    # Configure logging
    logger.add(settings.LOG_FILE, rotation="10 MB", level=settings.LOG_LEVEL)
    
    reviewer = DuplicateReviewer()
    
    print("🔍 Duplicate Review Tool")
    print("="*50)
    
    while True:
        try:
            choice = input("\nWhat would you like to do?\n"
                          "1. 🔄 Interactive review\n"
                          "2. 📄 Export duplicates to JSON\n"
                          "3. 📊 Get statistics\n"
                          "4. 📋 Get duplicate summary\n"
                          "5. 👋 Quit\n"
                          "Enter choice (1-5): ").strip()
            
            if choice == '1':
                reviewer.interactive_review()
            elif choice == '2':
                filename = input("Enter filename (default: duplicates_review.json): ").strip()
                if not filename:
                    filename = 'duplicates_review.json'
                reviewer.export_duplicates_for_review(filename)
            elif choice == '3':
                stats = reviewer.get_statistics()
                print("\n📊 Statistics:")
                print(f"  Total products: {stats.get('total_products', 'N/A')}")
                print(f"  Products with embeddings: {stats.get('products_with_embeddings', 'N/A')}")
                print(f"  Products with duplicates: {stats.get('products_with_duplicates', 'N/A')}")
                print(f"  Unchecked duplicates: {stats.get('unchecked_duplicates', 'N/A')}")
                print(f"  Completion rate: {stats.get('completion_rate', 'N/A')}")
            elif choice == '4':
                pending = reviewer.get_pending_duplicates()
                print(f"\n📋 Summary: {len(pending)} products have unchecked potential duplicates")
                if pending:
                    print("First 5 products needing review:")
                    for i, product in enumerate(pending[:5]):
                        print(f"  {i+1}. {product['product_id']} - {product.get('normalized_name', 'N/A')}")
            elif choice == '5':
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice. Please enter 1-5.")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    main()