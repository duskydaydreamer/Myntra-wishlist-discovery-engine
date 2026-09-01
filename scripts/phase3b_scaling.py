import os
import json
import time
import httpx
import sqlite3
import uuid
from datetime import datetime
from dotenv import load_dotenv

DB_FILE = "data/discovery_pulse.db"
EVAL_RESULTS_FILE = "data/phase3a_remaining_results.json"
TELEMETRY_FILE = "data/extraction_telemetry.json"
RUN_ID = "run_" + str(int(time.time()))
RUN_FILE = f"data/observations/{RUN_ID}.jsonl"
CACHE_FILE = "data/phase3b_extraction_cache.json"

def expand_enum(field, code):
    if code == "?": return "unknown"
    if not code: return "unknown"
    
    mappings = {
        "journey_stage": {"DI": "discovery", "EV": "evaluation", "PU": "purchase", "PP": "post_purchase"},
        "wishlist_intent": {"GP": "genuine_purchase", "PT": "price_tracking", "CS": "comparison_shortlist", 
                            "IN": "inspiration", "BM": "bookmarking", "AS": "aspirational_saving", "OP": "occasion_planning"},
        "purchase_intent": {"HI": "high", "LO": "low", "NO": "none"},
        "primary_barrier": {"PR": "price", "QU": "quality", "FI": "fit", "DE": "delivery", "TR": "trust"},
        "decision_outcome": {"AB": "abandoned", "BO": "bought", "DE": "delayed", "SW": "switched"},
        "secondary_barriers": {"PR": "price", "QU": "quality", "FI": "fit", "DE": "delivery", "TR": "trust"}
    }
    
    if field in mappings:
        if code not in mappings[field]:
            raise ValueError(f"Invalid compact code '{code}' for field '{field}'")
        return mappings[field][code]
    return code

def expand_observation(obs, original_text):
    if "i" not in obs or "q" not in obs:
        raise ValueError("Missing required field 'i' or 'q'")
        
    quote = obs["q"]
    if quote != "?" and quote not in original_text:
        raise ValueError(f"Evidence quote not found in text: {quote}")
        
    expanded = {"local_index": obs["i"], "evidence_quote": quote}
    for k, v in obs.items():
        if k in ["i", "q"]: continue
        
        field_map = {
            "m": "is_myntra_specific", "js": "journey_stage", "wi": "wishlist_intent",
            "pi": "purchase_intent", "pc": "product_category", "t": "theme",
            "pb": "primary_barrier", "sb": "secondary_barriers", "rc": "root_cause",
            "u": "uncertainty", "inf": "information_needed", "wa": "workaround",
            "ep": "external_platform_used", "ac": "alternative_considered",
            "o": "occasion", "do": "decision_outcome", "ss": "segment_signal"
        }
        
        full_field = field_map.get(k, k)
        
        if k == "sb" and isinstance(v, list):
            expanded[full_field] = [expand_enum(full_field, code) for code in v]
        elif k in ["js", "wi", "pi", "pb", "do"]:
            expanded[full_field] = expand_enum(full_field, v)
        else:
            expanded[full_field] = "unknown" if v == "?" else v
            
    return expanded

def create_telemetry_entry(batch_id, records, prompt, cand, thoughts, total, lat, succ, retries):
    entry = {
        "timestamp": time.time(),
        "provider": "google",
        "model": "gemini-3.6-flash",
        "prompt_version": "v2-compact-phase3b",
        "batch_id": batch_id,
        "records_in_request": records,
        "promptTokenCount": prompt,
        "candidatesTokenCount": cand,
        "thoughtsTokenCount": thoughts,
        "totalTokenCount": total,
        "latency": lat,
        "success": succ,
        "retry_count": retries
    }
    try:
        with open(TELEMETRY_FILE, "r") as f: data = json.load(f)
    except:
        data = []
    data.append(entry)
    with open(TELEMETRY_FILE, "w") as f: json.dump(data, f, indent=2)
    return entry

def extract_batch(client, url, system_instruction, compact_schema, batch, batch_id):
    mapped_batch = [{"i": i, "text": r["cleaned_text"]} for i, r in enumerate(batch)]
    
    payload = {
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"parts": [{"text": json.dumps(mapped_batch)}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "responseSchema": compact_schema,
            "thinkingConfig": {"thinkingLevel": "LOW"}
        }
    }
    
    retries = 0
    max_retries = 3
    
    while retries <= max_retries:
        start = time.time()
        try:
            resp = client.post(url, json=payload)
            lat = time.time() - start
            
            if resp.status_code == 429:
                create_telemetry_entry(batch_id, len(batch), 0, 0, 0, 0, lat, False, retries)
                return None, {}, lat, f"HTTP 429 Quota Exhausted"
                
            if resp.status_code == 503 and retries < max_retries:
                retries += 1
                time.sleep((2 ** retries) * 2)
                continue
                
            resp.raise_for_status()
            data = resp.json()
            usage = data.get("usageMetadata", {})
            text_out = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(text_out)
            
            p = usage.get("promptTokenCount", 0)
            c = usage.get("candidatesTokenCount", 0)
            t = usage.get("totalTokenCount", 0)
            th = usage.get("thoughtsTokenCount", 0)
            
            create_telemetry_entry(batch_id, len(batch), p, c, th, t, lat, True, retries)
            return parsed, usage, lat, None
        except Exception as e:
            lat = time.time() - start
            try: err_details = resp.text
            except: err_details = str(e)
            if retries < max_retries and not "429" in str(e):
                retries += 1
                time.sleep((2 ** retries) * 2)
                continue
            create_telemetry_entry(batch_id, len(batch), 0, 0, 0, 0, lat, False, retries)
            return None, {}, lat, f"{str(e)} - {err_details}"
            
    return None, {}, 0, "Max retries exceeded"

def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"
    
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT c.cleaned_record_id, c.cleaned_text, r.raw_record_id, r.source, r.source_url
        FROM classified_records cr
        JOIN cleaned_records c ON cr.cleaned_record_id = c.cleaned_record_id
        JOIN raw_records r ON c.raw_record_id = r.raw_record_id
        WHERE cr.relevance_label IN ('highly_relevant', 'somewhat_relevant')
        AND c.is_spam = 0 AND c.is_duplicate = 0
    """)
    relevant_records = [dict(row) for row in cursor.fetchall()]
    print(f"Total eligible relevant records: {len(relevant_records)}")
    
    try:
        with open(CACHE_FILE, "r") as f:
            extraction_cache = json.load(f)
    except:
        extraction_cache = {}
        
    cursor.execute("SELECT DISTINCT cleaned_record_id FROM observations")
    already_in_db = {row[0] for row in cursor.fetchall()}
    
    processed_ids = set(extraction_cache.keys()).union(already_in_db)
    remaining_records = [r for r in relevant_records if r["cleaned_record_id"] not in processed_ids]
    
    print(f"Already processed: {len(processed_ids)}")
    print(f"Remaining to process: {len(remaining_records)}")
    
    compact_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "i": {"type": "integer"}, "m": {"type": "boolean"},
                "js": {"type": "string", "enum": ["DI", "EV", "PU", "PP", "?"]},
                "wi": {"type": "string", "enum": ["GP", "PT", "CS", "IN", "BM", "AS", "OP", "?"]},
                "pi": {"type": "string", "enum": ["HI", "LO", "NO", "?"]},
                "pc": {"type": "string"}, "t": {"type": "string"},
                "pb": {"type": "string", "enum": ["PR", "QU", "FI", "DE", "TR", "?"]},
                "sb": {"type": "array", "items": {"type": "string", "enum": ["PR", "QU", "FI", "DE", "TR", "?"]}},
                "rc": {"type": "string"}, "u": {"type": "string"},
                "inf": {"type": "string"}, "wa": {"type": "string"},
                "ep": {"type": "string"}, "ac": {"type": "string"},
                "o": {"type": "string"},
                "do": {"type": "string", "enum": ["AB", "BO", "DE", "SW", "?"]},
                "ss": {"type": "string"}, "q": {"type": "string"}
            },
            "required": ["i", "q", "js", "wi", "pi", "pb", "do"]
        }
    }
    
    system_instruction = """
    Extract structured observations. Return an array of JSON objects.
    Each input record has an integer 'i'. Return multiple objects if multiple insights exist.
    Use '?' for unknown/unsupported values.
    
    Compact Keys:
    i = local index (integer, MUST match input)
    m = is_myntra_specific (boolean)
    js = journey_stage (DI=discovery, EV=evaluation, PU=purchase, PP=post_purchase)
    wi = wishlist_intent (GP=genuine_purchase, PT=price_tracking, CS=comparison_shortlist, IN=inspiration, BM=bookmarking, AS=aspirational_saving, OP=occasion_planning)
    pi = purchase_intent (HI=high, LO=low, NO=none)
    pc = product_category
    t = theme
    pb = primary_barrier (PR=price, QU=quality, FI=fit, DE=delivery, TR=trust)
    sb = secondary_barriers (array of short codes)
    rc = root_cause (free text)
    u = uncertainty (free text)
    inf = information_needed (free text)
    wa = workaround (free text)
    ep = external_platform_used
    ac = alternative_considered
    o = occasion
    do = decision_outcome (AB=abandoned, BO=bought, DE=delayed, SW=switched)
    ss = segment_signal
    q = evidence_quote (MUST be a verbatim substring of the input text)
    
    'q' must be an exact substring. Never invent quotes. Use compact enum codes for fixed taxonomies.
    """
    
    batch_size = 10
    chunks = [remaining_records[i:i+batch_size] for i in range(0, len(remaining_records), batch_size)]
    
    # FOR TESTING TO AVOID QUOTA EXHAUSTION: only process 5 batches MAX for now if requested, but let's just let it run until 429
    # The requirement says "Process only records genuinely requiring... Stop only if HTTP 429".
    # I will process everything it can.
    
    os.makedirs("data/observations", exist_ok=True)
    run_file = open(RUN_FILE, "a")
    
    with httpx.Client(timeout=90.0) as client:
        for batch_idx, batch in enumerate(chunks):
            batch_id = f"phase3b_batch_{batch_idx}_{int(time.time())}"
            print(f"Processing {batch_id} (size {len(batch)})...")
            
            parsed, usage, lat, err = extract_batch(client, url, system_instruction, compact_schema, batch, batch_id)
            
            if err:
                print(f"Error on {batch_id}: {err}")
                if "429" in err:
                    print("HTTP 429 Quota Exhausted. Stopping immediately.")
                    break
                else:
                    for r in batch:
                        extraction_cache[r["cleaned_record_id"]] = "unresolved_retryable"
                    continue
            
            if parsed is not None:
                valid_obs_for_db = []
                records_with_obs = set()
                
                for obs in parsed:
                    local_idx = obs.get("i")
                    if local_idx is None or local_idx < 0 or local_idx >= len(batch): 
                        continue
                    orig_record = batch[local_idx]
                    try:
                        expanded = expand_observation(obs, orig_record["cleaned_text"])
                        records_with_obs.add(orig_record["cleaned_record_id"])
                        
                        obs_id = uuid.uuid4().hex
                        db_obs = {
                            "observation_id": obs_id,
                            "source_record_id": orig_record["raw_record_id"],
                            "cleaned_record_id": orig_record["cleaned_record_id"],
                            "source": orig_record["source"],
                            "source_url": orig_record["source_url"],
                            "evidence_quote": expanded["evidence_quote"],
                            "extracted_at": datetime.utcnow().isoformat(),
                            "model_id": "gemini-3.6-flash",
                            "prompt_version": "v2-compact-phase3b",
                            "created_in_pipeline_run_id": RUN_ID,
                        }
                        
                        for k, v in expanded.items():
                            if k not in ["evidence_quote", "local_index"]:
                                if isinstance(v, list): v = json.dumps(v)
                                db_obs[k] = v
                                
                        valid_obs_for_db.append(db_obs)
                        run_file.write(json.dumps(db_obs) + "\n")
                    except Exception as e:
                        print(f"Expansion error in {batch_id}: {e}")
                        continue
                
                if valid_obs_for_db:
                    cols = list(valid_obs_for_db[0].keys())
                    sql = f"INSERT INTO observations ({','.join(cols)}) VALUES ({','.join(['?' for _ in cols])})"
                    for o in valid_obs_for_db:
                        cursor.execute(sql, [o[c] for c in cols])
                    conn.commit()
                
                for r in batch:
                    if r["cleaned_record_id"] in records_with_obs:
                        extraction_cache[r["cleaned_record_id"]] = "successfully_extracted"
                    else:
                        extraction_cache[r["cleaned_record_id"]] = "successfully_processed_zero_observations"
                        
                with open(CACHE_FILE, "w") as f:
                    json.dump(extraction_cache, f)
            
            time.sleep(1.0)
            
    run_file.close()
    conn.close()
    print("Batch processing finished.")

if __name__ == "__main__":
    main()
