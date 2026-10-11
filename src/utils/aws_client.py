# src/utils/aws_client.py
import boto3
from botocore.exceptions import ClientError
from config.settings import settings
from loguru import logger

class AWSClient:
    def __init__(self):
        """Initialize AWS clients"""
        session_kwargs = {'region_name': settings.AWS_REGION}
        
        self.session = boto3.Session(**session_kwargs)
        self.dynamodb = self.session.resource('dynamodb')
        self.s3 = self.session.client('s3')
        
    def get_table(self, table_name: str):
        """Get DynamoDB table reference"""
        return self.dynamodb.Table(table_name)
    
    def create_table_if_not_exists(self, table_name: str, key_schema: list, 
                                   attribute_definitions: list) -> bool:
        """Create DynamoDB table if it doesn't exist"""
        try:
            table = self.dynamodb.create_table(
                TableName=table_name,
                KeySchema=key_schema,
                AttributeDefinitions=attribute_definitions,
                BillingMode='PAY_PER_REQUEST'
            )
            table.wait_until_exists()
            logger.info(f"Created table: {table_name}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                logger.info(f"Table already exists: {table_name}")
                return True
            else:
                logger.error(f"Error creating table {table_name}: {e}")
                return False