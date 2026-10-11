# src/utils/ai_product_parser.py - ANTHROPIC CLAUDE 3.5 VERSION WITH INTELLIGENT SOURCE SELECTION
import anthropic
import json
import asyncio
import re
from typing import Dict, List, Optional
from loguru import logger
from config.settings import settings

class AIProductParser:
    def __init__(self):
        """Initialize AI product parser with Anthropic Claude 3.5"""
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.max_batch_size = 10
        self.max_concurrent_requests = 3
        
    def parse_product_batch(self, products: List[Dict]) -> List[Dict]:
        """Parse multiple products with intelligent source selection context"""
        if not products:
            return []
            
        # Cap batch size to avoid token limits
        if len(products) > self.max_batch_size:
            logger.warning(f"Batch size {len(products)} exceeds max {self.max_batch_size}, splitting...")
            results = []
            for i in range(0, len(products), self.max_batch_size):
                batch = products[i:i + self.max_batch_size]
                results.extend(self.parse_product_batch(batch))
            return results
        
        try:
            # Prepare batch data with intelligent source selection context
            batch_data = []
            for product in products:
                # Use enhanced name if available
                enhanced_name = product.get('serp_enhanced_name', '')
                original_name = product.get('original_product_name', '')
                
                # Get source selection information
                source_scores = product.get('source_scores', {})
                selected_source = source_scores.get('selected_source', 'original')
                source_domain = source_scores.get('source_domain', 'unknown')
                source_reasoning = source_scores.get('source_reasoning', 'Unknown source quality')
                
                # Choose best name based on intelligent selection
                if selected_source == 'serpapi' and enhanced_name:
                    best_name = enhanced_name
                    confidence_modifier = 0.1  # Boost confidence for selected SerpAPI
                else:
                    best_name = original_name
                    confidence_modifier = 0.0
                
                serp_titles = product.get('serp_info', {}).get('product_titles', [])
                serp_confidence = product.get('serp_confidence', 0.0)
                
                product_data = {
                    'product_id': product['product_id'],
                    'original_name': original_name,
                    'enhanced_name': enhanced_name,
                    'best_name': best_name,
                    'brand': product.get('brand', ''),
                    'current_model': product.get('model', ''),
                    'category': product.get('category', 'unknown'),
                    'source_url': product.get('source_url', ''),
                    'source_domain': source_domain,
                    'source_reasoning': source_reasoning,
                    'selected_source': selected_source,
                    'confidence_modifier': confidence_modifier,
                    'serp_confidence': serp_confidence,
                    'top_serp_titles': serp_titles[:3],
                    'visual_matches': [
                        {'title': match.get('title', ''), 'source': match.get('source', '')}
                        for match in product.get('serp_info', {}).get('visual_matches', [])[:2]
                    ]
                }
                batch_data.append(product_data)
            
            # Create enhanced prompt with intelligent source selection context
            prompt = self._create_intelligent_source_prompt(batch_data)
            
            # Call Anthropic Claude API
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=min(2000, len(products) * 150),
                temperature=0.1,
                system=self._get_intelligent_source_system_prompt(),
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse response
            response_content = response.content[0].text
            
            if not response_content or response_content.strip() == "":
                logger.error("Empty response from Claude")
                return self._create_fallback_results(batch_data)
            
            # Clean and parse response
            cleaned_content = self._clean_json_response_robust(response_content)
            
            try:
                result = json.loads(cleaned_content)
                parsed_results = result.get('products', [])
                
                # Enhanced validation with intelligent source selection context
                parsed_results = self._validate_results_with_source_context(parsed_results, batch_data)
                
                # Final validation and fixes
                parsed_results = self._validate_and_fix_results(parsed_results, batch_data)
                
                logger.info(f"Successfully parsed {len(parsed_results)} products with intelligent source selection")
                return parsed_results
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed after cleaning: {e}")
                logger.error(f"Cleaned content: {cleaned_content[:500]}...")
                
                # Try to extract partial results
                recovered_results = self._extract_partial_results(cleaned_content, batch_data)
                if recovered_results:
                    logger.info(f"Recovered {len(recovered_results)} products from malformed JSON")
                    return recovered_results
                
                return self._create_fallback_results(batch_data)
            
        except Exception as e:
            logger.error(f"Error in intelligent source selection AI batch parsing: {e}")
            return self._create_fallback_results(batch_data)
    
    def _get_intelligent_source_system_prompt(self) -> str:
        """Enhanced system prompt that considers intelligent source selection"""
        return """You are an expert at parsing luxury product names with intelligent source selection.

INTELLIGENT SOURCE PRIORITIZATION:
- HIGH-QUALITY SOURCES (StockX, Rebag, Farfetch): Trust original names, use cautiously with SerpAPI
- LOW-QUALITY SOURCES (TheRealReal): Prefer SerpAPI data when available and confident
- MEDIUM-QUALITY SOURCES (Fashionphile): Balance original and SerpAPI data

KEY PRINCIPLES:
1. **RESPECT SOURCE SELECTION** - The system has already chosen the best name source
2. **PRESERVE SPECIFICITY** - Don't lose model numbers or collection names
3. **EXTRACT CLEAN DATA** - Focus on brand, model, collaborator, colorway
4. **MAINTAIN CONFIDENCE** - Higher confidence when source selection is optimal

FORMAT: "Brand [x Collaborator] Model [ProductType] [Colorway]"

SOURCE-SPECIFIC PROCESSING:
- **StockX/Rebag (Original Selected)**: Trust the specific model names, high confidence
- **TheRealReal (SerpAPI Selected)**: Clean extracted data, moderate confidence  
- **Mixed Sources**: Use both original and SerpAPI context for validation

MODEL EXTRACTION PRIORITY:
1. Model numbers (4-5 digits): "7555", "12345"
2. Collection names: "Hamptons", "Neverfull", "Speedy", "Capucines"
3. Specific descriptors: "Twist-Lock", "Top Handle", "Camera Bag"
4. Size descriptors: "Mini", "PM", "MM", "GM"

EXAMPLES BY SOURCE QUALITY:

✅ HIGH-QUALITY SOURCE (Original Selected):
   INPUT: source="stockx.com", best_name="Samba LT Core Black Cloud White"
   OUTPUT: model="Samba LT", colorway="Core Black Cloud White"

✅ LOW-QUALITY SOURCE (SerpAPI Selected):
   INPUT: source="therealreal.com", best_name="Coach 7555 Hamptons Black Leather Satchel"
   OUTPUT: model="7555 Hamptons Satchel", colorway="Black"

✅ MEDIUM-QUALITY SOURCE (Balanced):
   INPUT: source="fashionphile.com", best_name="Caviar Quilted Small Double Flap"
   OUTPUT: model="Quilted Small Double Flap", colorway="Caviar"

CONFIDENCE SCORING:
- High-quality source + specific model = confidence 0.95
- SerpAPI selected + clean extraction = confidence 0.85
- Original selected + validation = confidence 0.90
- Fallback extraction = confidence 0.6

Return ONLY valid JSON with source-aware processing that respects the intelligent selection."""

    def _create_intelligent_source_prompt(self, batch_data: List[Dict]) -> str:
        """Create enhanced prompt that emphasizes intelligent source selection"""
        prompt = f"Parse {len(batch_data)} products using intelligent source selection:\n\n"
        
        for i, product in enumerate(batch_data, 1):
            prompt += f"PRODUCT {i} (ID: {product['product_id']}):\n"
            prompt += f"Brand: {product['brand']}\n"
            prompt += f"Category: {product['category']}\n"
            prompt += f"Source Domain: {product['source_domain']}\n"
            prompt += f"Selected Source: {product['selected_source']}\n"
            prompt += f"Source Quality: {product['source_reasoning']}\n"
            
            # Show the intelligently selected name
            prompt += f"🎯 SELECTED NAME: {product['best_name']}\n"
            
            # Show alternative for context
            if product['selected_source'] == 'serpapi':
                prompt += f"Original Name: {product['original_name']}\n"
                if product['serp_confidence'] > 0.7:
                    prompt += f"📍 HIGH SERPAPI CONFIDENCE - Trust visual search data\n"
            else:
                if product['enhanced_name']:
                    prompt += f"SerpAPI Alternative: {product['enhanced_name']} (confidence: {product['serp_confidence']:.2f})\n"
                prompt += f"📍 ORIGINAL SOURCE TRUSTED - High-quality source data\n"
            
            if product['top_serp_titles']:
                prompt += f"SerpAPI Context: {product['top_serp_titles']}\n"
            
            if product['source_url']:
                prompt += f"URL Context: {product['source_url']}\n"
            
            prompt += "\n"
        
        prompt += f"""
CRITICAL INSTRUCTIONS:
1. The system has ALREADY selected the best name source - respect this decision
2. For HIGH-QUALITY sources (original selected): Extract precisely, high confidence
3. For LOW-QUALITY sources (SerpAPI selected): Clean thoroughly, moderate confidence  
4. Preserve specific model identifiers (numbers, collection names)
5. Don't lose important details due to over-cleaning

EXPECTED OUTPUT - JSON with {len(batch_data)} products:
{{
  "products": [
    {{
      "product_id": "id",
      "brand": "brand", 
      "collaborator": "",
      "model": "specific model with preserved identifiers",
      "colorway": "colorway",
      "canonical_name": "Brand Specific Model Colorway",
      "confidence": 0.90,
      "reasoning": "High-quality source with specific model extraction",
      "data_source": "intelligent_selection"
    }}
  ]
}}

REMEMBER: 
- StockX "Samba LT Core Black" > generic "Adidas Sneaker"
- Preserve "7555 Hamptons" when found in any source
- Higher confidence for sources the system already validated"""
        
        return prompt

    def _validate_results_with_source_context(self, parsed_results: List[Dict], batch_data: List[Dict]) -> List[Dict]:
        """Enhanced validation using intelligent source selection context"""
        validated_results = []
        
        for i, (result, original_data) in enumerate(zip(parsed_results, batch_data)):
            selected_source = original_data.get('selected_source', 'original')
            source_domain = original_data.get('source_domain', 'unknown')
            confidence_modifier = original_data.get('confidence_modifier', 0.0)
            
            # Adjust confidence based on source selection quality
            if 'confidence' in result:
                base_confidence = result['confidence']
                
                # Boost confidence for good source selections
                if selected_source == 'serpapi' and source_domain in ['therealreal.com']:
                    # SerpAPI correctly selected for low-quality source
                    result['confidence'] = min(0.95, base_confidence + 0.1)
                elif selected_source == 'original' and source_domain in ['stockx.com', 'rebag.com']:
                    # Original correctly selected for high-quality source
                    result['confidence'] = min(0.95, base_confidence + 0.15)
                
                # Add general confidence modifier
                result['confidence'] = min(0.95, result['confidence'] + confidence_modifier)
            
            # Ensure model extraction captured important identifiers from selected source
            result = self._ensure_source_identifiers_preserved(result, original_data)
            
            # Set data source for tracking
            result['data_source'] = f"intelligent_selection_{selected_source}"
            result['source_domain'] = source_domain
            
            validated_results.append(result)
        
        return validated_results

    def _ensure_source_identifiers_preserved(self, result: Dict, original_data: Dict) -> Dict:
        """Ensure important identifiers from the selected source are preserved"""
        best_name = original_data.get('best_name', '')
        selected_source = original_data.get('selected_source', 'original')
        
        # Extract any model identifiers that might have been missed
        identifiers = []
        
        # Model numbers (especially important for luxury items)
        model_numbers = re.findall(r'\b\d{4,5}\b', best_name)
        identifiers.extend(model_numbers)
        
        # Collection names (luxury brands)
        collection_patterns = [
            r'\b(Hamptons?|Neverfull|Speedy|Capucines|Artsy|Galliera|Alma|Keepall)\b',
            r'\b(Soho|Jackie|Bamboo|Dionysus|Marmont|Ophidia)\b',
            r'\b(Twist|Coussin|Petite Malle|OnTheGo|Samba|Gazelle|Stan Smith)\b'
        ]
        
        for pattern in collection_patterns:
            matches = re.findall(pattern, best_name, re.IGNORECASE)
            identifiers.extend(matches)
        
        # Size descriptors that are model-specific
        size_terms = re.findall(r'\b(Mini|Small|Medium|Large|PM|MM|GM|LT)\b', best_name, re.IGNORECASE)
        identifiers.extend(size_terms)
        
        # Check if these are in the AI result
        ai_model = result.get('model', '')
        ai_canonical = result.get('canonical_name', '')
        
        missing_identifiers = []
        for identifier in identifiers:
            if identifier.lower() not in ai_model.lower() and identifier.lower() not in ai_canonical.lower():
                missing_identifiers.append(identifier)
        
        if missing_identifiers:
            logger.debug(f"Adding missing identifiers from {selected_source} source: {missing_identifiers}")
            
            # Add to model if not too long
            if len(ai_model) + len(' '.join(missing_identifiers)) < 50:
                result['model'] = f"{ai_model} {' '.join(missing_identifiers)}".strip()
            
            # Update canonical name
            canonical_parts = result.get('canonical_name', '').split()
            canonical_parts.extend(missing_identifiers)
            result['canonical_name'] = ' '.join(canonical_parts)
            
            # Update reasoning
            result['reasoning'] = f"{result.get('reasoning', '')} + {selected_source} identifiers preserved"
        
        return result

    def _clean_json_response_robust(self, content: str) -> str:
        """Robust JSON cleaning for Claude responses with better truncation handling"""
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
            
            # Step 3: Handle truncated responses more aggressively
            if '...' in cleaned or '"reasoning": "' in cleaned and not cleaned.count('"reasoning"') == cleaned.count('"data_source"'):
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
            
            # Step 4: Final cleanup
            cleaned = re.sub(r',\s*}', '}', cleaned)
            cleaned = re.sub(r',\s*]', ']', cleaned)
            
            # Remove extra closing brackets at the end
            if cleaned.endswith('}]}'):
                cleaned = cleaned[:-2]
            elif cleaned.endswith(']}...'):
                cleaned = cleaned[:-5] + '}'
            
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
        """Create minimal valid JSON from truncated response by extracting complete products"""
        try:
            # Extract all complete product objects using regex
            product_pattern = r'"product_id":\s*"([^"]+)"[^}]*?"brand":\s*"([^"]*)"[^}]*?"model":\s*"([^"]*)"'
            matches = re.findall(product_pattern, content, re.DOTALL)
            
            if not matches:
                logger.warning("No product patterns found, returning empty structure")
                return '{"products": []}'
            
            # Build minimal valid products
            products = []
            for match in matches:
                product_id, brand, model = match
                
                # Try to extract additional fields if they exist in the content
                collaborator = ""
                colorway = ""
                canonical_name = f"{brand} {model}".strip()
                
                # Look for these fields near the product_id
                product_section_start = content.find(f'"product_id": "{product_id}"')
                if product_section_start != -1:
                    # Look for the next product or end of content
                    next_product = content.find('"product_id":', product_section_start + 1)
                    if next_product == -1:
                        product_section = content[product_section_start:]
                    else:
                        product_section = content[product_section_start:next_product]
                    
                    # Extract fields from this section
                    collab_match = re.search(r'"collaborator":\s*"([^"]*)"', product_section)
                    if collab_match:
                        collaborator = collab_match.group(1)
                    
                    colorway_match = re.search(r'"colorway":\s*"([^"]*)"', product_section)
                    if colorway_match:
                        colorway = colorway_match.group(1)
                    
                    canonical_match = re.search(r'"canonical_name":\s*"([^"]*)"', product_section)
                    if canonical_match:
                        canonical_name = canonical_match.group(1)
                
                product = {
                    "product_id": product_id,
                    "brand": brand,
                    "collaborator": collaborator,
                    "model": model,
                    "colorway": colorway,
                    "canonical_name": canonical_name,
                    "confidence": 0.7,
                    "reasoning": "Recovered from truncated JSON response",
                    "data_source": "truncated_recovery"
                }
                products.append(product)
            
            # Create valid JSON structure
            result = {"products": products}
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"Error creating minimal valid JSON: {e}")
            return '{"products": []}'

    def _repair_truncated_json(self, content: str, start_pos: int) -> str:
        """Legacy repair function - now redirects to minimal JSON creation"""
        return self._create_minimal_valid_json(content, start_pos)

    def _final_json_repair(self, content: str) -> str:
        """Legacy final repair function - now redirects to minimal JSON creation"""
        return self._create_minimal_valid_json(content, 0)

    def _extract_partial_results(self, content: str, batch_data: List[Dict]) -> List[Dict]:
        """Extract partial results from malformed JSON"""
        try:
            results = []
            
            # Pattern to match product objects
            product_pattern = r'"product_id":\s*"([^"]+)"[^}]*?"brand":\s*"([^"]*)"[^}]*?"model":\s*"([^"]*)"[^}]*?"canonical_name":\s*"([^"]*)"'
            matches = re.findall(product_pattern, content, re.DOTALL)
            
            for match in matches:
                product_id, brand, model, canonical_name = match
                results.append({
                    'product_id': product_id,
                    'brand': brand,
                    'collaborator': '',
                    'model': model,
                    'colorway': '',
                    'canonical_name': canonical_name if canonical_name else f"{brand} {model}".strip(),
                    'confidence': 0.7,
                    'reasoning': 'Recovered from malformed JSON',
                    'data_source': 'recovered'
                })
            
            # Pad with fallbacks if needed
            while len(results) < len(batch_data):
                missing_idx = len(results)
                fallback = self._create_intelligent_fallback(batch_data[missing_idx])
                results.append(fallback)
            
            return results[:len(batch_data)]
            
        except Exception as e:
            logger.error(f"Error extracting partial results: {e}")
            return []

    def _create_intelligent_fallback(self, product_data: Dict) -> Dict:
        """Create fallback result that considers intelligent source selection"""
        # Use the intelligently selected best name
        best_name = product_data.get('best_name', '')
        original_name = product_data.get('original_name', '')
        brand = product_data.get('brand', '')
        selected_source = product_data.get('selected_source', 'original')
        source_domain = product_data.get('source_domain', 'unknown')
        
        # Use best name for model extraction
        source_name = best_name if best_name else original_name
        
        # Simple model extraction
        model = product_data.get('current_model', '')
        if not model and source_name:
            # Remove brand and extract meaningful parts
            model_part = source_name
            if brand:
                model_part = re.sub(re.escape(brand), '', source_name, flags=re.IGNORECASE).strip()
            
            # Extract first few meaningful words
            words = model_part.split()[:3]
            model = ' '.join(words) if words else 'Unknown Model'
        
        # Adjust confidence based on source selection
        if selected_source == 'serpapi' and source_domain in ['therealreal.com']:
            confidence = 0.6  # SerpAPI helped clean up poor source
        elif selected_source == 'original' and source_domain in ['stockx.com', 'rebag.com']:
            confidence = 0.8  # High-quality original source
        else:
            confidence = 0.5  # Default
        
        data_source = f'intelligent_fallback_{selected_source}'
        
        return {
            'product_id': product_data['product_id'],
            'brand': brand,
            'collaborator': '',
            'model': model,
            'colorway': '',
            'canonical_name': f"{brand} {model}".strip(),
            'confidence': confidence,
            'reasoning': f'Fallback extraction from {data_source}',
            'data_source': data_source,
            'source_domain': source_domain
        }

    def _create_fallback_results(self, batch_data: List[Dict]) -> List[Dict]:
        """Create fallback results when AI parsing fails"""
        fallback_results = []
        for product in batch_data:
            fallback_results.append(self._create_intelligent_fallback(product))
        return fallback_results

    def _validate_and_fix_results(self, parsed_results: List[Dict], batch_data: List[Dict]) -> List[Dict]:
        """Validate and fix parsed results with source context"""
        try:
            # Ensure we have the right number of results
            while len(parsed_results) < len(batch_data):
                missing_idx = len(parsed_results)
                fallback = self._create_intelligent_fallback(batch_data[missing_idx])
                parsed_results.append(fallback)
            
            # Fix any missing or malformed fields
            for i, result in enumerate(parsed_results):
                if not result.get('product_id'):
                    result['product_id'] = batch_data[i]['product_id']
                if not result.get('brand'):
                    result['brand'] = batch_data[i]['brand']
                if not result.get('model'):
                    result['model'] = batch_data[i]['current_model']
                if not result.get('canonical_name'):
                    result['canonical_name'] = f"{result['brand']} {result['model']}".strip()
                if not result.get('confidence'):
                    # Set confidence based on source selection
                    source_domain = batch_data[i].get('source_domain', 'unknown')
                    selected_source = batch_data[i].get('selected_source', 'original')
                    
                    if selected_source == 'original' and source_domain in ['stockx.com', 'rebag.com']:
                        result['confidence'] = 0.85
                    elif selected_source == 'serpapi' and source_domain in ['therealreal.com']:
                        result['confidence'] = 0.75
                    else:
                        result['confidence'] = 0.7
                
                if not result.get('reasoning'):
                    result['reasoning'] = f'AI processed with intelligent source selection ({batch_data[i].get("selected_source", "unknown")})'
                if not result.get('data_source'):
                    result['data_source'] = f'intelligent_selection_{batch_data[i].get("selected_source", "unknown")}'
                
                # Ensure required fields exist
                result.setdefault('collaborator', '')
                result.setdefault('colorway', '')
                result.setdefault('source_domain', batch_data[i].get('source_domain', 'unknown'))
            
            return parsed_results[:len(batch_data)]
            
        except Exception as e:
            logger.error(f"Error validating results: {e}")
            return self._create_fallback_results(batch_data)