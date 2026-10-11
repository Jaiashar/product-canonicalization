# src/embedding_generator.py
import numpy as np
from typing import Optional, List
from PIL import Image
from config.settings import settings
from src.utils.image_processor import ImageProcessor
from loguru import logger

class EmbeddingGenerator:
    def __init__(self):
        """Initialize embedding generator"""
        self.image_processor = ImageProcessor()
        self.method = settings.EMBEDDING_METHOD
        self.model = None
        self.preprocess = None
        self.device = None
        
        if self.method == 'local':
            self._load_local_clip()
        elif self.method == 'openai':
            self._load_openai_client()
        elif self.method == 'dummy':
            logger.info("Using dummy embeddings for testing")
        else:
            logger.warning(f"Unknown embedding method: {self.method}, falling back to dummy")
            self.method = 'dummy'
    
    def _load_local_clip(self):
        """Load local CLIP model"""
        try:
            import torch
            import clip
            
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model, self.preprocess = clip.load("ViT-B/32", device=self.device)
            logger.info(f"Loaded local CLIP model on {self.device}")
        except ImportError as e:
            logger.error(f"PyTorch or CLIP not installed: {e}")
            logger.info("Falling back to dummy embeddings. Install with: pip install torch torchvision clip-by-openai")
            self.method = 'dummy'
            self.model = None
        except Exception as e:
            logger.error(f"Error loading local CLIP model: {e}")
            logger.info("Falling back to dummy embeddings")
            self.method = 'dummy'
            self.model = None
    
    def _load_openai_client(self):
        """Load OpenAI client"""
        try:
            import openai
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not set in environment")
            self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("Initialized OpenAI client for embeddings")
        except ImportError:
            logger.error("OpenAI library not installed. Install with: pip install openai")
            logger.info("Falling back to dummy embeddings")
            self.method = 'dummy'
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {e}")
            logger.info("Falling back to dummy embeddings")
            self.method = 'dummy'
    
    def generate_embedding(self, image_url: str) -> Optional[List[float]]:
        """Generate embedding for an image"""
        if self.method == 'local':
            return self._generate_local_embedding(image_url)
        elif self.method == 'openai':
            return self._generate_openai_embedding(image_url)
        elif self.method == 'dummy':
            return self._generate_dummy_embedding(image_url)
        else:
            logger.error(f"Unknown embedding method: {self.method}")
            return None
    
    def _generate_local_embedding(self, image_url: str) -> Optional[List[float]]:
        """Generate embedding using local CLIP model"""
        try:
            if not self.model:
                logger.error("Local CLIP model not loaded")
                return self._generate_dummy_embedding(image_url)
            
            import torch
            
            # Download and preprocess image
            image = self.image_processor.download_image(image_url)
            if not image:
                return None
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Preprocess and generate embedding
            image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                image_features = self.model.encode_image(image_tensor)
                # Normalize the features
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            return image_features.cpu().numpy().flatten().tolist()
            
        except Exception as e:
            logger.error(f"Error generating local embedding for {image_url}: {e}")
            return self._generate_dummy_embedding(image_url)
    
    def _generate_openai_embedding(self, image_url: str) -> Optional[List[float]]:
        """Generate embedding using OpenAI API"""
        try:
            if not hasattr(self, 'openai_client'):
                logger.error("OpenAI client not initialized")
                return self._generate_dummy_embedding(image_url)
            
            # Download image
            image = self.image_processor.download_image(image_url)
            if not image:
                return None
            
            # Convert to base64
            image_b64 = self.image_processor.image_to_base64(image)
            if not image_b64:
                return None
            
            # Note: This is a placeholder - OpenAI doesn't have a direct CLIP embedding API
            # You might need to use a different service or implement this differently
            logger.warning("OpenAI CLIP embedding API not implemented - using dummy embedding")
            return self._generate_dummy_embedding(image_url)
            
        except Exception as e:
            logger.error(f"Error generating OpenAI embedding for {image_url}: {e}")
            return self._generate_dummy_embedding(image_url)
    
    def _generate_dummy_embedding(self, image_url: str) -> Optional[List[float]]:
        """Generate a dummy embedding for testing purposes"""
        try:
            # Generate a consistent dummy embedding based on the URL
            # This ensures the same URL always gets the same embedding
            import hashlib
            
            # Create a hash of the URL for consistency
            url_hash = hashlib.md5(image_url.encode()).hexdigest()
            
            # Use hash to seed random number generator for consistency
            import random
            random.seed(url_hash)
            
            # Generate a normalized 512-dimensional embedding
            embedding = [random.gauss(0, 1) for _ in range(512)]
            
            # Normalize to unit vector
            norm = sum(x*x for x in embedding) ** 0.5
            if norm > 0:
                embedding = [x/norm for x in embedding]
            
            logger.debug(f"Generated dummy embedding for {image_url}")
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating dummy embedding for {image_url}: {e}")
            return None
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        try:
            # Convert any Decimal values to float for numpy operations
            from decimal import Decimal
            
            def convert_to_float(val):
                if isinstance(val, Decimal):
                    return float(val)
                return val
            
            # Ensure both embeddings are lists of floats
            embedding1_float = [convert_to_float(x) for x in embedding1]
            embedding2_float = [convert_to_float(x) for x in embedding2]
            
            vec1 = np.array(embedding1_float, dtype=np.float32)
            vec2 = np.array(embedding2_float, dtype=np.float32)
            
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return float(dot_product / (norm1 * norm2))
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0