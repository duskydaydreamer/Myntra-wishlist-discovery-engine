import os
import json
import time
import httpx
import sqlite3
import uuid
from datetime import datetime
from dotenv import load_dotenv

DB_FILE = "data/discovery_pulse.db"
TELEMETRY_FILE = "data/extraction_telemetry_final.json"
ACCOUNTING_FILE = "data/extraction_accounting.json"
RUN_ID = "run_" + str(int(time.time()))
RUN_FILE = f"data/observations/{RUN_ID}.jsonl"
CACHE_FILE = "data/phase3b_extraction_cache.json"

base_delay = 4.0 # Target ~15 RPM


acct = {
    "batches_started": 0,
    "batches_completed": 0,
    "batches_unresolved": 0,
    "generatecontent_calls": 0,
    "successful_http_calls": 0,
    "failed_http_calls": 0,
    "retry_calls": 0,
    "http_429": 0,
    "http_503": 0,
    "transport_timeouts": 0,
    "other_provider_errors": 0,
    "tokens": {
        "prompt": 0,
        "candidate": 0,
        "thinking": 0,
        "total": 0
    },
    "successfully_processed_source_records": 0,
    "valid_observations": 0
}

def save_accounting():
    with open(ACCOUNTING_FILE, "w") as f:
        json.dump(acct, f, indent=2)

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
        "secondary_barriers": {"PR": "price", "QU": "quality", "FI": "fit", "DE": "delivery", "TR": "trust"},
        "sentiment": {"PO": "positive", "NE": "negative", "MI": "mixed", "NU": "neutral"},
        "problem_status": {"PB": "problem", "PA": "praise", "MX": "mixed", "IN": "informational"},
        "topic": {
            "FS": "fit_and_sizing", "PF": "pricing_and_fees", "PQ": "product_quality",
            "DF": "delivery_and_fulfillment", "RR": "returns_and_refunds",
            "CS": "customer_support", "PD": "product_discovery",
            "PI": "product_information", "SA": "seller_and_authenticity",
            "SV": "shopping_value", "OT": "other"
        }
    }
    if field in mappings:
        if code not in mappings[field]:
            raise ValueError(f"Invalid compact code '{code}' for field '{field}'")
        return mappings[field][code]
    return code

def normalize_text(text):
    """Normalize whitespace and case for comparison only."""
    import re
    return re.sub(r'\s+', ' ', text).strip().lower()

def expand_observation(obs, original_text):
    if "i" not in obs or "q" not in obs:
        raise ValueError("Missing required field 'i' or 'q'")
    quote = obs["q"]
    if quote != "?":
        # First try exact match
        if quote not in original_text:
            # Try normalized match (handles newline->space and case normalization)
            norm_quote = normalize_text(quote)
            norm_text = normalize_text(original_text)
            if norm_quote not in norm_text:
                raise ValueError(f"Evidence quote not found in text: {quote}")
            # Accepted via normalized match — quote is semantically verbatim
    expanded = {"local_index": obs["i"], "evidence_quote": quote}
    for k, v in obs.items():
        if k in ["i", "q"]: continue
        field_map = {
            "m": "is_myntra_specific", "js": "journey_stage", "wi": "wishlist_intent",
            "pi": "purchase_intent", "pc": "product_category", "t": "theme", "tp": "topic",
            "pb": "primary_barrier", "sb": "secondary_barriers", "rc": "root_cause",
            "u": "uncertainty", "inf": "information_needed", "wa": "workaround",
            "ep": "external_platform_used", "ac": "alternative_considered",
            "o": "occasion", "do": "decision_outcome", "ss": "segment_signal",
            "se": "sentiment", "ps": "problem_status", "cf": "ai_confidence"
        }
        full_field = field_map.get(k, k)
        if k == "sb" and isinstance(v, list):
            expanded[full_field] = [expand_enum(full_field, code) for code in v]
        elif k in ["js", "wi", "pi", "pb", "do", "se", "ps", "tp"]:
            expanded[full_field] = expand_enum(full_field, v)
        else:
            expanded[full_field] = "unknown" if v == "?" else v
    return expanded

def extract_batch(client, url, system_instruction, compact_schema, batch, batch_id):
    global base_delay
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
        acct["generatecontent_calls"] += 1
        if retries > 0: acct["retry_calls"] += 1
        try:
            resp = client.post(url, json=payload)
            lat = time.time() - start
            if resp.status_code == 429:
                acct["failed_http_calls"] += 1
                acct["http_429"] += 1
                try: err_body = resp.json()
                except: err_body = resp.text
                headers = dict(resp.headers)
                err_msg = str(err_body)
                is_daily = "per day" in err_msg.lower() or "daily" in err_msg.lower()
                print(f"429 DETAILS: Headers: {headers} | Body: {err_body}")
                if is_daily:
                    return None, {}, lat, "DAILY_QUOTA_EXHAUSTED", {"headers": headers, "body": err_body}
                else:
                    if "retry-after" in headers: delay = int(headers["retry-after"])
                    else: delay = (2 ** retries) * 5
                    if retries < max_retries:
                        print(f"429 Rate limit hit. Backing off for {delay}s...")
                        base_delay = min(base_delay * 1.5, 60.0)
                        time.sleep(delay)
                        retries += 1
                        continue
                    else:
                        return None, {}, lat, "RATE_LIMIT_EXHAUSTED", {"headers": headers, "body": err_body}
            elif resp.status_code == 503:
                acct["failed_http_calls"] += 1
                acct["http_503"] += 1
                if retries < max_retries:
                    delay = (2 ** retries) * 2
                    print(f"503 Service Unavailable. Backing off for {delay}s...")
                    time.sleep(delay)
                    retries += 1
                    continue
                else:
                    return None, {}, lat, "503_EXHAUSTED", {}
            resp.raise_for_status()
            acct["successful_http_calls"] += 1
            data = resp.json()
            usage = data.get("usageMetadata", {})
            text_out = data["candidates"][0]["content"]["parts"][0]["text"]
            try:
                parsed = json.loads(text_out)
            except json.JSONDecodeError as e:
                acct["other_provider_errors"] += 1
                if retries < max_retries:
                    time.sleep((2 ** retries) * 2)
                    retries += 1
                    continue
                else:
                    return None, {}, lat, f"JSON_DECODE_ERROR: {e}", {}
            return parsed, usage, lat, None, {}
        except httpx.ReadTimeout:
            lat = time.time() - start
            acct["failed_http_calls"] += 1
            acct["transport_timeouts"] += 1
            if retries < max_retries:
                delay = (2 ** retries) * 2
                time.sleep(delay)
                retries += 1
                continue
            else:
                return None, {}, lat, "TIMEOUT_EXHAUSTED", {}
        except Exception as e:
            lat = time.time() - start
            acct["failed_http_calls"] += 1
            acct["other_provider_errors"] += 1
            if retries < max_retries:
                time.sleep((2 ** retries) * 2)
                retries += 1
                continue
            return None, {}, lat, f"EXCEPTION: {str(e)}", {}
    return None, {}, 0, "MAX_RETRIES_EXCEEDED", {}

def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.cleaned_record_id, c.cleaned_text, r.raw_record_id, r.source, r.source_url, r.evidence_type
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
    print(f"Total eligible relevant records: {len(relevant_records)}")
    print(f"Remaining to process (unresolved_retryable): {len(remaining_records)}")
    
    compact_schema = {
        "type": "array", "items": {
            "type": "object", "properties": {
                "i": {"type": "integer"},
                "js": {"type": "string", "enum": ["DI", "EV", "PU", "PP", "?"]},
                "wi": {"type": "string", "enum": ["GP", "PT", "CS", "IN", "BM", "AS", "OP", "?"]},
                "pi": {"type": "string", "enum": ["HI", "LO", "NO", "?"]},
                "pc": {"type": "string"}, "t": {"type": "string"},
                "tp": {"type": "string", "enum": ["FS", "PF", "PQ", "DF", "RR", "CS", "PD", "PI", "SA", "SV", "OT", "?"]},
                "se": {"type": "string", "enum": ["PO", "NE", "MI", "NU", "?"]},
                "ps": {"type": "string", "enum": ["PB", "PA", "MX", "IN", "?"]},
                "cf": {"type": "number", "minimum": 0, "maximum": 1},
                "pb": {"type": "string", "enum": ["PR", "QU", "FI", "DE", "TR", "?"]},
                "sb": {"type": "array", "items": {"type": "string", "enum": ["PR", "QU", "FI", "DE", "TR", "?"]}},
                "rc": {"type": "string"}, "u": {"type": "string"},
                "inf": {"type": "string"}, "wa": {"type": "string"},
                "ep": {"type": "string"}, "ac": {"type": "string"},
                "o": {"type": "string"},
                "do": {"type": "string", "enum": ["AB", "BO", "DE", "SW", "?"]},
                "ss": {"type": "string"}, "q": {"type": "string"}
            },
            "required": ["i", "q", "js", "wi", "pi", "pb", "do", "tp", "se", "ps", "cf"]
        }
    }
    
    system_instruction = """
    Extract structured observations. Return an array of JSON objects.
    Each input record has an integer 'i'. Return multiple objects if multiple insights exist.
    Use '?' for unknown/unsupported values.
    
    Compact Keys:
    i = local index (integer, MUST match input)
    js = journey_stage (DI=discovery, EV=evaluation, PU=purchase, PP=post_purchase)
    wi = wishlist_intent (GP=genuine_purchase, PT=price_tracking, CS=comparison_shortlist, IN=inspiration, BM=bookmarking, AS=aspirational_saving, OP=occasion_planning)
    pi = purchase_intent (HI=high, LO=low, NO=none)
    pc = product_category
    t = theme
    tp = primary topic (FS=fit/sizing, PF=pricing/fees, PQ=product quality, DF=delivery/fulfillment,
         RR=returns/refunds, CS=customer support, PD=product discovery, PI=product information,
         SA=seller/authenticity, SV=shopping value, OT=other)
    se = expressed sentiment (PO=positive, NE=negative, MI=mixed, NU=neutral)
    ps = evidence role (PB=explicit problem/uncertainty/unmet need, PA=explicit praise,
         MX=both problem and praise, IN=informational without a problem or praise)
    cf = model self-rating from 0 to 1 for how directly tp/se/ps are supported by q
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
    
    Classify only what the quote explicitly supports. Do not infer a problem from a topic alone.
    Use '?' when topic, sentiment, or evidence role is unsupported. A request for missing information
    may be PB; a factual product-link post with no request is IN. Praise and problems must remain separate.
    'q' must be an exact substring. Never invent quotes. Use compact enum codes for fixed taxonomies.
    """
    
    batch_size = 50
    chunks = [remaining_records[i:i+batch_size] for i in range(0, len(remaining_records), batch_size)]
    os.makedirs("data/observations", exist_ok=True)
    run_file = open(RUN_FILE, "a")
    
    with httpx.Client(timeout=90.0) as client:
        for batch_idx, batch in enumerate(chunks):
            batch_id = f"phase3b_batch_{batch_idx}_{int(time.time())}"
            print(f"\nProcessing {batch_id} (size {len(batch)})...")
            acct["batches_started"] += 1
            parsed, usage, lat, err, err_meta = extract_batch(client, url, system_instruction, compact_schema, batch, batch_id)
            if err:
                print(f"Error on {batch_id}: {err}")
                acct["batches_unresolved"] += 1
                if "DAILY_QUOTA_EXHAUSTED" in err:
                    print("Daily Quota Exhausted. Stopping entirely.")
                    break
                elif "RATE_LIMIT_EXHAUSTED" in err:
                    print("Repeated rate limit failures. Stopping entirely.")
                    break
                continue
            
            if parsed is not None:
                p = usage.get("promptTokenCount", 0)
                c = usage.get("candidatesTokenCount", 0)
                t = usage.get("totalTokenCount", 0)
                th = usage.get("thoughtsTokenCount", 0)
                acct["tokens"]["prompt"] += p
                acct["tokens"]["candidate"] += c
                acct["tokens"]["thinking"] += th
                acct["tokens"]["total"] += t
                
                valid_obs_for_db = []
                records_with_obs = set()
                
                for obs in parsed:
                    local_idx = obs.get("i")
                    if local_idx is None or local_idx < 0 or local_idx >= len(batch): continue
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
                            "evidence_scope": orig_record.get("evidence_type") or "unknown",
                            "is_myntra_specific": orig_record.get("evidence_type") == "myntra_specific",
                            "evidence_quote": expanded["evidence_quote"],
                            "extracted_at": datetime.utcnow().isoformat(),
                            "model_id": "gemini-3.6-flash",
                            "prompt_version": "v3-research-safe-phase3b",
                            "created_in_pipeline_run_id": RUN_ID,
                        }
                        for k, v in expanded.items():
                            if k not in ["evidence_quote", "local_index"]:
                                if isinstance(v, list): v = json.dumps(v)
                                db_obs[k] = v
                        valid_obs_for_db.append(db_obs)
                        run_file.write(json.dumps(db_obs) + "\n")
                        acct["valid_observations"] += 1
                    except Exception as e:
                        print(f"Expansion/Validation error in {batch_id}: {e}")
                        continue
                
                if valid_obs_for_db:
                    # Use a fixed canonical column set so observations with different
                    # optional fields don't cause KeyErrors during batch insertion.
                    canonical_cols = [
                        "observation_id", "source_record_id", "cleaned_record_id",
                        "source", "source_url", "is_myntra_specific", "journey_stage",
                        "wishlist_intent", "purchase_intent", "product_category", "theme",
                        "topic", "sentiment", "problem_status", "evidence_scope",
                        "primary_barrier", "secondary_barriers", "root_cause", "uncertainty",
                        "information_needed", "workaround", "external_platform_used",
                        "alternative_considered", "occasion", "decision_outcome",
                        "segment_signal", "evidence_quote", "extracted_at",
                        "model_id", "prompt_version", "ai_confidence", "created_in_pipeline_run_id"
                    ]
                    sql = f"INSERT INTO observations ({','.join(canonical_cols)}) VALUES ({','.join(['?' for _ in canonical_cols])})"
                    for o in valid_obs_for_db:
                        cursor.execute(sql, [o.get(c) for c in canonical_cols])
                    conn.commit()
                
                for r in batch:
                    if r["cleaned_record_id"] in records_with_obs:
                        extraction_cache[r["cleaned_record_id"]] = "successfully_extracted"
                    else:
                        extraction_cache[r["cleaned_record_id"]] = "successfully_processed_zero_observations"
                    acct["successfully_processed_source_records"] += 1
                        
                with open(CACHE_FILE, "w") as f:
                    json.dump(extraction_cache, f, indent=2)
                acct["batches_completed"] += 1
            save_accounting()
            time.sleep(base_delay)
            
    run_file.close()
    conn.close()
    save_accounting()
    print("\nBatch processing finished.")
    print("ACCOUNTING SUMMARY:")
    print(json.dumps(acct, indent=2))

if __name__ == "__main__":
    main()
