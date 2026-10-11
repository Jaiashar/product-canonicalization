# src/utils/category_classifier.py - ANTHROPIC CLAUDE VERSION WITH SOURCE AWARENESS
import anthropic
import json
from typing import Dict, List, Optional
from loguru import logger
from config.settings import settings

class CategoryClassifier:
    def __init__(self):
        """Initialize category classifier with Anthropic Claude"""
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY) if settings.ANTHROPIC_API_KEY else None
        
        # Simplified to 6 core categories
        self.categories = [
            'shoes',
            'bags', 
            'clothing',
            'accessories',
            'jewelry',
            'watches'
        ]
        
        # Enhanced keyword mapping with more comprehensive terms
        self.keyword_mapping = {
            'shoes': ['shoe', 'sneaker', 'boot', 'sandal', 'heel', 'pump', 'loafer', 'oxford', 'trainer', 'runner', 'slip-on', 'slide', 'flip-flop', 'clog', 'mule', 'espadrille', 'athletic', 'footwear'],
            'bags': ['bag', 'handbag', 'purse', 'backpack', 'tote', 'clutch', 'satchel', 'briefcase', 'duffle', 'messenger', 'crossbody', 'wallet', 'cardholder', 'pouch', 'camera bag', 'shoulder bag', 'hobo bag'],
            'clothing': ['shirt', 'dress', 'jacket', 'coat', 'sweater', 'hoodie', 'pants', 'jeans', 'skirt', 'blouse', 'cardigan', 'blazer', 'suit', 'top', 'bottom', 'shorts', 'leggings', 'tweed', 'pattern', 'fabric', 'wool', 'cotton', 'silk', 'cashmere', 'denim', 'knitwear'],
            'jewelry': ['ring', 'necklace', 'bracelet', 'earring', 'pendant', 'chain', 'charm', 'brooch', 'cufflink', 'anklet', 'choker', 'bangle', 'stud', 'hoop'],
            'watches': ['watch', 'timepiece', 'chronograph', 'smartwatch', 'wristwatch'],
            'accessories': ['belt', 'scarf', 'hat', 'sunglasses', 'gloves', 'tie', 'bow tie', 'pocket square', 'keychain', 'phone case', 'fragrance', 'perfume', 'cologne']
        }
        
        # URL pattern mapping for more accurate classification
        self.url_patterns = {
            'shoes': ['/shoes/', '/footwear/', '/sneakers/', '/boots/', '/sandals/', '/heels/', '/pumps/', '/loafers/', '/oxfords/'],
            'bags': ['/bags/', '/handbags/', '/purses/', '/backpacks/', '/totes/', '/clutches/', '/briefcases/', '/wallets/'],
            'clothing': ['/clothing/', '/apparel/', '/jackets/', '/coats/', '/dresses/', '/shirts/', '/blouses/', '/pants/', '/jeans/', '/skirts/', '/sweaters/', '/hoodies/', '/blazers/', '/suits/', '/tops/', '/bottoms/'],
            'jewelry': ['/jewelry/', '/rings/', '/necklaces/', '/bracelets/', '/earrings/', '/pendants/', '/chains/', '/charms/'],
            'watches': ['/watches/', '/timepieces/', '/chronographs/'],
            'accessories': ['/accessories/', '/belts/', '/scarves/', '/hats/', '/sunglasses/', '/gloves/', '/ties/', '/fragrances/', '/perfumes/']
        }

    def classify_batch(self, products: List[Dict]) -> List[Dict]:
        """Always reclassify all products with source awareness"""
        try:
            # Always reclassify all products regardless of current category
            logger.info(f"Reclassifying {len(products)} products with source awareness")
            
            # First, try URL-based classification (most reliable)
            url_classified = self._classify_by_url_batch(products)
            
            # For products without clear URL classification, use AI or keywords
            need_ai_classification = []
            for product in url_classified:
                if product.get('classification_confidence', 0) < 0.8:
                    need_ai_classification.append(product)
            
            if need_ai_classification and self.client:
                # Use AI for ambiguous cases with source awareness
                ai_results = self._classify_with_ai_source_aware(need_ai_classification)
                
                # Update products with AI results
                ai_dict = {result.get('product_index', i): result for i, result in enumerate(ai_results)}
                
                for i, product in enumerate(url_classified):
                    if product.get('classification_confidence', 0) < 0.8:
                        if i in ai_dict:
                            ai_result = ai_dict[i]
                            product['category'] = ai_result.get('category', 'accessories')
                            product['classification_confidence'] = ai_result.get('confidence', 0.7)
                            product['classification_reasoning'] = ai_result.get('reasoning', 'AI classification with source awareness')
            else:
                # Fallback to keyword classification for ambiguous cases
                for product in url_classified:
                    if product.get('classification_confidence', 0) < 0.8:
                        keyword_category = self._classify_with_keywords_single(product)
                        product['category'] = keyword_category
                        product['classification_confidence'] = 0.6
                        product['classification_reasoning'] = 'Keyword-based classification'
            
            # Log reclassification results
            for product in url_classified:
                logger.info(f"Reclassified {product.get('product_id', 'unknown')}: {product.get('category')} "
                           f"(confidence: {product.get('classification_confidence', 0):.2f})")
            
            return url_classified
            
        except Exception as e:
            logger.error(f"Error in batch classification: {e}")
            return self._classify_with_keywords_batch(products)
        
    def _clean_json_response_robust(self, content: str) -> str:
        """Robust JSON cleaning for Claude responses (copied from ai_product_parser.py)"""
        try:
            # Step 1: Basic cleaning
            cleaned = content.strip()
            
            # Remove markdown code blocks
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            if cleaned.startswith('```'):
                cleaned = cleaned[3:]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            # Step 2: Find JSON boundaries
            start = cleaned.find('{')
            if start == -1:
                logger.error("No JSON object found in response")
                return '{}'
            
            # Step 3: Handle truncated responses
            if '...' in cleaned or '"reasoning": "' in cleaned and not cleaned.count('"reasoning"') == cleaned.count('"category"'):
                logger.warning("Detected truncated JSON response, applying aggressive repair")
                return self._create_minimal_valid_json(cleaned, start)
            
            # Find the matching closing brace
            brace_count = 0
            end = len(cleaned)
            for i, char in enumerate(cleaned[start:], start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = i + 1
                        break
            
            # If we didn't find a proper closing, the JSON is truncated
            if brace_count > 0:
                logger.warning(f"JSON appears truncated (unclosed braces: {brace_count}), creating minimal valid JSON")
                return self._create_minimal_valid_json(cleaned, start)
            
            cleaned = cleaned[start:end]
            
            # Step 4: Fix common JSON issues
            cleaned = re.sub(r',\s*}', '}', cleaned)
            cleaned = re.sub(r',\s*]', ']', cleaned)
            
            # Fix unterminated strings by adding closing quotes
            lines = cleaned.split('\n')
            for i, line in enumerate(lines):
                # Count quotes in the line
                quote_count = line.count('"')
                if quote_count % 2 == 1:  # Odd number of quotes = unterminated string
                    # Find the last quote and add a closing quote before any comma or brace
                    last_quote_pos = line.rfind('"')
                    after_quote = line[last_quote_pos + 1:]
                    if ',' in after_quote or '}' in after_quote:
                        # Insert closing quote before the comma/brace
                        insert_pos = last_quote_pos + 1
                        for char in after_quote:
                            if char in ',}':
                                break
                            insert_pos += 1
                        lines[i] = line[:insert_pos] + '"' + line[insert_pos:]
            
            cleaned = '\n'.join(lines)
            
            # Validate that we have valid JSON structure
            try:
                json.loads(cleaned)
                return cleaned
            except json.JSONDecodeError as e:
                logger.warning(f"Cleaned JSON still invalid ({e}), creating minimal valid JSON")
                return self._create_minimal_valid_json(content, start)
            
        except Exception as e:
            logger.error(f"Error in robust JSON cleaning: {e}")
            return self._create_minimal_valid_json(content, 0)

    def _create_minimal_valid_json(self, content: str, start_pos: int) -> str:
        """Create minimal valid JSON for category classification"""
        try:
            # For category classification, we need a simpler structure
            return '{"classifications": []}'
            
        except Exception as e:
            logger.error(f"Error creating minimal valid JSON: {e}")
            return '{"classifications": []}'

    def _classify_by_url_batch(self, products: List[Dict]) -> List[Dict]:
        """Classify products based on URL patterns (most reliable method)"""
        classified_products = []
        
        for product in products:
            source_url = product.get('source_url', '').lower()
            classified_category = None
            confidence = 0.0
            
            if source_url:
                # Check URL patterns for each category
                for category, patterns in self.url_patterns.items():
                    if any(pattern in source_url for pattern in patterns):
                        classified_category = category
                        confidence = 0.9  # High confidence for URL-based classification
                        break
            
            # Update product with classification result
            updated_product = product.copy()
            if classified_category:
                updated_product['category'] = classified_category
                updated_product['classification_confidence'] = confidence
                updated_product['classification_reasoning'] = f'URL-based classification from {source_url}'
                logger.info(f"URL classified {product.get('product_id')}: {classified_category} from URL")
            else:
                # Keep original category but with low confidence for further processing
                updated_product['classification_confidence'] = 0.3
                updated_product['classification_reasoning'] = 'No clear URL pattern, needs further classification'
            
            classified_products.append(updated_product)
        
        return classified_products

    def _classify_with_ai_source_aware(self, products: List[Dict]) -> List[Dict]:
        """Use AI to classify product categories with source awareness"""
        try:
            prompt = self._create_source_aware_classification_prompt(products)
            
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                temperature=0.1,
                system=self._get_source_aware_classification_system_prompt(),
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            response_content = response.content[0].text
            
            # USE ROBUST CLEANING (NEW)
            cleaned_content = self._clean_json_response_robust(response_content)
            
            result = json.loads(cleaned_content)
            classifications = result.get('classifications', [])
            
            # Validate classifications
            validated_classifications = []
            for i, classification in enumerate(classifications):
                category = classification.get('category', 'accessories')
                if category not in self.categories:
                    logger.warning(f"Invalid category {category}, defaulting to accessories")
                    category = 'accessories'
                
                validated_classifications.append({
                    'product_index': i,
                    'category': category,
                    'confidence': classification.get('confidence', 0.7),
                    'reasoning': classification.get('reasoning', 'AI classification with source awareness')
                })
            
            return validated_classifications
            
        except Exception as e:
            logger.error(f"Error in AI classification: {e}")
            return []

    def _get_source_aware_classification_system_prompt(self) -> str:
        """Enhanced system prompt for category classification with source awareness"""
        categories_str = ', '.join(self.categories)
        return f"""You are an expert at classifying luxury fashion and lifestyle products into categories with source quality awareness.

Available categories: {categories_str}

SOURCE-AWARE CLASSIFICATION RULES:
1. **PRIORITIZE URL PATTERNS** - If URL contains /clothing/, it's clothing regardless of name confusion
2. **CONSIDER SOURCE QUALITY** - High-quality sources (StockX, Rebag) have more reliable names
3. **USE ENHANCED NAMES** - When available, enhanced names from SerpAPI are often cleaner
4. **VALIDATE WITH SERP CONTEXT** - Multiple SerpAPI titles can confirm category

Category indicators with source context:
- **CLOTHING**: jacket, coat, dress, shirt, blouse, sweater, hoodie, pants, jeans, skirt, blazer, suit, top, bottom
- **BAGS**: bag, handbag, purse, backpack, tote, clutch, satchel, briefcase, duffle, messenger, crossbody, wallet
- **SHOES**: shoe, sneaker, boot, sandal, heel, pump, loafer, oxford, trainer, runner, slip-on, athletic, footwear
- **JEWELRY**: ring, necklace, bracelet, earring, pendant, chain, charm, brooch, cufflink, anklet, choker
- **WATCHES**: watch, timepiece, chronograph, smartwatch, wristwatch
- **ACCESSORIES**: belt, scarf, hat, sunglasses, gloves, tie, bow tie, keychain, fragrance, perfume

Special source considerations:
- **TheRealReal**: Often has category confusion due to poor naming, use SerpAPI context
- **StockX**: Excellent category consistency, trust the product names
- **Fashionphile**: Great category organization, but verify with enhanced names
- **Rebag**: Specialized in bags, very reliable for bag classification

Return ONLY valid JSON without markdown formatting."""

    def _create_source_aware_classification_prompt(self, products: List[Dict]) -> str:
        """Create enhanced prompt for category classification with source awareness"""
        prompt = "Classify these luxury products using source awareness and enhanced context:\n\n"
        
        for i, product in enumerate(products, 1):
            prompt += f"PRODUCT {i}:\n"
            prompt += f"Brand: {product.get('brand', '')}\n"
            prompt += f"Original Name: {product.get('original_product_name', '')}\n"
            
            # Include enhanced name if available
            enhanced_name = product.get('enhanced_product_name', '')
            if enhanced_name and enhanced_name != product.get('original_product_name', ''):
                prompt += f"Enhanced Name: {enhanced_name}\n"
            
            prompt += f"Model: {product.get('model', '')}\n"
            prompt += f"Source URL: {product.get('source_url', '')}\n"
            
            # Include source domain information
            source_domain = self._extract_source_domain(product.get('source_url', ''))
            if source_domain:
                prompt += f"Source Domain: {source_domain}\n"
            
            # Include serp titles if available
            serp_titles = product.get('serp_info', {}).get('product_titles', [])
            if serp_titles:
                prompt += f"SerpAPI Context: {serp_titles[:3]}\n"
            
            # Include current category as context but don't trust it
            current_category = product.get('category', 'unknown')
            if current_category != 'unknown':
                prompt += f"Current Category (verify): {current_category}\n"
            
            prompt += "\n"
        
        categories_str = ', '.join(self.categories)
        prompt += f"""
CRITICAL: 
1. Use URL patterns as PRIMARY indicator (/clothing/ = clothing, /bags/ = bags)
2. Consider source quality (StockX/Rebag more reliable than TheRealReal)
3. Use enhanced names when available (often cleaner than original)
4. Validate with SerpAPI context when multiple titles suggest same category

Classify each product into: {categories_str}

Return JSON:
{{
  "classifications": [
    {{
      "product_index": 1,
      "category": "clothing",
      "confidence": 0.95,
      "reasoning": "URL contains /clothing/ and enhanced name confirms jacket"
    }}
  ]
}}"""
        return prompt

    def _extract_source_domain(self, url: str) -> str:
        """Extract domain from URL"""
        if not url:
            return ''
        
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return ''

    def _classify_with_keywords_batch(self, products: List[Dict]) -> List[Dict]:
        """Classify multiple products using keyword matching"""
        result_products = []
        
        for product in products:
            category = self._classify_with_keywords_single(product)
            updated_product = product.copy()
            updated_product['category'] = category
            updated_product['classification_confidence'] = 0.6
            updated_product['classification_reasoning'] = 'Keyword-based classification'
            result_products.append(updated_product)
        
        return result_products

    def _classify_with_keywords_single(self, product: Dict) -> str:
        """Classify single product using enhanced keyword matching with source awareness"""
        # Combine text fields for analysis, prioritizing enhanced names
        text_fields = []
        
        # Prioritize enhanced name if available
        enhanced_name = product.get('enhanced_product_name', '')
        original_name = product.get('original_product_name', '')
        
        if enhanced_name and enhanced_name != original_name:
            text_fields.append(enhanced_name)  # Higher priority
            text_fields.append(original_name)
        else:
            text_fields.append(original_name)
        
        text_fields.extend([
            product.get('brand', ''),
            product.get('model', ''),
            product.get('source_url', '')
        ])
        
        # Add serp titles if available
        serp_titles = product.get('serp_info', {}).get('product_titles', [])
        text_fields.extend(serp_titles[:3])
        
        combined_text = ' '.join(text_fields).lower()
        
        # First, check URL patterns (highest priority)
        source_url = product.get('source_url', '').lower()
        if source_url:
            for category, patterns in self.url_patterns.items():
                if any(pattern in source_url for pattern in patterns):
                    logger.info(f"URL-based classification: {product.get('product_id')} -> {category}")
                    return category
        
        # Score each category based on keyword matches
        category_scores = {}
        for category, keywords in self.keyword_mapping.items():
            score = 0
            for keyword in keywords:
                if keyword in combined_text:
                    # Weight enhanced names higher
                    if enhanced_name and keyword in enhanced_name.lower():
                        score += 3
                    # Weight URL matches higher
                    elif keyword in source_url:
                        score += 2
                    else:
                        score += 1
            
            if score > 0:
                category_scores[category] = score
        
        # Return category with highest score, default to accessories
        if category_scores:
            best_category = max(category_scores, key=category_scores.get)
            logger.debug(f"Keyword classification: {product.get('product_id')} -> {best_category} (score: {category_scores[best_category]})")
            return best_category
        
        logger.debug(f"No clear category found for {product.get('product_id')}, defaulting to accessories")
        return 'accessories'  # Default fallback