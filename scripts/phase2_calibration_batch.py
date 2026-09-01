import os
import json
import sqlite3
import random
import time
import httpx
from dotenv import load_dotenv

CACHE_FILE = "data/phase2_calibration_cache.json"
REPORT_FILE = "data/phase2_calibration_report_batch.txt"

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

def generate_sample():
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
    candidates = [dict(row) for row in conn.execute(query).fetchall()]
    conn.close()
    
    source_buckets = {"reddit": [], "app_store": [], "play_store": [], "youtube": []}
    for c in candidates:
        src = c["source"]
        if src in source_buckets:
            source_buckets[src].append(c)
            
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
    return candidates, sample

def process_batch(client, generate_url, system_instruction, batch_records):
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
    
    headers = {'Content-Type': 'application/json'}
    try:
        resp = client.post(generate_url, json=payload, headers=headers, timeout=60.0)
        if resp.status_code == 429:
            print("429 Too Many Requests hit.")
            return None, None, True
        resp.raise_for_status()
        
        data = resp.json()
        usage = data.get("usageMetadata", {})
        text_out = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text_out)
        return parsed, usage, False
    except Exception as e:
        print(f"Request failed: {e}")
        return None, None, False

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

def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env")
        exit(1)
        
    target_model = "models/gemini-3.5-flash-lite"
    generate_url = f"https://generativelanguage.googleapis.com/v1beta/{target_model}:generateContent?key={api_key}"
    
    candidates, sample = generate_sample()
    cache = load_cache()
    
    pending = [r for r in sample if r["cleaned_record_id"] not in cache]
    print(f"Total sample: {len(sample)}, Cached: {len(sample)-len(pending)}, Pending: {len(pending)}")
    
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
        "failures": 0
    }
    
    current_batch_size = 25
    tested_25 = False
    tested_50 = False
    
    start_time = time.time()
    
    with httpx.Client(timeout=120.0) as client:
        while pending:
            if not tested_25:
                batch_size = 25
            elif not tested_50:
                batch_size = 50
            else:
                batch_size = current_batch_size
                
            batch = pending[:batch_size]
            expected_ids = [r["cleaned_record_id"] for r in batch]
            print(f"\nProcessing batch of {len(batch)} records...")
            
            parsed, usage, is_429 = process_batch(client, generate_url, system_instruction, batch)
            stats["requests"] += 1
            
            if is_429:
                print("429 hit. Sleeping for 15s...")
                time.sleep(15)
                stats["retries"] += 1
                continue
                
            is_valid, msg = False, "No parsed data"
            if parsed is not None:
                is_valid, msg = validate_batch(parsed, expected_ids)
                
            if not is_valid:
                print(f"Batch validation failed: {msg}")
                stats["failed_batches"] += 1
                stats["retries"] += 1
                
                print("Retrying batch once...")
                time.sleep(5)
                parsed, usage, is_429 = process_batch(client, generate_url, system_instruction, batch)
                stats["requests"] += 1
                
                is_valid2 = False
                if parsed is not None:
                    is_valid2, msg2 = validate_batch(parsed, expected_ids)
                
                if not is_valid2:
                    print(f"Retry also failed: {msg2}. Marking batch as failed in cache.")
                    for r in batch:
                        cache[r["cleaned_record_id"]] = {"success": False, "error": "Malformed output after retry"}
                        stats["failures"] += 1
                    save_cache(cache)
                    pending = pending[batch_size:]
                    if batch_size == 50:
                        current_batch_size = 25
                        tested_50 = True
                    else:
                        tested_25 = True
                    continue
            
            if is_valid:
                print(f"Batch valid! Caching {len(parsed)} records.")
                stats["in_tokens"] += usage.get("promptTokenCount", 0)
                stats["out_tokens"] += usage.get("candidatesTokenCount", 0)
                stats["total_tokens"] += usage.get("totalTokenCount", 0)
                
                for item in parsed:
                    rec_id = item["record_id"]
                    cache[rec_id] = {
                        "success": True,
                        "parsed": {
                            "relevance_label": item["relevance_label"],
                            "signals_detected": item["signals_detected"]
                        }
                    }
                save_cache(cache)
                pending = pending[batch_size:]
                
                if batch_size == 25 and not tested_25:
                    tested_25 = True
                    print("25-record batch passed successfully.")
                elif batch_size == 50 and not tested_50:
                    tested_50 = True
                    current_batch_size = 50
                    print("50-record batch passed successfully. Adopting 50 records/request.")
                    
            # Safe backoff (targeting 12 RPM -> 1 request every 5s)
            time.sleep(5.5)
            
    elapsed = time.time() - start_time
                
    # Generate report
    print("\nSTEP 6 — QUALITY REPORT", flush=True)
    
    sources = {}
    relevance_counts = {"highly_relevant": 0, "somewhat_relevant": 0, "not_relevant": 0}
    
    completed_sample = []
    failed_sample = []
    
    for r in sample:
        rec_id = r["cleaned_record_id"]
        if rec_id in cache:
            if cache[rec_id].get("success"):
                out = cache[rec_id]["parsed"]
                completed_sample.append((r, out))
                
                src = r["source"]
                sources[src] = sources.get(src, 0) + 1
                
                lbl = out["relevance_label"]
                relevance_counts[lbl] += 1
            else:
                failed_sample.append(r)

    avg_in = stats["in_tokens"] / len(completed_sample) if completed_sample else 0
    avg_out = stats["out_tokens"] / len(completed_sample) if completed_sample else 0
    avg_total = stats["total_tokens"] / len(completed_sample) if completed_sample else 0
    
    report = f"""
======================================================
CALIBRATION REPORT V4 (gemini-3.5-flash-lite BATCHED)
======================================================
1. Exact model used: {target_model}

2. Sample size: 500
   - Successfully Completed: {len(completed_sample)}
   - Failed: {len(failed_sample)}
   
3. Source distribution (Completed): {sources}

4. Relevance distribution:
   - highly_relevant: {relevance_counts['highly_relevant']}
   - somewhat_relevant: {relevance_counts['somewhat_relevant']}
   - not_relevant: {relevance_counts['not_relevant']}

5. API & Usage Stats:
   - API Requests Made: {stats['requests']}
   - Failed Batches (Malformed): {stats['failed_batches']}
   - Retries: {stats['retries']}
   - Total Failures (Records): {stats['failures']}
   - Input tokens: {stats['in_tokens']} (Avg: {avg_in:.1f}/record)
   - Output tokens: {stats['out_tokens']} (Avg: {avg_out:.1f}/record)
   - Total tokens: {stats['total_tokens']} (Avg: {avg_total:.1f}/record)
   - Elapsed Time: {elapsed:.2f} seconds
"""
    with open(REPORT_FILE, "w") as f:
        f.write(report)
        
    print(f"\nCalibration report written to {REPORT_FILE}", flush=True)

if __name__ == "__main__":
    main()
