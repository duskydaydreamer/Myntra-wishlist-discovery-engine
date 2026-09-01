import sqlite3
import chromadb
import json

def check_integrity():
    conn = sqlite3.connect("data/discovery_pulse.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("Running Evidence Store Integrity Check...\n")
    
    # Check 1: Observation maps to valid canonical source
    cursor.execute("""
        SELECT COUNT(*) FROM observations o
        LEFT JOIN raw_records r ON o.source_record_id = r.raw_record_id
        WHERE r.raw_record_id IS NULL
    """)
    orphan_obs = cursor.fetchone()[0]
    print(f"1. Observations without valid raw_record_id: {orphan_obs}")
    
    # Check 2: No spam/duplicate entered extraction
    cursor.execute("""
        SELECT COUNT(*) FROM observations o
        JOIN cleaned_records c ON o.cleaned_record_id = c.cleaned_record_id
        WHERE c.is_spam = 1 OR c.is_duplicate = 1
    """)
    spam_obs = cursor.fetchone()[0]
    print(f"2. Observations from spam/duplicate records: {spam_obs}")
    
    # Check 3: Non-empty evidence_quote and substring verifiable
    cursor.execute("""
        SELECT o.observation_id, o.evidence_quote, c.cleaned_text
        FROM observations o
        JOIN cleaned_records c ON o.cleaned_record_id = c.cleaned_record_id
    """)
    rows = cursor.fetchall()
    empty_quotes = 0
    invalid_quotes = 0
    for r in rows:
        q = r["evidence_quote"]
        if not q or q.strip() == "" or q == "?":
            empty_quotes += 1
        elif q not in r["cleaned_text"]:
            invalid_quotes += 1
            
    print(f"3. Empty evidence quotes: {empty_quotes}")
    print(f"4. Invalid substring evidence quotes: {invalid_quotes}")
    
    # Check 4: valid taxonomy values
    cursor.execute("""
        SELECT journey_stage, wishlist_intent, purchase_intent, primary_barrier, decision_outcome
        FROM observations
    """)
    tax_rows = cursor.fetchall()
    invalid_tax = 0
    for r in tax_rows:
        if r["journey_stage"] not in ["discovery", "evaluation", "purchase", "post_purchase", "unknown"]: invalid_tax += 1
        if r["purchase_intent"] not in ["high", "low", "none", "unknown"]: invalid_tax += 1
    print(f"5. Invalid taxonomy values: {invalid_tax}")
    
    # Check 5: No local index as canonical identity
    cursor.execute("""
        SELECT COUNT(*) FROM observations WHERE CAST(observation_id AS INTEGER) = observation_id
    """)
    try:
        local_ids = cursor.fetchone()[0]
    except:
        local_ids = 0
    print(f"6. Local indexes as canonical IDs: {local_ids}")
    
    # Check 6: No duplicates
    cursor.execute("""
        SELECT observation_id, COUNT(*) FROM observations GROUP BY observation_id HAVING COUNT(*) > 1
    """)
    dup_ids = len(cursor.fetchall())
    print(f"7. Duplicate observation IDs: {dup_ids}")
    
    # Check 7: Cache matches DB state
    try:
        with open("data/phase3b_extraction_cache.json") as f:
            cache = json.load(f)
            extracted_cache = sum(1 for v in cache.values() if v == "successfully_extracted")
    except:
        extracted_cache = 0
        
    cursor.execute("SELECT COUNT(DISTINCT cleaned_record_id) FROM observations")
    db_extracted = cursor.fetchone()[0]
    print(f"8. Cache extracted count: {extracted_cache}, DB extracted count: {db_extracted}")
    
    # Check 8: Embeddings reference valid IDs and count
    client = chromadb.PersistentClient("data/chroma")
    col_ev = client.get_or_create_collection("evidence_quote_embeddings")
    col_obs = client.get_or_create_collection("observation_embeddings")
    
    ev_count = col_ev.count()
    obs_count = col_obs.count()
    print(f"9. Embeddings counts: evidence_quotes={ev_count}, observations={obs_count}")
    
    db_obs_count = len(rows)
    print(f"10. Database observations count: {db_obs_count}")
    
    if ev_count > 0:
        ev_ids = set(col_ev.get()["ids"])
        obs_db_ids = set([r["observation_id"] for r in rows])
        missing_ev = len(ev_ids - obs_db_ids)
        print(f"11. Embedding IDs not in DB: {missing_ev}")
    
    print("\nIntegrity check complete.")

if __name__ == "__main__":
    check_integrity()
