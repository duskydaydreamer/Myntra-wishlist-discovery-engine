import os
import json
import time
import httpx
from dotenv import load_dotenv

EVAL_RECORDS_FILE = "data/phase3a_eval_records_v2.json"
EVAL_RESULTS_FILE = "data/phase3a_remaining_results.json"
TELEMETRY_FILE = "data/extraction_telemetry.json"

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
        
        # Mappings
        field_map = {
            "m": "is_myntra_specific",
            "js": "journey_stage",
            "wi": "wishlist_intent",
            "pi": "purchase_intent",
            "pc": "product_category",
            "t": "theme",
            "pb": "primary_barrier",
            "sb": "secondary_barriers",
            "rc": "root_cause",
            "u": "uncertainty",
            "inf": "information_needed",
            "wa": "workaround",
            "ep": "external_platform_used",
            "ac": "alternative_considered",
            "o": "occasion",
            "do": "decision_outcome",
            "ss": "segment_signal"
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
        "prompt_version": "v2-compact-phase3a",
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
    
    start = time.time()
    try:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        lat = time.time() - start
        
        data = resp.json()
        usage = data.get("usageMetadata", {})
        text_out = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text_out)
        
        p = usage.get("promptTokenCount", 0)
        c = usage.get("candidatesTokenCount", 0)
        t = usage.get("totalTokenCount", 0)
        th = usage.get("thoughtsTokenCount", 0)
        
        create_telemetry_entry(batch_id, len(batch), p, c, th, t, lat, True, 0)
        return parsed, usage, lat, None
    except Exception as e:
        lat = time.time() - start
        create_telemetry_entry(batch_id, len(batch), 0, 0, 0, 0, lat, False, 0)
        try:
            err_details = resp.text
        except:
            err_details = str(e)
        return None, {}, lat, f"{str(e)} - {err_details}"

def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"
    
    with open(EVAL_RECORDS_FILE, "r") as f:
        all_records = json.load(f)
        
    smoke_test_indices = {0, 10, 25}
    remaining_records = [r for idx, r in enumerate(all_records) if idx not in smoke_test_indices]
    
    print(f"Total initial records: {len(all_records)}")
    print(f"Smoke test records excluded: {len(smoke_test_indices)}")
    print(f"Remaining records to process: {len(remaining_records)}")
    
    compact_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "i": {"type": "integer"},
                "m": {"type": "boolean"},
                "js": {"type": "string", "enum": ["DI", "EV", "PU", "PP", "?"]},
                "wi": {"type": "string", "enum": ["GP", "PT", "CS", "IN", "BM", "AS", "OP", "?"]},
                "pi": {"type": "string", "enum": ["HI", "LO", "NO", "?"]},
                "pc": {"type": "string"},
                "t": {"type": "string"},
                "pb": {"type": "string", "enum": ["PR", "QU", "FI", "DE", "TR", "?"]},
                "sb": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["PR", "QU", "FI", "DE", "TR", "?"]}
                },
                "rc": {"type": "string"},
                "u": {"type": "string"},
                "inf": {"type": "string"},
                "wa": {"type": "string"},
                "ep": {"type": "string"},
                "ac": {"type": "string"},
                "o": {"type": "string"},
                "do": {"type": "string", "enum": ["AB", "BO", "DE", "SW", "?"]},
                "ss": {"type": "string"},
                "q": {"type": "string"}
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
    
    chunks = []
    chunk_sizes = [10, 10, 10, 10, 7]
    idx = 0
    for size in chunk_sizes:
        if idx < len(remaining_records):
            chunks.append(remaining_records[idx:idx+size])
            idx += size
            
    all_results = []
    stats = {"p": 0, "c": 0, "th": 0, "tot": 0, "reqs": 0, "failures": 0, "err": ""}
    
    print("Starting processing remaining 47 records...")
    
    with httpx.Client(timeout=90.0) as client:
        for batch_idx, batch in enumerate(chunks):
            batch_id = f"remaining_batch_{batch_idx}"
            print(f"Processing {batch_id} (size {len(batch)})...")
            
            parsed, usage, lat, err = extract_batch(client, url, system_instruction, compact_schema, batch, batch_id)
            stats["reqs"] += 1
            
            if err:
                print(f"Error on {batch_id}: {err}")
                stats["failures"] += 1
                stats["err"] = err
                break # Hard stop on quota/timeout error
                
            if parsed:
                stats["p"] += usage.get("promptTokenCount", 0)
                stats["c"] += usage.get("candidatesTokenCount", 0)
                stats["tot"] += usage.get("totalTokenCount", 0)
                stats["th"] += usage.get("thoughtsTokenCount", 0)
                
                valid_in_batch = 0
                for obs in parsed:
                    local_idx = obs.get("i")
                    if local_idx is None or local_idx < 0 or local_idx >= len(batch): 
                        continue
                    
                    orig_record = batch[local_idx]
                    
                    try:
                        expanded = expand_observation(obs, orig_record["cleaned_text"])
                        
                        final_res = {
                            "source_record_id": orig_record["cleaned_record_id"],
                            "original_text": orig_record["cleaned_text"],
                            "extracted": expanded
                        }
                        all_results.append(final_res)
                        valid_in_batch += 1
                    except Exception as e:
                        print(f"Expansion error in {batch_id}: {e}")
                        continue
                        
                print(f"Extracted {valid_in_batch} valid observations from {batch_id} (lat: {lat:.2f}s)")
            
            time.sleep(5)
            
    with open(EVAL_RESULTS_FILE, "w") as f:
        json.dump(all_results, f, indent=2)
        
    print(f"Finished. Extracted {len(all_results)} total valid observations.")
    print(f"Total requests: {stats['reqs']}")
    print(f"Total Tokens: {stats['tot']} (Prompt: {stats['p']}, Candidates: {stats['c']})")
    print(f"Total Failures: {stats['failures']}")

if __name__ == "__main__":
    main()
