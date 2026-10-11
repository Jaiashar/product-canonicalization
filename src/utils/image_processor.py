# src/utils/image_processor.py - Targeted fix for S3 images
import requests
import numpy as np
from PIL import Image
import io
import base64
from typing import Optional, List
from loguru import logger

class ImageProcessor:
    def __init__(self):
        """Initialize image processor"""
        # Add headers to mimic a real browser - some S3 buckets check this
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
        }
    
    def download_image(self, url: str) -> Optional[Image.Image]:
        """Download image from URL with S3-specific fixes"""
        try:
            logger.debug(f"Attempting to download image: {url}")
            
            # Use stream=True to handle large images better
            response = requests.get(url, timeout=30, headers=self.headers, stream=True)
            
            if response.status_code != 200:
                logger.error(f"Failed to download image: {url} (status: {response.status_code})")
                return None
            
            # Read all content at once - this is crucial for S3 images
            image_data = response.content
            
            if not image_data:
                logger.error(f"Empty response from image URL: {url}")
                return None
            
            logger.debug(f"Downloaded {len(image_data)} bytes from {url}")
            
            # Create BytesIO object and seek to beginning - THIS IS KEY
            image_buffer = io.BytesIO(image_data)
            image_buffer.seek(0)  # Ensure we're at the start
            
            try:
                # Try to open the image
                image = Image.open(image_buffer)
                
                # Load the image data immediately to catch any issues
                image.load()  # This forces PIL to read and decode the image
                
                # Convert to RGB if needed (RGBA, P mode, etc.)
                if image.mode not in ('RGB', 'L'):
                    image = image.convert('RGB')
                
                logger.debug(f"Successfully opened image: {url} ({image.size[0]}x{image.size[1]}, {image.mode})")
                return image
                
            except Exception as pil_error:
                logger.error(f"PIL cannot open image from {url}: {pil_error}")
                
                # Additional debugging - check what we actually got
                logger.debug(f"Response headers: {dict(response.headers)}")
                logger.debug(f"Content length: {len(image_data)}")
                logger.debug(f"First 100 bytes: {image_data[:100]}")
                
                # Try alternative approach - save to temporary file and re-read
                try:
                    import tempfile
                    import os
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                        tmp_file.write(image_data)
                        tmp_file.flush()
                        
                        # Try to open from file
                        image = Image.open(tmp_file.name)
                        image.load()
                        
                        # Clean up temp file
                        os.unlink(tmp_file.name)
                        
                        logger.info(f"Successfully opened image via temp file: {url}")
                        return image
                        
                except Exception as temp_error:
                    logger.error(f"Temp file approach also failed for {url}: {temp_error}")
                
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error downloading image {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading image {url}: {e}")
            return None
    
    def download_image_robust(self, url: str) -> Optional[Image.Image]:
        """Most robust download method - tries multiple approaches"""
        
        # Method 1: Standard approach
        try:
            image = self.download_image(url)
            if image is not None:
                return image
        except Exception as e:
            logger.warning(f"Standard download failed for {url}: {e}")
        
        # Method 2: Different request approach
        try:
            logger.info(f"Trying alternative download method for {url}")
            
            # Try without stream, different headers
            simple_headers = {'User-Agent': 'Python-requests/2.28.1'}
            response = requests.get(url, timeout=45, headers=simple_headers)
            
            if response.status_code == 200:
                # Try direct PIL opening
                image = Image.open(io.BytesIO(response.content))
                image.load()
                
                if image.mode not in ('RGB', 'L'):
                    image = image.convert('RGB')
                
                logger.info(f"Alternative method succeeded for {url}")
                return image
                
        except Exception as e:
            logger.warning(f"Alternative download also failed for {url}: {e}")
        
        # Method 3: Raw urllib approach (last resort)
        try:
            logger.info(f"Trying urllib fallback for {url}")
            import urllib.request
            
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as response:
                image_data = response.read()
                
            image = Image.open(io.BytesIO(image_data))
            image.load()
            
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
            
            logger.info(f"urllib method succeeded for {url}")
            return image
            
        except Exception as e:
            logger.error(f"All download methods failed for {url}: {e}")
        
        return None
    
    def image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        try:
            buffer = io.BytesIO()
            if image.mode != 'RGB':
                image = image.convert('RGB')
            image.save(buffer, format='JPEG', quality=85)
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error converting image to base64: {e}")
            return ""
    
    def resize_image(self, image: Image.Image, max_size: tuple = (224, 224)) -> Image.Image:
        """Resize image while maintaining aspect ratio"""
        try:
            resized_image = image.copy()
            resized_image.thumbnail(max_size, Image.Resampling.LANCZOS)
            return resized_image
        except Exception as e:
            logger.error(f"Error resizing image: {e}")
            return image