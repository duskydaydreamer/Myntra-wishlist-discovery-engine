import os
import json
from typing import Tuple, List

# Make sure to run `pip install groq`
try:
    from groq import AsyncGroq
except ImportError:
    AsyncGroq = None

class SpamFilter:
    def __init__(self, min_length: int = 10):
        self.min_length = min_length
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = AsyncGroq(api_key=self.api_key) if AsyncGroq and self.api_key else None
        self.model = "openai/gpt-oss-120b"
        
        self.system_prompt = """
You are a content quality filter for a fashion e-commerce research project.
Analyze the following user review/comment and classify it into one of these categories:
- "spam": gibberish, malicious links, completely irrelevant nonsense.
- "advertisement": promoting other apps, services, or products with referral codes or explicit marketing.
- "content_free": purely emojis, single words like "nice", "good", "bad", or text that carries absolutely no meaning or context.
- "keep": any review that describes an experience, problem, question, or opinion related to shopping, fashion, or app usage. Even if it is short, negative, informal, or grammatically incorrect, classify as "keep" if it has ANY meaning.

Respond ONLY with a JSON object in the following format:
{"label": "spam|advertisement|content_free|keep"}
"""

    async def filter_record(self, text: str) -> Tuple[bool, List[str]]:
        """
        Returns (is_spam, cleaning_flags)
        """
        if not text or not text.strip():
            return True, ["content_free"]
            
        # Heuristic
        if len(text.strip()) < self.min_length:
            return True, ["content_free", "heuristic_short"]
            
        # LLM Classification bypassed for token efficiency in Phase 2
        # Relying on min_length heuristic and downstream deterministic pre-filter
        return False, []
