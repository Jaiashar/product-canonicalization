# src/duplicate_reviewer.py
import json
from typing import Dict, List, Optional
from botocore.exceptions import ClientError
from loguru import logger
from datetime import datetime

from config.settings import settings
from src.utils.aws_client import AWSClient

class DuplicateReviewer:
    def __init__(self):
        """Initialize the duplicate reviewer"""
        self.aws_client = AWSClient()
        self.final_table = self.aws_client.get_table(settings.FINAL_TABLE_NAME)
        logger.info("DuplicateReviewer initialized")

    def get_pending_duplicates(self) -> List[Dict]:
        """Get all products that need duplicate review"""
        try:
            response = self.final_table.scan(
                FilterExpression='attribute_exists(potential_duplicates) AND size(potential_duplicates) > :zero AND duplicate_checked = :false',
                ExpressionAttributeValues={
                    ':zero': 0,
                    ':false': False
                }
            )
            
            return response.get('Items', [])
            
        except Exception as e:
            logger.error(f"Error getting pending duplicates: {e}")
            return []

    def get_product_by_id(self, product_id: str) -> Optional[Dict]:
        """Get a product by its ID"""
        try:
            response = self.final_table.get_item(Key={'product_id': product_id})
            return response.get('Item')
        except Exception as e:
            logger.error(f"Error getting product {product_id}: {e}")
            return None

    def display_duplicate_pair(self, product1: Dict, product2: Dict):
        """Display two products for comparison"""
        print("\n" + "="*80)
        print("POTENTIAL DUPLICATE PAIR")
        print("="*80)
        
        def format_product_info(product, label):
            print(f"\n{label}: {product['product_id']}")
            print(f"  Original Name: {product.get('original_product_name', 'N/A')}")
            print(f"  Normalized: {product.get('normalized_name', 'N/A')}")
            print(f"  Brand: {product.get('brand', 'N/A')}")
            print(f"  Model: {product.get('model', 'N/A')}")
            print(f"  Category: {product.get('category', 'N/A')}")
            print(f"  Colorway: {product.get('colorway', 'N/A')}")
            print(f"  Collaboration: {product.get('collaboration', 'N/A')}")
            print(f"  Source Sites: {', '.join(product.get('source_sites', []))}")
            print(f"  Main Image: {product.get('main_image_url', 'N/A')}")
            print(f"  Total Images: {len(product.get('all_image_urls', []))}")
        
        format_product_info(product1, "PRODUCT 1")
        format_product_info(product2, "PRODUCT 2")
        
        print("\n" + "-"*80)

    def merge_products(self, keep_product_id: str, remove_product_id: str) -> bool:
        """Merge two duplicate products - keep one, remove the other"""
        try:
            keep_item = self.get_product_by_id(keep_product_id)
            remove_item = self.get_product_by_id(remove_product_id)
            
            if not keep_item or not remove_item:
                logger.error("One or both products not found")
                return False
            
            # Merge attributes
            merged_attributes = keep_item.copy()
            
            # Combine source sites
            keep_sites = set(keep_item.get('source_sites', []))
            remove_sites = set(remove_item.get('source_sites', []))
            merged_attributes['source_sites'] = list(keep_sites.union(remove_sites))
            
            # Choose best images (product with more images)
            keep_images = keep_item.get('all_image_urls', [])
            remove_images = remove_item.get('all_image_urls', [])
            
            if len(remove_images) > len(keep_images):
                merged_attributes['all_image_urls'] = remove_images
                merged_attributes['main_image_url'] = remove_item.get('main_image_url')
                # Keep the embedding from the product with better images
                if remove_item.get('clip_embedding'):
                    merged_attributes['clip_embedding'] = remove_item['clip_embedding']
            
            # Remove from potential duplicates list
            merged_attributes['potential_duplicates'] = [
                dup for dup in merged_attributes.get('potential_duplicates', [])
                if dup != remove_product_id
            ]
            
            # Check if any duplicates left
            merged_attributes['duplicate_checked'] = len(merged_attributes['potential_duplicates']) == 0
            merged_attributes['updated_at'] = datetime.utcnow().isoformat()
            
            # Update the kept product
            self.final_table.put_item(Item=merged_attributes)
            
            # Remove the duplicate from other products' potential_duplicates lists
            self._remove_from_all_duplicate_lists(remove_product_id)
            
            # Delete the removed product
            self.final_table.delete_item(Key={'product_id': remove_product_id})
            
            logger.info(f"Successfully merged {remove_product_id} into {keep_product_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error merging products: {e}")
            return False

    def mark_as_not_duplicate(self, product_id: str, other_product_id: str) -> bool:
        """Mark two products as not duplicates"""
        try:
            # Remove from each other's potential duplicates list
            for pid in [product_id, other_product_id]:
                other_pid = other_product_id if pid == product_id else product_id
                
                item = self.get_product_by_id(pid)
                if item:
                    potential_duplicates = item.get('potential_duplicates', [])
                    if other_pid in potential_duplicates:
                        potential_duplicates.remove(other_pid)
                    
                    # If no more potential duplicates, mark as checked
                    duplicate_checked = len(potential_duplicates) == 0
                    
                    self.final_table.update_item(
                        Key={'product_id': pid},
                        UpdateExpression='SET potential_duplicates = :duplicates, duplicate_checked = :checked, updated_at = :updated_at',
                        ExpressionAttributeValues={
                            ':duplicates': potential_duplicates,
                            ':checked': duplicate_checked,
                            ':updated_at': datetime.utcnow().isoformat()
                        }
                    )
            
            logger.info(f"Marked {product_id} and {other_product_id} as not duplicates")
            return True
            
        except Exception as e:
            logger.error(f"Error marking as not duplicate: {e}")
            return False

    def _remove_from_all_duplicate_lists(self, product_id: str):
        """Remove a product ID from all other products' potential_duplicates lists"""
        try:
            # Scan for products that have this product_id in their potential_duplicates
            response = self.final_table.scan(
                FilterExpression='contains(potential_duplicates, :product_id)',
                ExpressionAttributeValues={':product_id': product_id}
            )
            
            for item in response['Items']:
                potential_duplicates = item.get('potential_duplicates', [])
                if product_id in potential_duplicates:
                    potential_duplicates.remove(product_id)
                    
                    self.final_table.update_item(
                        Key={'product_id': item['product_id']},
                        UpdateExpression='SET potential_duplicates = :duplicates, duplicate_checked = :checked',
                        ExpressionAttributeValues={
                            ':duplicates': potential_duplicates,
                            ':checked': len(potential_duplicates) == 0
                        }
                    )
            
        except Exception as e:
            logger.error(f"Error removing {product_id} from duplicate lists: {e}")

    def interactive_review(self):
        """Interactive duplicate review process"""
        pending_duplicates = self.get_pending_duplicates()
        
        if not pending_duplicates:
            print("🎉 No pending duplicates to review!")
            return
        
        print(f"📋 Found {len(pending_duplicates)} products with potential duplicates")
        
        reviewed_pairs = set()  # Track reviewed pairs to avoid duplicates
        
        for product in pending_duplicates:
            product_id = product['product_id']
            potential_duplicates = product.get('potential_duplicates', [])
            
            for dup_id in potential_duplicates:
                # Skip if we've already reviewed this pair
                pair_key = tuple(sorted([product_id, dup_id]))
                if pair_key in reviewed_pairs:
                    continue
                
                reviewed_pairs.add(pair_key)
                
                # Get the duplicate product
                dup_product = self.get_product_by_id(dup_id)
                if not dup_product:
                    continue
                
                # Display the pair
                self.display_duplicate_pair(product, dup_product)
                
                # Get user decision
                while True:
                    choice = input(f"\n🤔 What would you like to do?\n"
                                 f"1. Merge (keep {product_id}, remove {dup_id})\n"
                                 f"2. Merge (keep {dup_id}, remove {product_id})\n"
                                 f"3. Not duplicates (keep both)\n"
                                 f"4. Skip for now\n"
                                 f"5. Quit\n"
                                 f"Enter choice (1-5): ").strip()
                    
                    if choice == '1':
                        if self.merge_products(product_id, dup_id):
                            print(f"✅ Merged {dup_id} into {product_id}")
                        break
                    elif choice == '2':
                        if self.merge_products(dup_id, product_id):
                            print(f"✅ Merged {product_id} into {dup_id}")
                        break
                    elif choice == '3':
                        if self.mark_as_not_duplicate(product_id, dup_id):
                            print(f"✅ Marked as not duplicates")
                        break
                    elif choice == '4':
                        print("⏭️  Skipped")
                        break
                    elif choice == '5':
                        print("👋 Goodbye!")
                        return
                    else:
                        print("❌ Invalid choice. Please enter 1-5.")

    def export_duplicates_for_review(self, filename: str = 'duplicates_review.json'):
        """Export duplicates to JSON file for external review"""
        try:
            pending_duplicates = self.get_pending_duplicates()
            
            review_data = []
            reviewed_pairs = set()
            
            for product in pending_duplicates:
                product_id = product['product_id']
                potential_duplicates = product.get('potential_duplicates', [])
                
                for dup_id in potential_duplicates:
                    # Skip if we've already added this pair
                    pair_key = tuple(sorted([product_id, dup_id]))
                    if pair_key in reviewed_pairs:
                        continue
                    
                    reviewed_pairs.add(pair_key)
                    
                    # Get the duplicate product
                    dup_product = self.get_product_by_id(dup_id)
                    if dup_product:
                        review_data.append({
                            'product_1': {
                                'product_id': product_id,
                                'original_product_name': product.get('original_product_name', ''),
                                'normalized_name': product.get('normalized_name', ''),
                                'brand': product.get('brand', ''),
                                'model': product.get('model', ''),
                                'main_image_url': product.get('main_image_url', ''),
                                'source_sites': product.get('source_sites', [])
                            },
                            'product_2': {
                                'product_id': dup_id,
                                'original_product_name': dup_product.get('original_product_name', ''),
                                'normalized_name': dup_product.get('normalized_name', ''),
                                'brand': dup_product.get('brand', ''),
                                'model': dup_product.get('model', ''),
                                'main_image_url': dup_product.get('main_image_url', ''),
                                'source_sites': dup_product.get('source_sites', [])
                            }
                        })
            
            with open(filename, 'w') as f:
                json.dump(review_data, f, indent=2)
            
            print(f"✅ Exported {len(review_data)} duplicate pairs to {filename}")
            
        except Exception as e:
            logger.error(f"Error exporting duplicates: {e}")

    def get_statistics(self) -> Dict:
        """Get statistics about the canonicalization process"""
        try:
            # Get total products
            total_response = self.final_table.scan(Select='COUNT')
            total_products = total_response['Count']
            
            # Get products with embeddings
            embeddings_response = self.final_table.scan(
                FilterExpression='attribute_exists(clip_embedding)',
                Select='COUNT'
            )
            products_with_embeddings = embeddings_response['Count']
            
            # Get products with potential duplicates
            duplicates_response = self.final_table.scan(
                FilterExpression='attribute_exists(potential_duplicates) AND size(potential_duplicates) > :zero',
                ExpressionAttributeValues={':zero': 0},
                Select='COUNT'
            )
            products_with_duplicates = duplicates_response['Count']
            
            # Get unchecked duplicates
            unchecked_response = self.final_table.scan(
                FilterExpression='attribute_exists(potential_duplicates) AND size(potential_duplicates) > :zero AND duplicate_checked = :false',
                ExpressionAttributeValues={
                    ':zero': 0,
                    ':false': False
                },
                Select='COUNT'
            )
            unchecked_duplicates = unchecked_response['Count']
            
            return {
                'total_products': total_products,
                'products_with_embeddings': products_with_embeddings,
                'products_with_duplicates': products_with_duplicates,
                'unchecked_duplicates': unchecked_duplicates,
                'completion_rate': f"{((total_products - unchecked_duplicates) / total_products * 100):.1f}%" if total_products > 0 else "0%"
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {'error': str(e)}
