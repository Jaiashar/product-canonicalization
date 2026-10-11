#!/usr/bin/env python3
"""
Simple script to test AWS connectivity and verify table access
"""
import boto3
from dotenv import load_dotenv
import os
import sys

# Load environment variables
load_dotenv()

def test_aws_connection():
    """Test AWS connection and verify table access"""
    try:
        print("🔍 Testing AWS connection...")
        
        # Test DynamoDB connection
        region = os.getenv('AWS_REGION', 'us-east-1')
        dynamodb = boto3.resource('dynamodb', region_name=region)
        
        print(f"✅ Connected to DynamoDB in region: {region}")
        
        # List tables
        tables = list(dynamodb.tables.all())
        table_names = [table.name for table in tables]
        print(f"📋 Found {len(tables)} DynamoDB tables: {table_names}")
        
        # Check source table
        source_table_name = os.getenv('SOURCE_TABLE_NAME', 'LuxuryProductsTable')
        if source_table_name in table_names:
            source_table = dynamodb.Table(source_table_name)
            print(f"✅ Source table '{source_table_name}' found")
            print(f"   Item count: {source_table.item_count}")
            print(f"   Table size: {source_table.table_size_bytes / 1024 / 1024:.2f} MB")
            
            # Test reading a few items
            response = source_table.scan(Limit=3)
            items = response.get('Items', [])
            print(f"   Sample items: {len(items)} retrieved")
            
            if items:
                sample_item = items[0]
                print(f"   Sample product_id: {sample_item.get('product_id', 'N/A')}")
                print(f"   Sample brand: {sample_item.get('brand', 'N/A')}")
                
        else:
            print(f"❌ Source table '{source_table_name}' not found")
            print(f"Available tables: {table_names}")
            return False
        
        # Check final table
        final_table_name = os.getenv('FINAL_TABLE_NAME', 'FinalProductsTable')
        if final_table_name in table_names:
            final_table = dynamodb.Table(final_table_name)
            print(f"✅ Final table '{final_table_name}' found")
            print(f"   Item count: {final_table.item_count}")
        else:
            print(f"⚠️  Final table '{final_table_name}' not found (will be created)")
        
        # Test S3 access (optional)
        try:
            s3 = boto3.client('s3', region_name=region)
            buckets = s3.list_buckets()
            print(f"✅ S3 access verified - {len(buckets['Buckets'])} buckets accessible")
        except Exception as e:
            print(f"⚠️  S3 access limited: {e}")
        
        print("\n🎉 AWS connection test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ AWS connection test failed: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Check your AWS credentials in .env file")
        print("2. Verify AWS CLI is configured: aws configure list")
        print("3. Ensure your IAM user has DynamoDB permissions")
        print("4. Check if the region is correct")
        return False

def check_environment():
    """Check if environment is properly configured"""
    print("🔧 Checking environment configuration...")
    
    required_vars = ['AWS_REGION']
    optional_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'SOURCE_TABLE_NAME', 'FINAL_TABLE_NAME']
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {missing_vars}")
        return False
    
    print("✅ Environment configuration looks good")
    
    # Show configuration
    print("\n📋 Current configuration:")
    print(f"   AWS Region: {os.getenv('AWS_REGION')}")
    print(f"   Source Table: {os.getenv('SOURCE_TABLE_NAME', 'LuxuryProductsTable')}")
    print(f"   Final Table: {os.getenv('FINAL_TABLE_NAME', 'FinalProductsTable')}")
    print(f"   Embedding Method: {os.getenv('EMBEDDING_METHOD', 'local')}")
    print(f"   Similarity Threshold: {os.getenv('SIMILARITY_THRESHOLD', '0.85')}")
    
    return True

if __name__ == "__main__":
    print("🚀 AWS Connection Test")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    print()
    
    # Test connection
    if not test_aws_connection():
        sys.exit(1)
    
    print("\n✨ Ready to run canonicalization!")
    print("Next steps:")
    print("1. python scripts/setup_tables.py")
    print("2. python scripts/run_canonicalization.py")
    print("3. python scripts/review_duplicates.py")