# src/utils/async_serp_api_client.py
import asyncio
import aiohttp
import time
from typing import Dict, List, Optional, Tuple
from loguru import logger
from config.settings import settings
import json
from dataclasses import dataclass

@dataclass
class SerpResult:
    """Result container for SerpAPI calls"""
    product_id: str
    success: bool
    data: Optional[Dict] = None
    error: Optional[str] = None
    attempts: int = 0

class AsyncSerpAPIClient:
    def __init__(self, max_concurrent: int = 8, max_retries: int = 3):
        """Initialize async SerpAPI client with concurrency control"""
        self.api_key = settings.SERP_API_KEY
        self.base_url = "https://serpapi.com/search"
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        self.rate_limit_delay = 0.5  # Reduced since we're managing concurrency
        
        # Rate limiting
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.last_request_times = []
        
        # Session will be created when needed
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=45, connect=10),
            connector=aiohttp.TCPConnector(limit=20, limit_per_host=10)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _rate_limit(self):
        """Async rate limiting"""
        current_time = time.time()
        
        # Clean old timestamps (older than 60 seconds)
        self.last_request_times = [t for t in self.last_request_times if current_time - t < 60]
        
        # If we've made too many requests recently, wait
        if len(self.last_request_times) >= self.max_concurrent:
            oldest_time = min(self.last_request_times)
            wait_time = self.rate_limit_delay - (current_time - oldest_time)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        self.last_request_times.append(current_time)
    
    async def visual_search_single(self, product_id: str, image_url: str) -> SerpResult:
        """
        Perform single visual search with retries
        """
        async with self.semaphore:  # Limit concurrency
            for attempt in range(1, self.max_retries + 1):
                try:
                    await self._rate_limit()
                    
                    params = {
                        'engine': 'google_lens',
                        'url': image_url,
                        'api_key': self.api_key,
                        'hl': 'en',
                        'country': 'us'
                    }
                    
                    logger.debug(f"SerpAPI attempt {attempt}/{self.max_retries} for {product_id}")
                    
                    async with self.session.get(self.base_url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            logger.debug(f"SerpAPI success for {product_id} on attempt {attempt}")
                            return SerpResult(
                                product_id=product_id,
                                success=True,
                                data=data,
                                attempts=attempt
                            )
                        elif response.status == 429:  # Rate limited
                            error_msg = f"Rate limited (429) for {product_id} on attempt {attempt}"
                            logger.warning(error_msg)
                            if attempt < self.max_retries:
                                # Exponential backoff for rate limiting
                                wait_time = min(2 ** attempt, 30)  # Max 30 seconds
                                logger.info(f"Waiting {wait_time}s before retry for {product_id}")
                                await asyncio.sleep(wait_time)
                                continue
                        else:
                            error_text = await response.text()
                            error_msg = f"SerpAPI error {response.status}: {error_text}"
                            logger.error(f"{error_msg} for {product_id} on attempt {attempt}")
                            
                            if attempt < self.max_retries and response.status >= 500:
                                # Retry server errors
                                await asyncio.sleep(1 * attempt)
                                continue
                            
                            return SerpResult(
                                product_id=product_id,
                                success=False,
                                error=error_msg,
                                attempts=attempt
                            )
                
                except asyncio.TimeoutError:
                    error_msg = f"Timeout for {product_id} on attempt {attempt}"
                    logger.warning(error_msg)
                    if attempt < self.max_retries:
                        await asyncio.sleep(2 * attempt)
                        continue
                        
                except Exception as e:
                    error_msg = f"Unexpected error for {product_id} on attempt {attempt}: {e}"
                    logger.error(error_msg)
                    if attempt < self.max_retries:
                        await asyncio.sleep(1 * attempt)
                        continue
            
            # All attempts failed
            return SerpResult(
                product_id=product_id,
                success=False,
                error=f"All {self.max_retries} attempts failed",
                attempts=self.max_retries
            )
    
    async def visual_search_batch(self, items: List[Tuple[str, str]]) -> List[SerpResult]:
        """
        Perform batch visual search with concurrency control
        
        Args:
            items: List of (product_id, image_url) tuples
        """
        if not items:
            return []
        
        logger.info(f"Starting batch SerpAPI search for {len(items)} products "
                   f"(max_concurrent: {self.max_concurrent})")
        
        # Create tasks for all items
        tasks = [
            self.visual_search_single(product_id, image_url)
            for product_id, image_url in items
        ]
        
        # Execute all tasks concurrently with progress tracking
        results = []
        completed = 0
        
        # Process in chunks to avoid overwhelming the system
        chunk_size = min(50, len(tasks))  # Process max 50 at once
        
        for i in range(0, len(tasks), chunk_size):
            chunk_tasks = tasks[i:i + chunk_size]
            chunk_results = await asyncio.gather(*chunk_tasks, return_exceptions=True)
            
            # Process results and handle exceptions
            for j, result in enumerate(chunk_results):
                if isinstance(result, Exception):
                    product_id = items[i + j][0]
                    logger.error(f"Task exception for {product_id}: {result}")
                    results.append(SerpResult(
                        product_id=product_id,
                        success=False,
                        error=str(result),
                        attempts=0
                    ))
                else:
                    results.append(result)
                
                completed += 1
                
                # Log progress every 10 items
                if completed % 10 == 0:
                    success_count = sum(1 for r in results if r.success)
                    logger.info(f"SerpAPI progress: {completed}/{len(items)} "
                               f"({success_count} successful)")
        
        # Final summary
        success_count = sum(1 for r in results if r.success)
        logger.info(f"SerpAPI batch complete: {success_count}/{len(items)} successful")
        
        return results
    
    def extract_product_info(self, search_result: Dict) -> Dict:
        """
        Extract relevant product information from Google Lens search results
        Focus on top results only for efficiency
        """
        try:
            product_info = {
                'product_titles': [],
                'sources': [],
                'visual_matches': []
            }
            
            # Process visual matches (top 5 only)
            visual_matches = search_result.get('visual_matches', [])
            for match in visual_matches[:5]:  # Only top 5 for speed
                match_data = {
                    'title': match.get('title', ''),
                    'source': match.get('source', ''),
                    'link': match.get('link', ''),
                    'price': match.get('price', {}),
                    'rating': match.get('rating'),
                    'reviews': match.get('reviews'),
                    'in_stock': match.get('in_stock'),
                    'condition': match.get('condition', ''),
                    'thumbnail': match.get('thumbnail', '')
                }
                
                product_info['visual_matches'].append(match_data)
                
                # Collect titles and sources for AI processing
                if match_data['title']:
                    product_info['product_titles'].append(match_data['title'])
                if match_data['source']:
                    product_info['sources'].append(match_data['source'])
            
            return product_info
            
        except Exception as e:
            logger.error(f"Error extracting product info from Google Lens data: {e}")
            return {
                'product_titles': [],
                'sources': [],
                'visual_matches': []
            }

# Compatibility wrapper for existing synchronous code
class SerpAPIClientCompat:
    """Compatibility wrapper for existing synchronous SerpAPI usage"""
    
    def __init__(self):
        self.async_client = AsyncSerpAPIClient()
    
    def visual_search(self, image_url: str) -> Optional[Dict]:
        """Synchronous wrapper for async visual_search"""
        async def _search():
            async with self.async_client as client:
                result = await client.visual_search_single("sync_call", image_url)
                return result.data if result.success else None
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, we can't use run()
                logger.warning("Synchronous SerpAPI call from async context - consider using async version")
                return None
            else:
                return asyncio.run(_search())
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(_search())
    
    def extract_product_info(self, search_result: Dict) -> Dict:
        """Extract product info (same as async version)"""
        return self.async_client.extract_product_info(search_result)