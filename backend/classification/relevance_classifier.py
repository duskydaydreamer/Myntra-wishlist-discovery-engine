import os
import json
from typing import Dict, Any, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from groq import AsyncGroq
except ImportError:
    AsyncGroq = None

class RelevanceClassifier:
    def __init__(self, confidence_threshold: float = 0.70):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = AsyncGroq(api_key=self.api_key) if AsyncGroq and self.api_key else None
        self.model_name = "openai/gpt-oss-120b"
        self.confidence_threshold = confidence_threshold
        
        # Load prompt
        prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', 'relevance_v1.txt')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.system_prompt = f.read()
            
        # Embedding model for pre-filter
        self.embed_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Seed texts for pre-filtering (very basic examples)
        self.irrelevant_seeds = [
            "App keeps crashing during payment",
            "I cannot login to my account",
            "Customer care is the worst, they don't pick up",
            "Please update the app, it is very slow",
            "Money deducted but order not placed"
        ]
        self.irrelevant_embeddings = self.embed_model.encode(self.irrelevant_seeds)

        # Embeddings are no longer strictly needed for pre-filter, but we keep the setup
        pass

    def deterministic_prefilter(self, text: str) -> Tuple[str, str]:
        """
        Returns (status, reason). Status is 'kept' or 'skipped'.
        """
        import re
        
        if not text or not text.strip():
            return "skipped", "empty_or_whitespace"
            
        t = text.lower()
        
        # 1. URL-only check
        # Very basic check: if it looks like a bare URL
        if re.match(r'^https?://\S+$', text.strip()):
            return "skipped", "url_only"
            
        # 2. Emoji-only / Symbol-only check
        # Remove all emojis and non-alphanumeric (excluding space) to see if any real text remains
        emoji_pattern = re.compile("[\U00010000-\U0010ffff]", flags=re.UNICODE)
        text_without_emojis = emoji_pattern.sub('', text)
        alphanum_only = re.sub(r'[^a-zA-Z0-9]', '', text_without_emojis)
        
        if not alphanum_only:
            return "skipped", "emoji_or_symbol_only"
            
        # 3. App Technical Only signals
        tech_keywords = [
            "crash", "login", "otp", "loading", "slow", "bug", "stuck", "update", "screen",
            "app is not working", "uninstall"
        ]
        
        # 4. Shopping Signals (high value)
        shopping_keywords = [
            "wishlist", "saved", "liked", "cart",
            "buy", "purchase", "order", "returned", "exchange", "refund",
            "size", "fit", "sizing", "tight", "loose",
            "quality", "fabric", "material", "cloth",
            "price", "discount", "expensive", "sale", "cheap", "cost",
            "review", "rating", "trust", "fake", "original",
            "delivery", "delay", "shipping",
            "compare", "confused", "doubt", "worth",
            "brand", "outfit", "occasion", "wedding", "party", "styling", "look", "color", "colour",
            "ajio", "amazon", "flipkart", "meesho", "myntra"
        ]
        
        has_shopping = any(w in t for w in shopping_keywords)
        has_tech = any(w in t for w in tech_keywords)
        
        # Determine status
        if has_shopping:
            return "kept", "shopping_signal_detected"
            
        if has_tech:
            return "skipped", "app_technical_only"
            
        # If it's very short and has no shopping/tech signals, it's likely generic ("nice", "good app")
        words = text.strip().split()
        if len(words) < 5:
            # We skip generic very short texts with NO shopping signals
            return "skipped", "generic_short_low_info"
            
        # Default fallback: favor recall, keep it for LLM classification
        return "kept", "fallback_kept"

    async def classify(self, text: str) -> Dict[str, Any]:
        """
        Returns a dictionary with label, confidence, and signals_detected.
        (Note: the caller should only call this if deterministic_prefilter returned 'kept')
        """
            
        # 2. LLM Classification
        if not self.client:
            # Fallback
            return {
                "label": "somewhat_relevant",
                "confidence": 0.5,
                "signals_detected": []
            }
            
        retries = 5
        import asyncio
        for attempt in range(retries + 1):
            try:
                chat_completion = await self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": text}
                    ],
                    model=self.model_name,
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                
                response_text = chat_completion.choices[0].message.content
                result = json.loads(response_text)
                
                # Validate schema
                label = result.get("label", "not_relevant")
                confidence = float(result.get("confidence", 0.0))
                signals = result.get("signals_detected", [])
                
                if label not in ["highly_relevant", "somewhat_relevant", "not_relevant"]:
                    label = "not_relevant"
                    
                return {
                    "label": label,
                    "confidence": confidence,
                    "signals_detected": signals
                }
            except Exception as e:
                if '429' in str(e) or 'rate_limit' in str(e).lower():
                    if attempt < retries:
                        await asyncio.sleep(4 + (attempt * 2))
                        continue
                if attempt == retries:
                    print(f"Classification failed after retries: {e}")
                    return {
                        "label": "not_relevant",
                        "confidence": 0.0,
                        "signals_detected": [],
                        "error": str(e)
                    }
