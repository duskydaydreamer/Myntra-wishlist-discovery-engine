import asyncio
import json
import os
import sys
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["HF_HUB_OFFLINE"] = "1"

# Load environment variables from .env
load_dotenv()

from fastapi.testclient import TestClient
from backend.api.main import app
import time

client = TestClient(app)

questions = [
    # E. DELIVERY / RETURNS
    "What delivery or return friction do users describe?",
    # F. COMPARISON BEHAVIOR
    "How do shoppers compare products before deciding?",
    # G. EXTERNAL RESEARCH
    "How do users research products outside Myntra before buying?",
    # H. PREDEFINED THEME
    "What do users say about App Navigation & Filters?",
    # I. EMERGENT CLUSTER
    "Why do shoppers hesitate to buy shoes online?",
    # J. SOURCE FILTER
    "What fit-related evidence comes from YouTube?",
    # K. PURCHASE-INTENT FILTER
    "What barriers appear among high-purchase-intent observations?",
    # L. JOURNEY / OUTCOME QUERY
    "What are the pain points during checkout?",
    # M. DETERMINISTIC COUNT QUERY
    "How many observations mention fit?",
    # N. DETERMINISTIC PERCENTAGE QUERY
    "What percentage of the evidence has price as the primary barrier?",
    # O. EXPLICIT FILTER WITH NO RESULT
    "What sizing problems do Reddit users report?",
    # P. AMBIGUOUS EXPLORATORY QUERY
    "Tell me something interesting about users.",
    # Q. SOLUTION-SEEKING QUERY
    "What feature should Myntra build?"
]

results = []

for q in questions:
    print(f"Executing: {q}")
    start = time.time()
    res = client.post("/api/query", json={"query": q})
    dur = time.time() - start
    
    if res.status_code == 200:
        data = res.json()
        if data.get("answer") and "An error occurred" in data.get("answer"):
            results.append({
                "question": q,
                "status": "FAIL: RATE_LIMIT",
                "error": data.get("answer"),
                "time": dur
            })
            print("Rate limit hit! Stopping benchmark.")
            break
            
        results.append({
            "question": q,
            "status": "PASS",
            "query_type": data.get("query_type"),
            "retrieval_mode": data.get("retrieval_mode"),
            "applied_filters": data.get("applied_filters"),
            "evidence_count": data.get("evidence_count"),
            "unique_source_count": data.get("unique_source_count", 0),
            "eligible_subset_size": data.get("eligible_subset_size", 0),
            "answer": data.get("answer"),
            "time": dur
        })
    else:
        results.append({
            "question": q,
            "status": f"FAIL: {res.status_code}",
            "error": res.text,
            "time": dur
        })
    with open(os.path.join(os.path.dirname(__file__), "benchmark_results.json"), "w") as f:
        json.dump(results, f, indent=2)
    time.sleep(4) # Rate limit protection

print("Benchmark complete!")

print("Benchmark complete!")
