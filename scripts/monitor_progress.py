#!/usr/bin/env python3
"""
Monitor canonicalization progress
"""
import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.duplicate_reviewer import DuplicateReviewer

def monitor_progress():
    """Monitor progress in real-time"""
    reviewer = DuplicateReviewer()
    
    print("📊 Canonicalization Progress Monitor")
    print("=" * 50)
    
    while True:
        try:
            stats = reviewer.get_statistics()
            print(f"\r🔄 Products: {stats.get('total_products', 0)} | "
                  f"With embeddings: {stats.get('products_with_embeddings', 0)} | "
                  f"Duplicates: {stats.get('products_with_duplicates', 0)} | "
                  f"Completion: {stats.get('completion_rate', '0%')}", end='')
            
            time.sleep(30)  # Update every 30 seconds
            
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    monitor_progress()