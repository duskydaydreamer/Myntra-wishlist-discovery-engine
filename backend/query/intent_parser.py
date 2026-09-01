import json
import os
import httpx
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, ".env"))

OLLAMA_ENDPOINT = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

INTENT_PROMPT = """
You are an expert natural language query parser for an e-commerce research system.
A Product Manager is asking a question about user behavior, specifically around why users add items to their wishlist but don't buy them.

Extract the research intent and any implied filters from their question.

Valid fields for implied_filters are:
- source (e.g., "Play Store", "App Store", "YouTube", "Reddit")
- wishlist_intent (e.g., "bookmarking", "price_tracking", "comparison_shortlist")
- purchase_intent (e.g., "high", "medium", "low")
- primary_barrier (one of "price", "trust", "fit", "quality", "delivery")
- journey_stage (e.g., "discovery", "evaluation", "purchase", "post_purchase")
- decision_outcome (e.g., "delayed", "abandoned", "bought", "switched")

You must classify the query into one of two types:
1. "count_filter": The user is asking for a deterministic count, percentage, or list of filters (e.g., "How many...", "What percentage...").
2. "evidence_explanatory": The user is asking for explanations, reasons, or evidence (e.g., "Why do users...", "What workarounds...").

Return ONLY valid JSON matching this schema:
{
  "query_type": "count_filter" | "evidence_explanatory",
  "research_intent": "Brief description of what the user is trying to learn",
  "implied_filters": {
    "field_name": ["value1", "value2"]
  }
}

User Question: {question}
"""

async def parse_intent(question: str) -> dict:
    q_lower = question.lower().strip()
    implied_filters = {}
    
    # 1. Deterministic source extraction
    if "play store" in q_lower:
        implied_filters["source"] = ["play_store"]
    elif "app store" in q_lower:
        implied_filters["source"] = ["app_store"]
    elif "youtube" in q_lower:
        implied_filters["source"] = ["youtube"]
    elif "reddit" in q_lower:
        implied_filters["source"] = ["reddit"]
        
    # 2. Deterministic barrier extraction
    if "price" in q_lower or "expensive" in q_lower:
        implied_filters["primary_barrier"] = ["price"]
    elif "trust" in q_lower or "fake" in q_lower:
        implied_filters["primary_barrier"] = ["trust"]
    elif "fit" in q_lower or "sizing" in q_lower or "size" in q_lower:
        implied_filters["primary_barrier"] = ["fit", "fit_and_sizing"]
    elif "quality" in q_lower or "fabric" in q_lower:
        implied_filters["primary_barrier"] = ["quality"]
    elif "delivery" in q_lower or "shipping" in q_lower:
        implied_filters["primary_barrier"] = ["delivery"]

    # 3. Deterministic outcome extraction
    if "delayed" in q_lower:
        implied_filters["decision_outcome"] = ["delayed"]
    elif "abandoned" in q_lower:
        implied_filters["decision_outcome"] = ["abandoned"]
        
    # 4. Intent Classification
    if q_lower.startswith("how many") or q_lower.startswith("what percentage"):
        return {
            "query_type": "count_filter",
            "research_intent": "Deterministic Count Query",
            "implied_filters": implied_filters
        }
    elif q_lower.startswith("why") or q_lower.startswith("what") or q_lower.startswith("how"):
        return {
            "query_type": "evidence_explanatory",
            "research_intent": "Explanatory Research Inquiry",
            "implied_filters": implied_filters
        }

    # If it's a completely unsupported language structure, attempt Ollama fallback
    prompt = INTENT_PROMPT.replace("{question}", question)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{OLLAMA_ENDPOINT}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.0
                    }
                }
            )
            response.raise_for_status()
            result = response.json()
            return json.loads(result.get("response", "{}"))
    except Exception as e:
        print(f"Error parsing intent with Ollama: {e}")
        # Safe fallback: Unfiltered explanatory request
        return {
            "query_type": "evidence_explanatory",
            "research_intent": "General inquiry",
            "implied_filters": {}
        }

