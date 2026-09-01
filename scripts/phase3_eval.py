import os
import json
import time
import httpx
import sqlite3
import argparse
from dotenv import load_dotenv

DB_FILE = "data/discovery_pulse.db"
MANIFEST_FILE = "data/eval_manifest_100.json"

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
            return code
        return mappings[field][code]
    return code

def run_eval(model_name, batch_size):
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

    with open(MANIFEST_FILE, "r") as f:
        manifest = json.load(f)

    # Fetch cleaned_text for these records
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    rids = [m["source_record_id"] for m in manifest]
    cursor.execute(f"""
        SELECT c.cleaned_text, r.raw_record_id
        FROM cleaned_records c
        JOIN raw_records r ON c.raw_record_id = r.raw_record_id
        WHERE r.raw_record_id IN ({','.join(['?']*len(rids))})
    """, rids)
    
    texts = {row["raw_record_id"]: row["cleaned_text"] for row in cursor.fetchall()}
    
    records = []
    for m in manifest:
        rid = m["source_record_id"]
        records.append({"raw_record_id": rid, "cleaned_text": texts[rid], "subset": m["subset"]})
        
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

    all_parsed = []
    total_usage = {"prompt": 0, "output": 0, "total": 0}
    schema_pass = True
    
    # Process in batches
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        mapped_batch = [{"i": j, "text": r["cleaned_text"]} for j, r in enumerate(batch)]
        
        payload = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"parts": [{"text": json.dumps(mapped_batch)}]}],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
                "responseSchema": compact_schema
            }
        }
        
        if "3.6-flash" in model_name:
            payload["generationConfig"]["thinkingConfig"] = {"thinkingLevel": "LOW"}

        print(f"Submitting {model_name} batch of size {len(batch)}...")
        start_time = time.time()
        with httpx.Client(timeout=180.0) as client:
            resp = client.post(url, json=payload)
            lat = time.time() - start_time
            print(f"HTTP {resp.status_code} in {lat:.2f}s")
            
            if resp.status_code == 429:
                print("429 NO FREE QUOTA")
                return
            elif resp.status_code != 200:
                print(f"Error: {resp.text}")
                return

            data = resp.json()
            usage = data.get("usageMetadata", {})
            total_usage["prompt"] += usage.get("promptTokenCount", 0)
            total_usage["output"] += usage.get("candidatesTokenCount", 0)
            total_usage["total"] += usage.get("totalTokenCount", 0)
            
            try:
                text_out = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text_out)
                
                # Fix up the index 'i' to be global across the 100 records
                for obs in parsed:
                    if "i" in obs:
                        obs["i"] = obs["i"] + i
                
                all_parsed.extend(parsed)
            except Exception as e:
                print(f"Failed to parse response: {e}")
                schema_pass = False

    # Validation
    quote_failures = 0
    omitted = 0
    cross_record = 0
    
    # Baseline observation differences
    # We will get current observations from DB for these records and compare
    cursor.execute(f"""
        SELECT source_record_id, primary_barrier, decision_outcome, uncertainty, evidence_quote
        FROM observations
        WHERE source_record_id IN ({','.join(['?']*len(rids))})
    """, rids)
    
    baseline_obs = {}
    for row in cursor.fetchall():
        rid = row["source_record_id"]
        if rid not in baseline_obs:
            baseline_obs[rid] = []
        baseline_obs[rid].append(dict(row))

    new_obs = {}
    for obs in all_parsed:
        idx = obs.get("i")
        if idx is None or idx < 0 or idx >= len(records):
            cross_record += 1
            continue
            
        rid = records[idx]["raw_record_id"]
        original_text = records[idx]["cleaned_text"]
        quote = obs.get("q", "")
        
        if quote != "?" and quote not in original_text:
            quote_failures += 1
            
        if rid not in new_obs:
            new_obs[rid] = []
        new_obs[rid].append(obs)
        
    zero_obs_diff = 0
    obs_count_diff = 0
    
    comparison_data = []
    
    for r in records:
        rid = r["raw_record_id"]
        b_list = baseline_obs.get(rid, [])
        n_list = new_obs.get(rid, [])
        
        if not b_list and not n_list:
            continue # both zero
        elif not b_list and n_list:
            zero_obs_diff += 1
        elif b_list and not n_list:
            zero_obs_diff += 1
            omitted += 1
            
        if len(b_list) != len(n_list):
            obs_count_diff += 1
            
        # Collect for manual review
        comparison_data.append({
            "record_id": rid,
            "text": r["cleaned_text"],
            "subset": r["subset"],
            "baseline": b_list,
            "new": n_list
        })
        
    # Save the run results
    out_file = f"data/eval_{model_name.replace('/', '_')}_batch{batch_size}.json"
    with open(out_file, "w") as f:
        json.dump({
            "model": model_name,
            "batch_size": batch_size,
            "usage": total_usage,
            "schema_pass": schema_pass,
            "quote_failures": quote_failures,
            "omitted": omitted,
            "cross_record_leakage": cross_record,
            "zero_obs_diff": zero_obs_diff,
            "obs_count_diff": obs_count_diff,
            "records": comparison_data
        }, f, indent=2)
        
    print(f"\nStats for {model_name} Batch {batch_size}")
    print(f"Total tokens: {total_usage['total']}")
    print(f"Schema pass: {schema_pass}")
    print(f"Quote failures: {quote_failures}")
    print(f"Omitted records: {omitted}")
    print(f"Cross-record leakage: {cross_record}")
    print(f"Zero-obs diffs: {zero_obs_diff}")
    print(f"Obs count diffs: {obs_count_diff}")
    print(f"Saved results to {out_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--batch", type=int, required=True)
    args = parser.parse_args()
    
    run_eval(args.model, args.batch)
