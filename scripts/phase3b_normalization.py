import sqlite3
import json
import os

DB_FILE = "data/discovery_pulse.db"
CACHE_FILE = "data/phase3b_extraction_cache.json"

def main():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Get all eligible records
    cursor.execute("""
        SELECT c.cleaned_record_id, r.raw_record_id
        FROM classified_records cr
        JOIN cleaned_records c ON cr.cleaned_record_id = c.cleaned_record_id
        JOIN raw_records r ON c.raw_record_id = r.raw_record_id
        WHERE cr.relevance_label IN ('highly_relevant', 'somewhat_relevant')
        AND c.is_spam = 0 AND c.is_duplicate = 0
    """)
    eligible_records = [dict(row) for row in cursor.fetchall()]
    eligible_ids = {r["cleaned_record_id"] for r in eligible_records}
    print(f"Total eligible records (DB): {len(eligible_ids)}")

    # 2. Get records that have successful extraction artifacts in DB
    cursor.execute("SELECT DISTINCT cleaned_record_id FROM observations")
    db_extracted_ids = {row[0] for row in cursor.fetchall()}
    
    # 3. Read cache file
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
    else:
        cache = {}
        
    # Count variables
    successfully_processed = 0
    successfully_processed_zero_observations = 0
    permanently_failed = 0
    unresolved_retryable = 0
    
    # Normalizing
    for cid in eligible_ids:
        if cid in db_extracted_ids:
            # Must be successfully extracted
            cache[cid] = "successfully_extracted"
            successfully_processed += 1
        elif cache.get(cid) == "successfully_processed_zero_observations":
            successfully_processed_zero_observations += 1
        elif cache.get(cid) == "permanently_failed":
            permanently_failed += 1
        else:
            # Unaccounted or previously unresolved -> mark unresolved_retryable
            cache[cid] = "unresolved_retryable"
            unresolved_retryable += 1

    # Save cache
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)
        
    # Verify
    total_accounted = (successfully_processed + successfully_processed_zero_observations + 
                       unresolved_retryable + permanently_failed)
    unaccounted = len(eligible_ids) - total_accounted
    
    print("--- NORMALIZATION REPORT ---")
    print(f"eligible = {len(eligible_ids)}")
    print(f"successfully_processed (in DB) = {successfully_processed}")
    print(f"successfully_processed_zero_observations (in Cache) = {successfully_processed_zero_observations}")
    print(f"unresolved_retryable = {unresolved_retryable}")
    print(f"permanently_failed = {permanently_failed}")
    print(f"unaccounted = {unaccounted}")

if __name__ == "__main__":
    main()
