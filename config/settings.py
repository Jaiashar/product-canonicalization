# config/settings.py
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        # AWS Configuration
        self.AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
        self.AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
        self.AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
        
        # DynamoDB Tables
        self.SOURCE_TABLE_NAME = os.getenv('SOURCE_TABLE_NAME', 'LuxuryProductsTable')
        self.FINAL_TABLE_NAME = os.getenv('FINAL_TABLE_NAME', 'FinalProductsTable')
        
        # Embedding Configuration
        self.EMBEDDING_METHOD = os.getenv('EMBEDDING_METHOD', 'local')  # local or openai
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
        self.SIMILARITY_THRESHOLD = float(os.getenv('SIMILARITY_THRESHOLD', '0.85'))
        self.MODEL_SIMILARITY_THRESHOLD = float(os.getenv('MODEL_SIMILARITY_THRESHOLD', '0.3'))
        
        # SerpAPI Configuration
        self.SERP_API_KEY = os.getenv('SERP_API_KEY')
        self.USE_SERP_API = os.getenv('USE_SERP_API', 'true').lower() == 'true'
        self.SERP_RATE_LIMIT = float(os.getenv('SERP_RATE_LIMIT', '1.0'))
        self.SERP_CONFIDENCE_THRESHOLD = float(os.getenv('SERP_CONFIDENCE_THRESHOLD', '0.3'))
        
        # AI Processing Configuration
        self.USE_AI_PARSING = os.getenv('USE_AI_PARSING', 'true').lower() == 'true'
        self.AI_CONFIDENCE_THRESHOLD = float(os.getenv('AI_CONFIDENCE_THRESHOLD', '0.7'))
        self.AI_BATCH_SIZE = int(os.getenv('AI_BATCH_SIZE', '5'))  # Process 5 items per AI call
        
        # Logging
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_FILE = os.getenv('LOG_FILE', 'logs/canonicalization.log')
        
        # Processing
        self.BATCH_SIZE = int(os.getenv('BATCH_SIZE', '100'))

settings = Settings()