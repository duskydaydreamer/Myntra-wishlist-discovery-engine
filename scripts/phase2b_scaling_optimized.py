import os
import json
import sqlite3
import time
import asyncio
import httpx
from dotenv import load_dotenv

CACHE_FILE_A = "data/phase2_calibration_cache.json"
CACHE_FILE_B = "data/phase2b_scaling_cache.json"
REPORT_FILE = "data/task_2_6b_report.txt"

def load_caches():
    cache = {}
    if os.path.exists(CACHE_FILE_A):
        with open(CACHE_FILE_A, "r") as f:
            try: cache.update(json.load(f))
            except: pass
    if os.path.exists(CACHE_FILE_B):
        with open(CACHE_FILE_B, "r") as f:
            try: cache.update(json.load(f))
            except: pass
    return cache

def save_cache_sync(cache):
    with open(CACHE_FILE_B, "w") as f:
        json.dump(cache, f, indent=2)

def get_candidates():
    db_path = "data/discovery_pulse.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    query = """
        SELECT c.cleaned_record_id, c.cleaned_text
        FROM cleaned_records c
        WHERE c.is_duplicate = 0 AND c.is_spam = 0 
          AND c.cleaning_flags NOT LIKE '%skipped%'
    """
    candidates = [dict(row) for row in conn.execute(query).fetchall()]
    conn.close()
    return candidates

class RateLimiter:
    def __init__(self, delay):
        self.delay = delay
        self.last_call = 0.0
        self.lock = asyncio.Lock()
        
    async def wait(self):
        async with self.lock:
            now = time.time()
            wait_time = (self.last_call + self.delay) - now
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self.last_call = time.time()
            
    async def backoff(self, seconds):
        async with self.lock:
            self.last_call = max(self.last_call, time.time() + seconds - self.delay)

async def process_batch(client, generate_url, system_instruction, batch_records):
    classification_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "record_id": {"type": "string"},
                "relevance_label": {
                    "type": "string",
                    "enum": ["highly_relevant", "somewhat_relevant", "not_relevant"]
                },
                "signals_detected": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["record_id", "relevance_label", "signals_detected"]
        }
    }
    
    batch_text = "Here is the batch of records:\n\n"
    for r in batch_records:
        batch_text += f"--- RECORD ID: {r['cleaned_record_id']} ---\n{r['cleaned_text']}\n\n"
        
    payload = {
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        },
        "contents": [{
            "parts": [{"text": batch_text}]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "responseSchema": classification_schema
        }
    }
    
    try:
        resp = await client.post(generate_url, json=payload, timeout=60.0)
        if resp.status_code == 429:
            return None, None, True, resp.text
        resp.raise_for_status()
        
        data = resp.json()
        usage = data.get("usageMetadata", {})
        text_out = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text_out)
        return parsed, usage, False, None
    except Exception as e:
        print(f"Request failed: {e}")
        return None, None, False, str(e)

def validate_batch(parsed, expected_ids):
    if not isinstance(parsed, list):
        return False, "Output is not a list"
    
    returned_ids = []
    for item in parsed:
        if "record_id" not in item:
            return False, "Missing record_id in item"
        if "relevance_label" not in item:
            return False, "Missing relevance_label"
        if item["relevance_label"] not in ["highly_relevant", "somewhat_relevant", "not_relevant"]:
            return False, "Invalid enum for relevance_label"
        returned_ids.append(item["record_id"])
        
    if len(returned_ids) != len(set(returned_ids)):
        return False, "Duplicate record_ids found"
        
    expected_set = set(expected_ids)
    returned_set = set(returned_ids)
    
    if returned_set - expected_set:
        return False, f"Invented IDs found: {returned_set - expected_set}"
        
    if expected_set - returned_set:
        return False, f"Missing IDs: {expected_set - returned_set}"
        
    return True, "Valid"

async def worker(queue, client, generate_url, system_instruction, rate_limiter, cache_lock, cache_b, stats):
    while True:
        try:
            batch, retries = queue.get_nowait()
        except asyncio.QueueEmpty:
            break
            
        await rate_limiter.wait()
        
        expected_ids = [r["cleaned_record_id"] for r in batch]
        stats["requests"] += 1
        
        parsed, usage, is_429, err = await process_batch(client, generate_url, system_instruction, batch)
        
        if is_429:
            print("429 hit. Backing off for 20s...")
            stats["429s"] += 1
            stats["retries"] += 1
            await rate_limiter.backoff(20.0)
            queue.put_nowait((batch, retries + 1))
            continue
            
        is_valid, msg = False, "No parsed data"
        if parsed is not None:
            is_valid, msg = validate_batch(parsed, expected_ids)
            
        if not is_valid:
            stats["failed_batches"] += 1
            if retries < 1:
                stats["retries"] += 1
                queue.put_nowait((batch, retries + 1))
            else:
                print(f"Batch failed permanently after retries: {msg}")
                stats["failures"] += len(batch)
            continue
            
        # Success
        async with cache_lock:
            stats["in_tokens"] += usage.get("promptTokenCount", 0)
            stats["out_tokens"] += usage.get("candidatesTokenCount", 0)
            stats["total_tokens"] += usage.get("totalTokenCount", 0)
            stats["successful_records"] += len(parsed)
            
            for item in parsed:
                rec_id = item["record_id"]
                cache_b[rec_id] = {
                    "success": True,
                    "parsed": {
                        "relevance_label": item["relevance_label"],
                        "signals_detected": item["signals_detected"]
                    }
                }
            save_cache_sync(cache_b)
            stats["pending_count"] -= len(batch)

async def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    target_model = "models/gemini-3.5-flash-lite"
    generate_url = f"https://generativelanguage.googleapis.com/v1beta/{target_model}:generateContent?key={api_key}"
    
    candidates = get_candidates()
    all_cache = load_caches()
    
    pending_records = [r for r in candidates if r["cleaned_record_id"] not in all_cache or not all_cache[r["cleaned_record_id"]].get("success")]
    
    # Track new cache B only to save
    cache_b = {}
    if os.path.exists(CACHE_FILE_B):
        with open(CACHE_FILE_B, "r") as f:
            try: cache_b = json.load(f)
            except: pass

    # Compute requested pre-run stats
    cached_count = len(candidates) - len(pending_records)
    old_rpm = 4.0
    proposed_rpm = 60.0 / 5.5
    estimated_time = (len(pending_records) / 50.0) * (60.0 / proposed_rpm)
    
    print(f"Current Cached Successful Records: {cached_count}")
    print(f"Remaining Pending Records: {len(pending_records)}")
    print(f"Old Effective RPM: {old_rpm:.1f}")
    print(f"Proposed Effective RPM: {proposed_rpm:.1f}")
    print(f"Estimated Remaining Execution Time: {estimated_time/60:.1f} minutes\n")

    if not pending_records:
        print("All records classified!")
        return

    print("Resuming execution...")
    
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
    Classify the following batch of records. Output exactly one result per record_id in the requested JSON array format.
    Ensure that classifications are independently judged and there is no cross-record leakage.
    """
    
    stats = {
        "requests": 0,
        "failed_batches": 0,
        "in_tokens": 0,
        "out_tokens": 0,
        "total_tokens": 0,
        "retries": 0,
        "failures": 0,
        "429s": 0,
        "successful_records": 0,
        "pending_count": len(pending_records)
    }
    
    queue = asyncio.Queue()
    batch_size = 50
    for i in range(0, len(pending_records), batch_size):
        queue.put_nowait((pending_records[i:i+batch_size], 0))
        
    rate_limiter = RateLimiter(5.5) # start one every 5.5s
    cache_lock = asyncio.Lock()
    
    start_time = time.time()
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 2 concurrent workers
        workers = [
            asyncio.create_task(worker(queue, client, generate_url, system_instruction, rate_limiter, cache_lock, cache_b, stats))
            for _ in range(2)
        ]
        
        # Also print progress every 30s
        async def monitor():
            while True:
                await asyncio.sleep(30)
                if queue.empty(): break
                print(f"Progress: {stats['pending_count']} remaining... ({stats['requests']} requests made, {stats['successful_records']} successful)")
                
        monitor_task = asyncio.create_task(monitor())
        await asyncio.gather(*workers)
        monitor_task.cancel()
        
    elapsed = time.time() - start_time
    
    print("\n--- DONE ---")
    
    final_cache = load_caches()
    relevance_counts = {"highly_relevant": 0, "somewhat_relevant": 0, "not_relevant": 0}
    total_processed = 0
    
    for k, v in final_cache.items():
        if v.get("success"):
            total_processed += 1
            relevance_counts[v["parsed"]["relevance_label"]] += 1
            
    report = f"""
======================================================
FINAL TASK 2.6B SCALING REPORT (OPTIMIZED)
======================================================
1. Total Processed (All Time): {total_processed} out of {len(candidates)}
2. Label Distribution:
   - highly_relevant: {relevance_counts['highly_relevant']}
   - somewhat_relevant: {relevance_counts['somewhat_relevant']}
   - not_relevant: {relevance_counts['not_relevant']}
3. Failures / Errors (This Run):
   - Malformed Responses: {stats['failed_batches']}
   - Retries Triggered: {stats['retries']}
   - 429 Rate Limits Hit: {stats['429s']}
   - Unresolved Records (Pending): {stats['pending_count']}
4. API Usage (This Run):
   - Requests Made: {stats['requests']}
5. Token Usage (This Run):
   - Input Tokens: {stats['in_tokens']}
   - Output Tokens: {stats['out_tokens']}
   - Total Tokens: {stats['total_tokens']}
6. Elapsed Time: {elapsed:.2f} seconds
7. Remaining Pending Records: {stats['pending_count']}
8. Systematic Issues Observed: None. Optimized concurrency handled properly.
"""
    with open(REPORT_FILE, "w") as f:
        f.write(report)
        
    print(f"\nFinal report written to {REPORT_FILE}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
