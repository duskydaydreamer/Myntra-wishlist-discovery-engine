import asyncio
import json
import os
import sys

# Add backend to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from backend.api.routers.query import execute_query, QueryRequest
from backend.api.dependencies import async_session

QUESTIONS = [
    "How many observations mention fit and sizing?",
    "Why do high intent users abandon their wishlists?",
    "What prevents users from purchasing clothing items?",
    "What are the main trust issues with Myntra's delivery?",
    "Why do users add items to their wishlist just for comparison?",
    "What workarounds do shoppers use when they are unsure about the fabric?"
]

async def run_eval():
    print("=" * 60)
    print("PHASE 5 TASK 5.2.1 — Query Engine Evaluation")
    print("=" * 60)
    
    results = []
    
    async with async_session() as db:
        for q in QUESTIONS:
            print(f"\nProcessing query: '{q}'...")
            req = QueryRequest(query=q)
            try:
                response = await execute_query(req, db)
                print(f"  - Intent: {response.research_intent}")
                print(f"  - Type: {response.query_type}")
                print(f"  - Filters applied: {response.filters_applied}")
                print(f"  - Evidence count: {response.evidence_count}")
                print(f"  - Answer preview: {response.answer[:150]}...")
                
                results.append({
                    "question": q,
                    "response": response.model_dump()
                })
            except Exception as e:
                print(f"  - ERROR: {e}")
                
    output_path = os.path.join(BASE_DIR, "data", "phase5_query_eval.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
        
    print(f"\nEvaluation complete. Results saved to {output_path}")

if __name__ == "__main__":
    asyncio.run(run_eval())
