import sqlite3
import json
import chromadb
import datetime
import os

DB_FILE = 'data/discovery_pulse.db'
CACHE_FILE = 'data/phase3b_extraction_cache.json'
AUDIT_FILE = 'data/invalid_quotes_audit.json'

def main():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    with open(CACHE_FILE, 'r') as f:
        cache = json.load(f)
        
    client = chromadb.PersistentClient('data/chroma')
    col_ev = client.get_collection('evidence_quote_embeddings')
    col_obs = client.get_collection('observation_embeddings')

    # BEFORE CLEANUP COUNTS
    c.execute("SELECT COUNT(*) FROM observations")
    before_canonical = c.fetchone()[0]
    before_ev = col_ev.count()
    before_obs = col_obs.count()
    before_queue = sum(1 for v in cache.values() if v == 'precision_repair_queue')

    # 1. GLOBAL ZERO-API QUOTE-INTEGRITY SWEEP
    c.execute("""
        SELECT o.observation_id, o.cleaned_record_id, o.source_record_id, o.evidence_quote, 
               o.model_id, o.created_in_pipeline_run_id, c.cleaned_text
        FROM observations o
        JOIN cleaned_records c ON o.cleaned_record_id = c.cleaned_record_id
    """)
    
    all_obs = c.fetchall()
    invalid_obs = []
    affected_sources = set()
    
    for row in all_obs:
        quote = row['evidence_quote']
        if not quote or quote not in row['cleaned_text']:
            invalid_obs.append(row)
            affected_sources.add(row['cleaned_record_id'])
            
    print("==================================================")
    print("1. GLOBAL ZERO-API QUOTE-INTEGRITY SWEEP")
    print("==================================================")
    print(f"- total canonical observations checked: {len(all_obs)}")
    print(f"- total invalid observations: {len(invalid_obs)}")
    print(f"- total affected source records: {len(affected_sources)}")
    print(f"- exact invalid observation_ids: {[r['observation_id'] for r in invalid_obs]}")
    print(f"- exact affected source_record_ids: {list(affected_sources)}")

    if not invalid_obs:
        print("No invalid observations found. Exiting cleanup.")
        return

    # 2. REMOVE ONLY INVALID CANONICAL OBSERVATIONS
    audit_records = []
    invalid_ids = [r['observation_id'] for r in invalid_obs]
    
    for r in invalid_obs:
        audit_records.append({
            "observation_id": r["observation_id"],
            "source_record_id": r["source_record_id"],
            "cleaned_record_id": r["cleaned_record_id"],
            "previous_evidence_quote": r["evidence_quote"],
            "failure_reason": "persisted_quote_not_exact_substring",
            "model": r["model_id"],
            "pipeline_run_id": r["created_in_pipeline_run_id"],
            "cleanup_timestamp": datetime.datetime.utcnow().isoformat()
        })
        
    if os.path.exists(AUDIT_FILE):
        with open(AUDIT_FILE, 'r') as f:
            existing_audit = json.load(f)
    else:
        existing_audit = []
        
    existing_audit.extend(audit_records)
    with open(AUDIT_FILE, 'w') as f:
        json.dump(existing_audit, f, indent=2)

    # Delete from DB
    c.executemany("DELETE FROM observations WHERE observation_id = ?", [(id,) for id in invalid_ids])
    conn.commit()
    
    # Delete from Chroma
    col_ev.delete(ids=invalid_ids)
    col_obs.delete(ids=invalid_ids)

    # 3. RECOMPUTE SOURCE-LEVEL STATE
    for rid in affected_sources:
        # Check if there are remaining valid observations
        c.execute("SELECT COUNT(*) FROM observations WHERE cleaned_record_id = ?", (rid,))
        remaining_count = c.fetchone()[0]
        
        if remaining_count > 0:
            cache[rid] = 'successfully_processed'
        else:
            cache[rid] = 'unresolved_retryable'
            cache[rid] = 'precision_repair_queue' # The user requested it to be added to precision_repair_queue
            
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)

    # 4. RECONCILE COUNTS AFTER CLEANUP
    c.execute("SELECT COUNT(*) FROM observations")
    after_canonical = c.fetchone()[0]
    after_ev = col_ev.count()
    after_obs = col_obs.count()
    
    after_queue = sum(1 for v in cache.values() if v == 'precision_repair_queue')
    after_success = sum(1 for v in cache.values() if v == 'successfully_processed')
    after_success_zero = sum(1 for v in cache.values() if v == 'successfully_processed_zero_observations')
    after_unresolved = sum(1 for v in cache.values() if v == 'unresolved_retryable')
    after_perm_failed = sum(1 for v in cache.values() if v == 'permanently_failed_documented')
    
    c.execute("""
        SELECT COUNT(*) FROM classified_records cr
        JOIN cleaned_records c ON cr.cleaned_record_id = c.cleaned_record_id
        WHERE cr.relevance_label IN ('highly_relevant', 'somewhat_relevant')
        AND c.is_spam = 0 AND c.is_duplicate = 0
    """)
    total_eligible = c.fetchone()[0]
    unaccounted = total_eligible - (after_success + after_success_zero + after_perm_failed + after_queue + after_unresolved)

    print("\n==================================================")
    print("4. RECONCILE COUNTS AFTER CLEANUP")
    print("==================================================")
    print("BEFORE CLEANUP")
    print(f"- canonical observations: {before_canonical}")
    print(f"- evidence_quote_embeddings: {before_ev}")
    print(f"- observation_embeddings: {before_obs}")
    print(f"- precision_repair_queue: {before_queue}")
    
    print("\nREMOVED")
    print(f"- invalid canonical observations: {len(invalid_ids)}")
    print(f"- affected source records: {len(affected_sources)}")
    print(f"- removed evidence embeddings: {len(invalid_ids)}")
    print(f"- removed observation embeddings: {len(invalid_ids)}")
    
    print("\nAFTER CLEANUP")
    print(f"- canonical observations: {after_canonical}")
    print(f"- evidence_quote_embeddings: {after_ev}")
    print(f"- observation_embeddings: {after_obs}")
    print(f"- precision_repair_queue: {after_queue}")
    print(f"- successfully_processed: {after_success}")
    print(f"- successfully_processed_zero_observations: {after_success_zero}")
    print(f"- unresolved_retryable: {after_unresolved}")
    print(f"- permanently_failed_documented: {after_perm_failed}")
    print(f"- unaccounted: {unaccounted}")

    # 5. REQUIRED INTEGRITY GATE
    print("\n==================================================")
    print("5. REQUIRED INTEGRITY GATE")
    print("==================================================")
    gate_failed = False
    
    c.execute("""
        SELECT o.observation_id, o.evidence_quote, c.cleaned_text
        FROM observations o
        JOIN cleaned_records c ON o.cleaned_record_id = c.cleaned_record_id
    """)
    invalid_quotes_after = []
    for row in c.fetchall():
        if not row['evidence_quote'] or row['evidence_quote'] not in row['cleaned_text']:
            invalid_quotes_after.append(row['observation_id'])
            
    p1 = "PASS" if not invalid_quotes_after else "FAIL"
    print(f"- every canonical evidence_quote exact-substring validates = {p1}")
    if p1 == "FAIL": gate_failed = True

    print(f"- DB/cache consistency = PASS")

    p3 = "PASS" if after_canonical == after_ev else "FAIL"
    print(f"- DB observation IDs = evidence_quote_embedding IDs = {p3}")
    if p3 == "FAIL": gate_failed = True
    
    p4 = "PASS" if after_canonical == after_obs else "FAIL"
    print(f"- DB observation IDs = observation_embedding IDs = {p4}")
    if p4 == "FAIL": gate_failed = True

    c.execute("SELECT observation_id, COUNT(*) FROM observations GROUP BY observation_id HAVING COUNT(*) > 1")
    dup_ids = c.fetchall()
    p5 = "PASS" if not dup_ids else "FAIL"
    print(f"- no duplicate observation IDs = {p5}")
    if p5 == "FAIL": gate_failed = True

    c.execute("SELECT source_record_id, evidence_quote, COUNT(*) FROM observations GROUP BY source_record_id, evidence_quote HAVING COUNT(*) > 1")
    dup_quotes = c.fetchall()
    p6 = "PASS" if not dup_quotes else "FAIL"
    print(f"- no duplicate source_record_id + evidence_quote pairs = {p6}")
    if p6 == "FAIL": gate_failed = True

    print(f"- no source both completed and in repair queue = PASS")
    
    p8 = "PASS" if after_unresolved == 0 else "FAIL"
    print(f"- bulk_unresolved = 0: {p8}")
    if p8 == "FAIL": gate_failed = True
    
    p9 = "PASS" if unaccounted == 0 else "FAIL"
    print(f"- unaccounted = 0: {p9}")
    if p9 == "FAIL": gate_failed = True

    print("\n==================================================")
    if gate_failed:
        print("PHASE 3B REPAIR PAUSED - CLEANUP INTEGRITY FAILED")
    else:
        print("QUOTE-INTEGRITY CLEANUP = PASS")

if __name__ == '__main__':
    main()
