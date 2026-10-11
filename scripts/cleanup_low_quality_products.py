# interactive_quality_cleanup.py
"""
Interactive script to analyze and delete low quality products.
Easy-to-use menu interface with detailed analysis and safe deletion options.
"""

import boto3
import time
from typing import List, Dict, Any
from decimal import Decimal
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings

class InteractiveQualityCleanup:
    def __init__(self):
        self.dynamodb_client = boto3.client('dynamodb', region_name='us-east-1')
        self.table_name = settings.FINAL_TABLE_NAME
        
        self.stats = {
            'total_scanned': 0,
            'pages_processed': 0,
            'high_quality': 0,
            'medium_quality': 0,
            'low_quality': 0,
            'very_low_quality': 0
        }
        
        # Quality thresholds
        self.thresholds = {
            'ai_very_low': 0.3,
            'ai_low': 0.5,
            'ai_medium': 0.7,
            'serp_very_low': 0.2,
            'serp_low': 0.4,
            'serp_medium': 0.6
        }
    
    def force_complete_quality_scan(self) -> Dict[str, List[Dict[str, Any]]]:
        """Force complete scan and categorize products by quality."""
        print("🔍 Analyzing ALL products for quality...")
        
        categories = {
            'very_low': [],
            'low': [],
            'medium': [],
            'high': []
        }
        
        try:
            scan_kwargs = {
                'TableName': self.table_name
            }
            
            while True:
                response = self.dynamodb_client.scan(**scan_kwargs)
                
                # Process this page's items
                items = response.get('Items', [])
                scanned_count = response.get('ScannedCount', 0)
                
                self.stats['pages_processed'] += 1
                self.stats['total_scanned'] += scanned_count
                
                # Categorize items
                for item in items:
                    python_item = self._convert_dynamodb_to_python(item)
                    category = self._categorize_product_quality(python_item)
                    categories[category].append(python_item)
                    self.stats[f'{category}_quality'] += 1
                
                print(f"📄 Page {self.stats['pages_processed']}: "
                      f"{scanned_count:,} scanned "
                      f"(total: {self.stats['total_scanned']:,})")
                
                # Check if there are more pages
                last_evaluated_key = response.get('LastEvaluatedKey')
                if not last_evaluated_key:
                    break
                
                # Set up for next page
                scan_kwargs['ExclusiveStartKey'] = last_evaluated_key
                
                # Small delay to avoid throttling
                time.sleep(0.1)
            
            print(f"✅ Quality analysis complete:")
            print(f"   Total products scanned: {self.stats['total_scanned']:,}")
            print(f"   High quality: {len(categories['high']):,}")
            print(f"   Medium quality: {len(categories['medium']):,}")
            print(f"   Low quality: {len(categories['low']):,}")
            print(f"   Very low quality: {len(categories['very_low']):,}")
            
            return categories
            
        except Exception as e:
            print(f"❌ Error in quality scan: {e}")
            return {}
    
    def _categorize_product_quality(self, product: Dict[str, Any]) -> str:
        """Categorize product quality based on multiple factors."""
        canonical_name = product.get('canonical_name', '')
        
        # Convert confidence scores safely
        try:
            ai_confidence = float(product.get('ai_confidence', 0))
            serp_confidence = float(product.get('serp_confidence', 0))
        except (ValueError, TypeError):
            ai_confidence = 0.0
            serp_confidence = 0.0
        
        # Check for obvious bad indicators
        bad_keywords = ['SOLD', 'Price', 'price', 'Size', 'size', 'See Similar', 'Add to Cart']
        has_bad_keywords = any(keyword in canonical_name for keyword in bad_keywords)
        
        # Very low quality criteria
        if (has_bad_keywords or 
            len(canonical_name.strip()) < 5 or
            ai_confidence < self.thresholds['ai_very_low'] or
            serp_confidence < self.thresholds['serp_very_low']):
            return 'very_low'
        
        # Low quality criteria
        if (ai_confidence < self.thresholds['ai_low'] or
            serp_confidence < self.thresholds['serp_low']):
            return 'low'
        
        # High quality criteria
        if (ai_confidence >= self.thresholds['ai_medium'] and
            serp_confidence >= self.thresholds['serp_medium']):
            return 'high'
        
        # Everything else is medium
        return 'medium'
    
    def _convert_dynamodb_to_python(self, dynamodb_item: Dict) -> Dict[str, Any]:
        """Convert DynamoDB item format to Python dict."""
        python_item = {}
        
        for key, value in dynamodb_item.items():
            if 'S' in value:  # String
                python_item[key] = value['S']
            elif 'N' in value:  # Number
                python_item[key] = float(value['N'])
            elif 'L' in value:  # List
                python_item[key] = [self._convert_dynamodb_value(item) for item in value['L']]
            elif 'M' in value:  # Map
                python_item[key] = {k: self._convert_dynamodb_value(v) for k, v in value['M'].items()}
            elif 'BOOL' in value:  # Boolean
                python_item[key] = value['BOOL']
            elif 'NULL' in value:  # Null
                python_item[key] = None
            else:
                python_item[key] = str(value)  # Fallback
        
        return python_item
    
    def _convert_dynamodb_value(self, dynamodb_value: Dict) -> Any:
        """Convert a single DynamoDB value to Python value."""
        if 'S' in dynamodb_value:
            return dynamodb_value['S']
        elif 'N' in dynamodb_value:
            return float(dynamodb_value['N'])
        elif 'L' in dynamodb_value:
            return [self._convert_dynamodb_value(item) for item in dynamodb_value['L']]
        elif 'M' in dynamodb_value:
            return {k: self._convert_dynamodb_value(v) for k, v in dynamodb_value['M'].items()}
        elif 'BOOL' in dynamodb_value:
            return dynamodb_value['BOOL']
        elif 'NULL' in dynamodb_value:
            return None
        else:
            return str(dynamodb_value)
    
    def _show_quality_breakdown(self, categories: Dict[str, List[Dict[str, Any]]]) -> None:
        """Show detailed breakdown of quality categories."""
        print(f"\n📊 QUALITY BREAKDOWN:")
        print("=" * 60)
        
        for category, products in categories.items():
            if not products:
                continue
                
            print(f"\n🏷️  {category.upper().replace('_', ' ')} QUALITY: {len(products):,} products")
            
            # Show brand breakdown
            brand_breakdown = {}
            for product in products:
                brand = product.get('brand', 'Unknown')
                brand_breakdown[brand] = brand_breakdown.get(brand, 0) + 1
            
            print(f"   Top brands:")
            for brand, count in sorted(brand_breakdown.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"     {brand}: {count:,}")
            
            # Show sample products
            print(f"   Sample products:")
            for i, product in enumerate(products[:3]):
                canonical = product.get('canonical_name', 'Unknown')[:50]
                ai_conf = product.get('ai_confidence', 0)
                serp_conf = product.get('serp_confidence', 0)
                print(f"     {i+1}. {canonical}... (AI: {ai_conf:.2f}, Serp: {serp_conf:.2f})")
    
    def _show_deletion_preview(self, products: List[Dict[str, Any]], title: str) -> None:
        """Show what would be deleted."""
        print(f"\n📋 {title}: {len(products):,} products")
        print("=" * 60)
        
        # Brand breakdown
        brand_breakdown = {}
        for product in products:
            brand = product.get('brand', 'Unknown')
            brand_breakdown[brand] = brand_breakdown.get(brand, 0) + 1
        
        print(f"📊 By brand:")
        for brand, count in sorted(brand_breakdown.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"   {brand}: {count:,} products")
        
        # Quality reasons
        print(f"\n📋 Sample products to delete:")
        for i, product in enumerate(products[:10]):
            canonical = product.get('canonical_name', 'Unknown')[:40]
            ai_conf = product.get('ai_confidence', 0)
            serp_conf = product.get('serp_confidence', 0)
            
            # Identify reasons for deletion
            reasons = []
            if 'SOLD' in canonical:
                reasons.append('Contains SOLD')
            if any(word in canonical for word in ['Price', 'price', 'Size', 'size']):
                reasons.append('Contains price/size')
            if ai_conf < 0.3:
                reasons.append(f'Very low AI ({ai_conf:.2f})')
            if serp_conf < 0.2:
                reasons.append(f'Very low Serp ({serp_conf:.2f})')
            
            print(f"   {i+1}. {canonical}...")
            print(f"      AI: {ai_conf:.2f}, Serp: {serp_conf:.2f}")
            print(f"      Reasons: {', '.join(reasons) if reasons else 'Low quality'}")
        
        if len(products) > 10:
            print(f"   ... and {len(products) - 10:,} more")
    
    def delete_products_forced(self, products: List[Dict[str, Any]], dry_run: bool = True) -> None:
        """Delete products using batch operations."""
        
        if dry_run:
            print(f"🧪 DRY RUN: Would delete {len(products):,} products")
            return
        
        print(f"🗑️  Deleting {len(products):,} products...")
        
        deleted_count = 0
        failed_count = 0
        batch_size = 25
        total_batches = (len(products) + batch_size - 1) // batch_size
        
        start_time = time.time()
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(products))
            batch = products[start_idx:end_idx]
            
            # Progress update
            if batch_num % 50 == 0 or batch_num == total_batches - 1:
                elapsed = time.time() - start_time
                rate = deleted_count / max(elapsed, 1)
                eta = (len(products) - deleted_count) / max(rate, 1)
                print(f"📦 Batch {batch_num + 1:,}/{total_batches:,} | "
                      f"Deleted: {deleted_count:,}/{len(products):,} | "
                      f"Rate: {rate:.1f}/s | ETA: {eta:.0f}s")
            
            try:
                # Prepare delete requests
                delete_requests = []
                for product in batch:
                    delete_requests.append({
                        'DeleteRequest': {
                            'Key': {
                                'product_id': {'S': product['product_id']}
                            }
                        }
                    })
                
                # Execute batch delete
                if delete_requests:
                    response = self.dynamodb_client.batch_write_item(
                        RequestItems={
                            self.table_name: delete_requests
                        }
                    )
                    
                    # Handle unprocessed items
                    unprocessed = response.get('UnprocessedItems', {})
                    if unprocessed:
                        failed_count += len(unprocessed.get(self.table_name, []))
                    
                    successful = len(delete_requests) - len(unprocessed.get(self.table_name, []))
                    deleted_count += successful
                
                # Throttling protection
                time.sleep(0.05)
                
            except Exception as e:
                print(f"❌ Error in batch {batch_num + 1}: {e}")
                failed_count += len(batch)
                continue
        
        total_time = time.time() - start_time
        print(f"\n🎯 Deletion complete!")
        print(f"⏱️  Total time: {total_time:.1f}s")
        print(f"✅ Deleted: {deleted_count:,}")
        print(f"❌ Failed: {failed_count:,}")
        print(f"📈 Rate: {deleted_count / max(total_time, 1):.1f} deletions/second")
    
    def run_interactive_cleanup(self):
        """Run interactive cleanup with menu options."""
        print("🧹 Interactive Quality Cleanup")
        print("=" * 60)
        
        start_time = time.time()
        
        # Step 1: Analyze all products
        print("1️⃣  Analyzing product quality...")
        categories = self.force_complete_quality_scan()
        
        if not categories:
            print("❌ Failed to analyze products")
            return
        
        # Step 2: Show summary
        analysis_time = time.time() - start_time
        print(f"\n📊 QUALITY ANALYSIS COMPLETE ({analysis_time:.1f}s)")
        print(f"   Total products: {self.stats['total_scanned']:,}")
        print(f"   High quality: {len(categories['high']):,} ({len(categories['high'])/self.stats['total_scanned']*100:.1f}%)")
        print(f"   Medium quality: {len(categories['medium']):,} ({len(categories['medium'])/self.stats['total_scanned']*100:.1f}%)")
        print(f"   Low quality: {len(categories['low']):,} ({len(categories['low'])/self.stats['total_scanned']*100:.1f}%)")
        print(f"   Very low quality: {len(categories['very_low']):,} ({len(categories['very_low'])/self.stats['total_scanned']*100:.1f}%)")
        
        # Step 3: Interactive menu
        while True:
            print(f"\n🛠️  CLEANUP OPTIONS:")
            print(f"1. Show detailed quality breakdown")
            print(f"2. Preview very low quality products ({len(categories['very_low']):,} products)")
            print(f"3. Preview low quality products ({len(categories['low']):,} products)")
            print(f"4. Delete very low quality products (DRY RUN)")
            print(f"5. Delete very low quality products (REAL)")
            print(f"6. Delete low + very low quality products (DRY RUN)")
            print(f"7. Delete low + very low quality products (REAL)")
            print(f"8. Custom deletion (choose your own criteria)")
            print(f"9. Exit")
            
            choice = input("Choose action (1-9): ").strip()
            
            if choice == "1":
                self._show_quality_breakdown(categories)
            
            elif choice == "2":
                self._show_deletion_preview(categories['very_low'], "VERY LOW QUALITY PRODUCTS")
            
            elif choice == "3":
                self._show_deletion_preview(categories['low'], "LOW QUALITY PRODUCTS")
            
            elif choice == "4":
                self.delete_products_forced(categories['very_low'], dry_run=True)
            
            elif choice == "5":
                print(f"\n⚠️  WARNING: This will delete {len(categories['very_low']):,} very low quality products!")
                confirm = input("Type 'DELETE VERY LOW' to confirm: ")
                if confirm == 'DELETE VERY LOW':
                    self.delete_products_forced(categories['very_low'], dry_run=False)
                else:
                    print("❌ Cancelled")
            
            elif choice == "6":
                combined = categories['very_low'] + categories['low']
                self.delete_products_forced(combined, dry_run=True)
            
            elif choice == "7":
                combined = categories['very_low'] + categories['low']
                print(f"\n⚠️  WARNING: This will delete {len(combined):,} low quality products!")
                confirm = input("Type 'DELETE LOW QUALITY' to confirm: ")
                if confirm == 'DELETE LOW QUALITY':
                    self.delete_products_forced(combined, dry_run=False)
                else:
                    print("❌ Cancelled")
            
            elif choice == "8":
                self._custom_deletion_menu(categories)
            
            elif choice == "9":
                print("👋 Exiting cleanup")
                break
            
            else:
                print("❌ Invalid choice. Please choose 1-9.")
    
    def _custom_deletion_menu(self, categories: Dict[str, List[Dict[str, Any]]]) -> None:
        """Custom deletion menu with user-defined criteria."""
        # Combine low quality products for analysis
        all_low_quality = categories['very_low'] + categories['low']
        
        # Calculate counts for each criteria
        sold_count = sum(1 for p in all_low_quality if 'SOLD' in p.get('canonical_name', ''))
        low_ai_count = sum(1 for p in all_low_quality if p.get('ai_confidence', 0) < 0.3)
        low_serp_count = sum(1 for p in all_low_quality if p.get('serp_confidence', 0) < 0.2)
        both_low_count = sum(1 for p in all_low_quality 
                           if p.get('ai_confidence', 0) < 0.3 and p.get('serp_confidence', 0) < 0.2)
        
        print(f"\n🎯 CUSTOM DELETION CRITERIA:")
        print(f"Choose products to delete by criteria:")
        print(f"1. Products with 'SOLD' in name ({sold_count:,} products)")
        print(f"2. Products with AI confidence < 0.3 ({low_ai_count:,} products)")
        print(f"3. Products with SerpAPI confidence < 0.2 ({low_serp_count:,} products)")
        print(f"4. Products with both low AI and SerpAPI confidence ({both_low_count:,} products)")
        print(f"5. Back to main menu")
        
        choice = input("Choose criteria (1-5): ").strip()
        
        if choice == "1":
            products_to_delete = [p for p in all_low_quality if 'SOLD' in p.get('canonical_name', '')]
        elif choice == "2":
            products_to_delete = [p for p in all_low_quality if p.get('ai_confidence', 0) < 0.3]
        elif choice == "3":
            products_to_delete = [p for p in all_low_quality if p.get('serp_confidence', 0) < 0.2]
        elif choice == "4":
            products_to_delete = [p for p in all_low_quality 
                                if p.get('ai_confidence', 0) < 0.3 and p.get('serp_confidence', 0) < 0.2]
        elif choice == "5":
            return
        else:
            print("❌ Invalid choice")
            return
        
        if products_to_delete:
            self._show_deletion_preview(products_to_delete, "CUSTOM DELETION PREVIEW")
            
            delete_choice = input(f"\nDelete these {len(products_to_delete):,} products? (y/N): ").strip().lower()
            if delete_choice == 'y':
                confirm = input("Type 'DELETE CUSTOM' to confirm: ")
                if confirm == 'DELETE CUSTOM':
                    self.delete_products_forced(products_to_delete, dry_run=False)
                else:
                    print("❌ Cancelled")
        else:
            print("❌ No products match this criteria")

def main():
    cleanup = InteractiveQualityCleanup()
    cleanup.run_interactive_cleanup()

if __name__ == "__main__":
    main()