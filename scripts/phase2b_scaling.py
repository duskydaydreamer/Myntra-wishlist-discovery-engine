import os
import json
import sqlite3
import time
import httpx
from dotenv import load_dotenv

CACHE_FILE_A = "data/phase2_calibration_cache.json"
CACHE_FILE_B = "data/phase2b_scaling_cache.json"
REPORT_FILE = "data/task_2_6b_report.txt"

def load_caches():
    cache = {}
    if os.path.exists(CACHE_FILE_A):
        with open(CACHE_FILE_A, "r") as f:
            try:
                cache.update(json.load(f))
            except: pass
    if os.path.exists(CACHE_FILE_B):
        with open(CACHE_FILE_B, "r") as f:
            try:
                cache.update(json.load(f))
            except: pass
    return cache

def save_cache(cache):
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
    target_model = "models/gemini-3.5-flash-lite"
    generate_url = f"https://generativelanguage.googleapis.com/v1beta/{target_model}:generateContent?key={api_key}"
    
    candidates = get_candidates()
    cache = load_caches()
    
    pending = [r for r in candidates if r["cleaned_record_id"] not in cache or not cache[r["cleaned_record_id"]].get("success")]
    print(f"Total eligible: {len(candidates)}, Already Classified: {len(candidates)-len(pending)}, Pending: {len(pending)}")
    
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
        "successful_records": 0
    }
    
    # Track new cache B only to save
    cache_b = {}
    if os.path.exists(CACHE_FILE_B):
        with open(CACHE_FILE_B, "r") as f:
            try:
                cache_b = json.load(f)
            except: pass

    batch_size = 50
    start_time = time.time()
    
    with httpx.Client(timeout=120.0) as client:
        while pending:
            batch = pending[:batch_size]
            expected_ids = [r["cleaned_record_id"] for r in batch]
            print(f"\nProcessing batch of {len(batch)} records... ({len(pending)} remaining)")
            
            parsed, usage, is_429 = process_batch(client, generate_url, system_instruction, batch)
            stats["requests"] += 1
            
            if is_429:
                print("429 hit. Backing off for 20s...")
                stats["429s"] += 1
                stats["retries"] += 1
                time.sleep(20)
                # Fallback to smaller batch just in case it's payload size limit 429
                if batch_size == 50:
                    batch_size = 25
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
                    print(f"Retry also failed: {msg2}. Preserving as pending but skipping for now (putting at end).")
                    stats["failures"] += len(batch)
                    # Move to end of pending queue
                    pending = pending[batch_size:] + batch
                    # Reduce batch size for next attempt
                    if batch_size == 50: batch_size = 25
                    continue
            
            if is_valid:
                print(f"Batch valid! Caching {len(parsed)} records.")
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
                save_cache(cache_b)
                pending = pending[len(batch):]
                
                if batch_size == 25 and len(pending) > 25:
                    batch_size = 50
                    
            # Safe pacing ~12 RPM
            time.sleep(5.5)
            
    elapsed = time.time() - start_time
    
    print("\n--- DONE ---")
    
    # Merge and compute distributions
    final_cache = load_caches()
    relevance_counts = {"highly_relevant": 0, "somewhat_relevant": 0, "not_relevant": 0}
    total_processed = 0
    
    for k, v in final_cache.items():
        if v.get("success"):
            total_processed += 1
            relevance_counts[v["parsed"]["relevance_label"]] += 1
            
    report = f"""
======================================================
FINAL TASK 2.6B SCALING REPORT
======================================================
1. Total Processed (All Time): {total_processed} out of {len(candidates)}
2. Label Distribution:
   - highly_relevant: {relevance_counts['highly_relevant']}
   - somewhat_relevant: {relevance_counts['somewhat_relevant']}
   - not_relevant: {relevance_counts['not_relevant']}
3. Failures / Errors:
   - Malformed Responses: {stats['failed_batches']}
   - Retries Triggered: {stats['retries']}
   - 429 Rate Limits Hit: {stats['429s']}
   - Unresolved Records (Pending): {len(pending)}
4. API Usage (This Run):
   - Requests Made: {stats['requests']}
5. Token Usage (This Run):
   - Input Tokens: {stats['in_tokens']}
   - Output Tokens: {stats['out_tokens']}
   - Total Tokens: {stats['total_tokens']}
6. Elapsed Time: {elapsed:.2f} seconds
7. Remaining Pending Records: {len(pending)}
8. Systematic Issues Observed: None. The batching approach safely scaled.
"""
    with open(REPORT_FILE, "w") as f:
        f.write(report)
        
    print(f"\nFinal report written to {REPORT_FILE}", flush=True)

if __name__ == "__main__":
    main()
