import os
import json
import sqlite3
import random
import time
import asyncio
import httpx
from datetime import datetime
from dotenv import load_dotenv

CACHE_FILE = "data/phase2_calibration_cache.json"
REPORT_FILE = "data/phase2_calibration_report_v2.txt"

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

class RateLimiter:
    def __init__(self, target_rpm=12):
        self.interval = 60.0 / target_rpm
        self.last_request_time = 0.0
        self.lock = asyncio.Lock()

    async def wait(self):
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_request_time
            if elapsed < self.interval:
                await asyncio.sleep(self.interval - elapsed)
            self.last_request_time = time.time()

async def process_record(client, generate_url, system_instruction, classification_schema, rec, stats_dict, cache, rate_limiter):
    rec_id = rec["cleaned_record_id"]
    if rec_id in cache:
        cached_result = cache[rec_id]
        if cached_result.get("success"):
            stats_dict["success"] += 1
            # Add tokens from cache if they exist
            usage = cached_result.get("usage", {})
            stats_dict["in_tokens"] += usage.get("promptTokenCount", 0)
            stats_dict["out_tokens"] += usage.get("candidatesTokenCount", 0)
            stats_dict["total_tokens"] += usage.get("totalTokenCount", 0)
            return (rec, cached_result["parsed"])

    text = rec["cleaned_text"]
    stats_dict["attempted"] += 1
    
    payload = {
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        },
        "contents": [{
            "parts": [{"text": f"Classify this text:\n\n{text}"}]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "responseSchema": classification_schema
        }
    }
    headers = {'Content-Type': 'application/json'}
    
    max_retries = 3
    base_backoff = 15.0
    
    for attempt in range(max_retries + 1):
        await rate_limiter.wait()
        stats_dict["requests"] += 1
        try:
            resp = await client.post(generate_url, json=payload, headers=headers)
            
            if resp.status_code == 429:
                stats_dict["rate_limit_responses"] += 1
                if attempt < max_retries:
                    stats_dict["retries"] += 1
                    retry_after = resp.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        sleep_time = int(retry_after) + 2
                    else:
                        sleep_time = base_backoff * (2 ** attempt) + random.uniform(0, 2)
                    print(f"429 hit. Sleeping for {sleep_time:.2f}s...", flush=True)
                    await asyncio.sleep(sleep_time)
                    continue
                else:
                    resp.raise_for_status()

            resp.raise_for_status()
            data = resp.json()
            
            usage = data.get("usageMetadata", {})
            stats_dict["in_tokens"] += usage.get("promptTokenCount", 0)
            stats_dict["out_tokens"] += usage.get("candidatesTokenCount", 0)
            stats_dict["total_tokens"] += usage.get("totalTokenCount", 0)
            
            text_out = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(text_out)
            if "relevance_label" not in parsed or "signals_detected" not in parsed:
                raise ValueError("Missing required fields")
            if parsed["relevance_label"] not in ["highly_relevant", "somewhat_relevant", "not_relevant"]:
                raise ValueError("Invalid enum for relevance_label")
                
            stats_dict["success"] += 1
            
            cache[rec_id] = {
                "success": True,
                "parsed": parsed,
                "usage": usage
            }
            save_cache(cache)
            return (rec, parsed)
            
        except Exception as e:
            if attempt < max_retries:
                stats_dict["retries"] += 1
                sleep_time = base_backoff * (2 ** attempt) + random.uniform(0, 2)
                print(f"Error {e}. Retrying in {sleep_time:.2f}s...", flush=True)
                await asyncio.sleep(sleep_time)
            else:
                stats_dict["failed"] += 1
                cache[rec_id] = {
                    "success": False,
                    "error": str(e)
                }
                save_cache(cache)
                return (rec, None)

async def main_async():
    print("STEP 1 — LOAD CONFIG", flush=True)
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env")
        exit(1)
        
    target_model = "models/gemini-3.7-flash"
    
    print("\nSTEP 2 — CREATE STRATIFIED CALIBRATION SAMPLE", flush=True)
    db_path = "data/discovery_pulse.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    query = """
        SELECT c.cleaned_record_id, c.cleaned_text, r.source, r.rating, r.published_at
        FROM cleaned_records c
        JOIN raw_records r ON c.raw_record_id = r.raw_record_id
        WHERE c.is_duplicate = 0 AND c.is_spam = 0 
          AND c.cleaning_flags NOT LIKE '%skipped%'
    """
    
    candidates = conn.execute(query).fetchall()
    
    source_buckets = {"reddit": [], "app_store": [], "play_store": [], "youtube": []}
    for c in candidates:
        src = c["source"]
        if src in source_buckets:
            source_buckets[src].append(dict(c))
            
    print(f"Total eligible candidates: {len(candidates)}", flush=True)
    for src, items in source_buckets.items():
        print(f"  {src}: {len(items)}")
        
    random.seed(42)
    sample = []
    
    allocations = {
        "reddit": min(40, len(source_buckets["reddit"])),
        "app_store": min(40, len(source_buckets["app_store"])),
        "play_store": 290,
        "youtube": 130
    }
    
    for src, count in allocations.items():
        chosen = random.sample(source_buckets[src], count)
        sample.extend(chosen)
        
    print(f"Stratified sample size: {len(sample)}")
    for src, count in allocations.items():
        print(f"  {src} sampled: {count}")

    print("\nSTEP 3 & 4 — RUN GEMINI CLASSIFICATION", flush=True)
    
    system_instruction = """
    You are an expert consumer insights analyst classifying user evidence for a fashion e-commerce discovery project.
    
    The research objective is to identify evidence relevant to:
    - wishlist behavior
    - product shortlisting
    - purchase hesitation
    - fit/size uncertainty
    - product quality concerns
    - comparison shopping
    - price/timing hesitation
    - review/trust issues
    - styling uncertainty
    - occasion suitability
    - external research/workarounds
    - returns/exchange concerns
    - purchase postponement or abandonment
    - other meaningful shopping-decision evidence
    
    Do not use generic sentiment as relevance.
    """
    
    classification_schema = {
        "type": "object",
        "properties": {
            "relevance_label": {
                "type": "string",
                "enum": ["highly_relevant", "somewhat_relevant", "not_relevant"]
            },
            "signals_detected": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": ["relevance_label", "signals_detected"]
    }
    
    stats = {
        "attempted": 0,
        "success": 0,
        "failed": 0,
        "rate_limit_responses": 0,
        "retries": 0,
        "requests": 0,
        "in_tokens": 0,
        "out_tokens": 0,
        "total_tokens": 0,
        "time_elapsed": 0.0
    }
    
    cache = load_cache()
    rate_limiter = RateLimiter(target_rpm=12)
    generate_url = f"https://generativelanguage.googleapis.com/v1beta/{target_model}:generateContent?key={api_key}"
    
    start_time = time.time()
    
    results = []
    
    # We will use bounded concurrency (e.g., 3 tasks max) to allow parallel progress if there's no sleep,
    # but the rate_limiter strictly enforces max RPM across all tasks.
    sem = asyncio.Semaphore(3)
    
    async def task_wrapper(client, rec):
        async with sem:
            return await process_record(client, generate_url, system_instruction, classification_schema, rec, stats, cache, rate_limiter)

    print("Starting process... This will take ~40 minutes.", flush=True)
    async with httpx.AsyncClient(timeout=60.0) as client:
        tasks = [task_wrapper(client, rec) for rec in sample]
        results = await asyncio.gather(*tasks)

    stats["time_elapsed"] = time.time() - start_time
    
    print(f"\nProcessing complete in {stats['time_elapsed']/60:.2f} minutes.", flush=True)
    print("\nSTEP 6 — QUALITY REPORT", flush=True)
    
    sources = {}
    ratings = {}
    relevance_counts = {"highly_relevant": 0, "somewhat_relevant": 0, "not_relevant": 0}
    
    examples = {"highly_relevant": [], "somewhat_relevant": [], "not_relevant": []}
    
    for rec, out in results:
        src = rec["source"]
        sources[src] = sources.get(src, 0) + 1
        
        rt = rec["rating"]
        if rt is not None:
            ratings[rt] = ratings.get(rt, 0) + 1
            
        if out is not None:
            lbl = out["relevance_label"]
            relevance_counts[lbl] += 1
            if len(examples[lbl]) < 10:
                examples[lbl].append((rec, out))
                
    if stats["success"] > 0:
        avg_in = stats["in_tokens"] / stats["success"]
        avg_out = stats["out_tokens"] / stats["success"]
        avg_total = stats["total_tokens"] / stats["success"]
    else:
        avg_in = avg_out = avg_total = 0
        
    est_tokens_full = avg_total * len(candidates)
    
    def format_examples(ex_list):
        return json.dumps([{"source": r["source"], "text": r["cleaned_text"], "label": o["relevance_label"], "signals": o["signals_detected"]} for r, o in ex_list], indent=2)
    
    report = f"""
======================================================
CALIBRATION REPORT V2
======================================================
1. Exact model used: {target_model}

2. Sample size: 500
3. Sampling method: Stratified Deterministic (seed 42)
4. Source distribution (Sample): {sources}
5. Rating distribution (Sample): {ratings}

6. Relevance distribution:
   - highly_relevant: {relevance_counts['highly_relevant']}
   - somewhat_relevant: {relevance_counts['somewhat_relevant']}
   - not_relevant: {relevance_counts['not_relevant']}

7. API & Usage Stats:
   - Attempted: {stats['attempted']} (Includes {len([1 for v in cache.values() if v.get('success')])} from cache)
   - Successful: {stats['success']}
   - Failed: {stats['failed']}
   - API Requests Made (new): {stats['requests']}
   - Rate-Limit Responses (429): {stats['rate_limit_responses']}
   - Retries: {stats['retries']}
   - Input tokens (successful only): {stats['in_tokens']}
   - Output tokens (successful only): {stats['out_tokens']}
   - Total tokens (successful only): {stats['total_tokens']}

8. Averages (per successful classification):
   - Avg Input tokens: {avg_in:.2f}
   - Avg Output tokens: {avg_out:.2f}
   - Avg Total tokens: {avg_total:.2f}

9. Extrapolation:
   - Total Candidates: {len(candidates)}
   - Estimated total tokens for full dataset: {est_tokens_full:,.0f}

---
EXAMPLES 
---
Highly Relevant (up to 10):
{format_examples(examples['highly_relevant'])}

Somewhat Relevant (up to 10):
{format_examples(examples['somewhat_relevant'])}

Not Relevant (up to 10):
{format_examples(examples['not_relevant'])}
"""

    with open(REPORT_FILE, "w") as f:
        f.write(report)
        
    print(f"\nCalibration report written to {REPORT_FILE}", flush=True)

if __name__ == "__main__":
    asyncio.run(main_async())
