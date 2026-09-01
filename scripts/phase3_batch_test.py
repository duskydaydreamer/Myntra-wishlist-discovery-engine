import os
import json
import time
import httpx
import sqlite3
from dotenv import load_dotenv

DB_FILE = "data/discovery_pulse.db"
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

def run_batch_test(batch_size=50):
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
    
    with open(CACHE_FILE, "r") as f:
        extraction_cache = json.load(f)
        
    remaining_records = [r for r in relevant_records if extraction_cache.get(r["cleaned_record_id"]) == "unresolved_retryable"]
    batch = remaining_records[:batch_size]
    
    if len(batch) < batch_size:
        print(f"Not enough records for batch size {batch_size}. Exiting.")
        return
        
    compact_schema = {
        "type": "array", "items": {
            "type": "object", "properties": {
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
    
    print(f"Submitting Batch {batch_size} to gemini-3.6-flash...")
    start_time = time.time()
    with httpx.Client(timeout=120.0) as client:
        try:
            resp = client.post(url, json=payload)
            lat = time.time() - start_time
            print(f"HTTP {resp.status_code} in {lat:.2f}s")
            if resp.status_code != 200:
                print(f"Error Body: {resp.text}")
                return
            
            data = resp.json()
            usage = data.get("usageMetadata", {})
            text_out = data["candidates"][0]["content"]["parts"][0]["text"]
            
            print(f"\nTokens: Prompt={usage.get('promptTokenCount')}, Output={usage.get('candidatesTokenCount')}, Total={usage.get('totalTokenCount')}")
            
            parsed = json.loads(text_out)
            print(f"JSON Parsed successfully. Objects returned: {len(parsed)}")
            
            schema_failures = 0
            invalid_indices = 0
            evidence_failures = 0
            unique_indices = set()
            
            for obs in parsed:
                idx = obs.get("i")
                if idx is None or idx < 0 or idx >= len(batch):
                    invalid_indices += 1
                    continue
                unique_indices.add(idx)
                
                try:
                    expand_observation(obs, batch[idx]["cleaned_text"])
                except Exception as e:
                    if "Evidence quote not found" in str(e):
                        evidence_failures += 1
                    else:
                        schema_failures += 1
            
            # Find omitted records
            omitted = set(range(batch_size)) - unique_indices
            
            print("\n--- VALIDATION RESULTS ---")
            print(f"Source records submitted: {batch_size}")
            print(f"Source records represented in output: {len(unique_indices)}")
            print(f"Omitted records: {len(omitted)}")
            print(f"Observations returned: {len(parsed)}")
            print(f"Schema/Enum failures: {schema_failures}")
            print(f"Evidence quote substring failures: {evidence_failures}")
            print(f"Invalid indices: {invalid_indices}")
            print(f"Cross-record leakage: {invalid_indices}")
            print("--------------------------\n")
            
            if schema_failures == 0 and evidence_failures == 0 and invalid_indices == 0 and len(omitted) == 0:
                print(f"BATCH SIZE {batch_size} PASSES ALL VALIDATION.")
            else:
                print(f"BATCH SIZE {batch_size} FAILED VALIDATION.")
                
        except Exception as e:
            print(f"Exception during request: {e}")

if __name__ == "__main__":
    import sys
    batch_size = 50
    if len(sys.argv) > 1:
        batch_size = int(sys.argv[1])
    run_batch_test(batch_size)
