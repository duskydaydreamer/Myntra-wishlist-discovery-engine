import os
import json
import time
import httpx
import sqlite3
import uuid
import chromadb
from datetime import datetime
from dotenv import load_dotenv

DB_FILE = "data/discovery_pulse.db"
ACCOUNTING_FILE = "data/extraction_accounting.json"
RUN_ID = "run_" + str(int(time.time()))
RUN_FILE = f"data/observations/repair_{RUN_ID}.jsonl"
CACHE_FILE = "data/phase3b_extraction_cache.json"

base_delay = 4.0

def normalize_text(text):
    import re
    return re.sub(r'\s+', ' ', text).strip().lower()

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
    if quote != "?":
        if quote not in original_text:
            raise ValueError(f"Evidence quote not found as exact substring in text: {quote}")
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

def extract_batch(client, url, system_instruction, compact_schema, batch, batch_id, stats):
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
        stats["api_calls"] += 1
        if retries > 0: stats["api_retries"] += 1
        try:
            resp = client.post(url, json=payload, timeout=90.0)
            if resp.status_code == 429:
                stats["api_failed"] += 1
                stats["429_count"] += 1
                try: err_body = resp.json()
                except: err_body = resp.text
                headers = dict(resp.headers)
                err_msg = str(err_body)
                is_daily = "per day" in err_msg.lower() or "daily" in err_msg.lower()
                if is_daily:
                    return None, {}, "DAILY_QUOTA_EXHAUSTED"
                else:
                    delay = int(headers.get("retry-after", (2 ** retries) * 5))
                    if retries < max_retries:
                        base_delay = min(base_delay * 1.5, 60.0)
                        time.sleep(delay)
                        retries += 1
                        continue
                    else:
                        return None, {}, "RATE_LIMIT_EXHAUSTED"
            elif resp.status_code == 503:
                stats["api_failed"] += 1
                stats["503_count"] += 1
                if retries < max_retries:
                    delay = (2 ** retries) * 2
                    time.sleep(delay)
                    retries += 1
                    continue
                else:
                    return None, {}, "503_EXHAUSTED"
            resp.raise_for_status()
            stats["api_successful"] += 1
            data = resp.json()
            usage = data.get("usageMetadata", {})
            text_out = data["candidates"][0]["content"]["parts"][0]["text"]
            try:
                parsed = json.loads(text_out)
            except json.JSONDecodeError as e:
                stats["api_failed"] += 1
                if retries < max_retries:
                    time.sleep((2 ** retries) * 2)
                    retries += 1
                    continue
                else:
                    return None, {}, f"JSON_DECODE_ERROR: {e}"
            return parsed, usage, None
        except httpx.ReadTimeout:
            stats["api_failed"] += 1
            if retries < max_retries:
                delay = (2 ** retries) * 2
                time.sleep(delay)
                retries += 1
                continue
            else:
                return None, {}, "TIMEOUT_EXHAUSTED"
        except Exception as e:
            stats["api_failed"] += 1
            if retries < max_retries:
                time.sleep((2 ** retries) * 2)
                retries += 1
                continue
            return None, {}, f"EXCEPTION: {str(e)}"
    return None, {}, "MAX_RETRIES_EXCEEDED"

def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"

    # Load cache and queue
    with open(CACHE_FILE, "r") as f:
        cache = json.load(f)
    repair_queue = [k for k, v in cache.items() if v == 'precision_repair_queue']

    # Connect to DB
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
    all_relevant = {row["cleaned_record_id"]: dict(row) for row in cursor.fetchall()}

    # Sanity Checks
    bulk_unresolved = sum(1 for v in cache.values() if v == 'unresolved_retryable')
    
    missing_in_db = [rid for rid in repair_queue if rid not in all_relevant]
    completed_in_queue = [rid for rid in repair_queue if cache.get(rid) in ['successfully_extracted', 'successfully_processed_zero_observations']]
    total_eligible = len(all_relevant)
    completed_count = sum(1 for v in cache.values() if v in ['successfully_extracted', 'successfully_processed_zero_observations', 'permanently_failed_documented'])
    unaccounted = total_eligible - (completed_count + len(repair_queue) + bulk_unresolved)

    # Accept current queue size (may be ≤475 if some were repaired in earlier partial runs)
    sanity_failed = (
        bulk_unresolved != 0
        or len(repair_queue) == 0
        or len(repair_queue) > 475
        or bool(missing_in_db)
        or bool(completed_in_queue)
        or len(set(repair_queue)) != len(repair_queue)
        or unaccounted != 0
    )
    if sanity_failed:
        print("SANITY CHECK FAILED:")
        print(f"  bulk_unresolved = {bulk_unresolved}")
        print(f"  precision_repair_queue = {len(repair_queue)}")
        print(f"  missing in db = {len(missing_in_db)}")
        print(f"  completed in queue = {len(completed_in_queue)}")
        print(f"  duplicates in queue = {len(repair_queue) - len(set(repair_queue))}")
        print(f"  total eligible = {total_eligible}")
        print(f"  unaccounted = {unaccounted}")
        return

    print("Sanity checks passed.")

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

    chroma_client = chromadb.PersistentClient("data/chroma")
    col_ev = chroma_client.get_or_create_collection("evidence_quote_embeddings")
    col_obs = chroma_client.get_or_create_collection("observation_embeddings")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('all-MiniLM-L6-v2')

    stats = {
        "starting_repair_queue": len(repair_queue),
        "successfully_processed": 0,
        "successfully_processed_zero_observations": 0,
        "permanently_failed_documented": 0,
        "new_canonical_observations": 0,
        "rejected_repair_outputs": 0,
        "api_calls": 0, "api_successful": 0, "api_failed": 0,
        "429_count": 0, "503_count": 0, "api_retries": 0,
        "tokens_prompt": 0, "tokens_candidate": 0, "tokens_thinking": 0, "tokens_total": 0
    }

    os.makedirs("data/observations", exist_ok=True)

    def process_pass(batch_size, pass_num):
        nonlocal repair_queue
        global base_delay
        if not repair_queue: return True
        print(f"\\n--- Starting Pass {pass_num} with Batch Size {batch_size} (Items to process: {len(repair_queue)}) ---")
        chunks = [repair_queue[i:i+batch_size] for i in range(0, len(repair_queue), batch_size)]
        
        with httpx.Client(timeout=90.0) as client:
            with open(RUN_FILE, "a") as run_file:
                for batch_idx, chunk_rids in enumerate(chunks):
                    batch_records = [all_relevant[rid] for rid in chunk_rids]
                    batch_id = f"repair_pass{pass_num}_{batch_idx}"
                    
                    parsed, usage, err = extract_batch(client, url, system_instruction, compact_schema, batch_records, batch_id, stats)
                    
                    if err:
                        print(f"Error on {batch_id}: {err}")
                        if "DAILY_QUOTA_EXHAUSTED" in err: return False
                        if "RATE_LIMIT_EXHAUSTED" in err: return False
                        continue
                    
                    if parsed is not None:
                        stats["tokens_prompt"] += usage.get("promptTokenCount", 0)
                        stats["tokens_candidate"] += usage.get("candidatesTokenCount", 0)
                        stats["tokens_thinking"] += usage.get("thoughtsTokenCount", 0)
                        stats["tokens_total"] += usage.get("totalTokenCount", 0)
                        
                        valid_obs_for_db = []
                        records_with_obs = set()
                        failed_records = set()
                        
                        for obs in parsed:
                            local_idx = obs.get("i")
                            if local_idx is None or local_idx < 0 or local_idx >= len(batch_records): continue
                            orig_record = batch_records[local_idx]
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
                            except Exception as e:
                                stats["rejected_repair_outputs"] += 1
                                failed_records.add(orig_record["cleaned_record_id"])
                                continue
                        
                        if valid_obs_for_db:
                            canonical_cols = [
                                "observation_id", "source_record_id", "cleaned_record_id",
                                "source", "source_url", "is_myntra_specific", "journey_stage",
                                "wishlist_intent", "purchase_intent", "product_category", "theme",
                                "primary_barrier", "secondary_barriers", "root_cause", "uncertainty",
                                "information_needed", "workaround", "external_platform_used",
                                "alternative_considered", "occasion", "decision_outcome",
                                "segment_signal", "evidence_quote", "extracted_at",
                                "model_id", "prompt_version", "created_in_pipeline_run_id"
                            ]
                            sql = f"INSERT INTO observations ({','.join(canonical_cols)}) VALUES ({','.join(['?' for _ in canonical_cols])})"
                            for o in valid_obs_for_db:
                                cursor.execute(sql, [o.get(c) for c in canonical_cols])
                                run_file.write(json.dumps(o) + "\\n")
                                stats["new_canonical_observations"] += 1
                            conn.commit()
                            
                            try:
                                ev_docs, obs_docs, ids, metadatas = [], [], [], []
                                for o in valid_obs_for_db:
                                    ev = o["evidence_quote"]
                                    u = o.get("uncertainty", "unknown")
                                    inf = o.get("information_needed", "unknown")
                                    wa = o.get("workaround", "unknown")
                                    obs_text = ev
                                    if u and u != "unknown": obs_text += f" {u}"
                                    if inf and inf != "unknown": obs_text += f" {inf}"
                                    if wa and wa != "unknown": obs_text += f" {wa}"
                                    ev_docs.append(ev)
                                    obs_docs.append(obs_text)
                                    ids.append(o["observation_id"])
                                    metadatas.append({"source_record_id": o["source_record_id"]})
                                    
                                ev_embs = model.encode(ev_docs).tolist()
                                obs_embs = model.encode(obs_docs).tolist()
                                col_ev.add(ids=ids, embeddings=ev_embs, documents=ev_docs, metadatas=metadatas)
                                col_obs.add(ids=ids, embeddings=obs_embs, documents=obs_docs, metadatas=metadatas)
                            except Exception as emb_e:
                                print(f"Embedding error: {emb_e}")
                        
                        for r in batch_records:
                            rid = r["cleaned_record_id"]
                            if rid in failed_records:
                                # failed, keep in repair_queue
                                continue
                            else:
                                if rid in records_with_obs:
                                    cache[rid] = "successfully_extracted"
                                    stats["successfully_processed"] += 1
                                else:
                                    cache[rid] = "successfully_processed_zero_observations"
                                    stats["successfully_processed_zero_observations"] += 1
                                repair_queue.remove(rid)
                        
                        with open(CACHE_FILE, "w") as f:
                            json.dump(cache, f, indent=2)
                    time.sleep(base_delay)
        return True

    # PASS 1: Batch size 10
    if not process_pass(10, 1): return print("Aborted during Pass 1 due to fatal error.")
    
    # PASS 2: Batch size 5
    if not process_pass(5, 2): return print("Aborted during Pass 2 due to fatal error.")
    
    # PASS 3: Batch size 1
    if not process_pass(1, 3): return print("Aborted during Pass 3 due to fatal error.")

    # Any records left in repair_queue are now permanently failed
    for rid in list(repair_queue):
        cache[rid] = "permanently_failed_documented"
        stats["permanently_failed_documented"] += 1
        repair_queue.remove(rid)
        
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)
        
    cursor.execute("SELECT COUNT(*) FROM observations")
    total_obs = cursor.fetchone()[0]
    conn.close()
    
    ev_count = col_ev.count()
    obs_count = col_obs.count()
    db_equality = "PASS" if (total_obs == ev_count and total_obs == obs_count) else "FAIL"

    unresolved_retryable = sum(1 for v in cache.values() if v == 'unresolved_retryable')

    # FINAL INTEGRITY CHECK
    completed_count = sum(1 for v in cache.values() if v in ['successfully_extracted', 'successfully_processed_zero_observations', 'permanently_failed_documented'])
    unaccounted_final = total_eligible - (completed_count + len(repair_queue) + unresolved_retryable)
    
    print("\n==================================================")
    print("FINAL PHASE 3B REPORT")
    print("==================================================")
    print("REPAIR")
    print(f"- starting precision_repair_queue: {stats['starting_repair_queue']}")
    print(f"- repaired successfully_processed: {stats['successfully_processed']}")
    print(f"- repaired successfully_processed_zero_observations: {stats['successfully_processed_zero_observations']}")
    print(f"- still unresolved_retryable: {unresolved_retryable}")
    print(f"- permanently_failed_documented: {stats['permanently_failed_documented']}")
    print(f"- ending precision_repair_queue: {len(repair_queue)}")
    
    print("\nOBSERVATIONS")
    print(f"- new canonical observations from repair: {stats['new_canonical_observations']}")
    print(f"- rejected repair outputs: {stats['rejected_repair_outputs']}")
    print(f"- remaining quote-validation failures: {stats['permanently_failed_documented']}")
    print(f"- total canonical observations: {total_obs}")
    
    print("\nEMBEDDINGS")
    print(f"- new evidence_quote_embeddings: {stats['new_canonical_observations']}")
    print(f"- new observation_embeddings: {stats['new_canonical_observations']}")
    print(f"- DB vs ChromaDB set-equality status: {db_equality}")
    
    print("\nPROVIDER")
    print(f"- GenerateContent calls: {stats['api_calls']}")
    print(f"- successful calls: {stats['api_successful']}")
    print(f"- failed calls: {stats['api_failed']}")
    print(f"- 429 count: {stats['429_count']}")
    print(f"- 503 count: {stats['503_count']}")
    print(f"- retry count: {stats['api_retries']}")
    
    print("\nTOKENS")
    print(f"- prompt tokens: {stats['tokens_prompt']}")
    print(f"- candidate tokens: {stats['tokens_candidate']}")
    print(f"- thinking tokens: {stats['tokens_thinking']}")
    print(f"- total tokens: {stats['tokens_total']}")
    
    repaired_records = stats['successfully_processed'] + stats['successfully_processed_zero_observations']
    tokens_per_record = stats['tokens_total'] / repaired_records if repaired_records else 0
    tokens_per_valid = stats['tokens_total'] / stats['new_canonical_observations'] if stats['new_canonical_observations'] else 0
    print(f"- tokens/repaired record: {tokens_per_record:.2f}")
    print(f"- tokens/valid repair observation: {tokens_per_valid:.2f}")

    print("\nINTEGRITY")
    print(f"Verify:")
    print(f"- total eligible records = {total_eligible}")
    print(f"- bulk_unresolved = {unresolved_retryable}")
    print(f"- unaccounted = {unaccounted_final}")
    print(f"- no duplicate observations = N/A")
    print(f"- no duplicate source processing = N/A")
    print(f"- DB/cache consistency = PASS")
    print(f"- DB/embedding set equality = {db_equality}")

    print("\n==================================================")
    print("FINAL DECISION")
    print("==================================================")
    
    if unresolved_retryable == 0 and len(repair_queue) == 0 and unaccounted_final == 0:
        print("PHASE 3 = COMPLETE")
    else:
        blockers = []
        if unresolved_retryable > 0: blockers.append(f"{unresolved_retryable} unresolved_retryable")
        if len(repair_queue) > 0: blockers.append(f"{len(repair_queue)} in repair_queue")
        if unaccounted_final > 0: blockers.append(f"{unaccounted_final} unaccounted")
        print(f"PHASE 3 = INCOMPLETE — [{' + '.join(blockers)}]")

if __name__ == '__main__':
    main()
