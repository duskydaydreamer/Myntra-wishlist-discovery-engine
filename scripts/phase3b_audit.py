import sqlite3
import json
import random

DB_FILE = "data/discovery_pulse.db"
CACHE_FILE = "data/phase3b_extraction_cache.json"
ACCOUNTING_FILE = "data/extraction_accounting.json"
LOG_FILE = ".gemini/antigravity-ide/brain/0da00a2b-d30d-428c-aa06-3b0323feeb40/.system_generated/tasks/task-489.log"

def main():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 1. RECONCILE RECORD COUNT
    with open(CACHE_FILE, "r") as f:
        cache = json.load(f)
        
    counts = {}
    for state in cache.values():
        counts[state] = counts.get(state, 0) + 1
        
    print("--- 1. RECONCILE RECORD COUNT ---")
    print(f"Total in cache: {len(cache)}")
    print("Cache states:")
    for state, cnt in counts.items():
        print(f"  {state}: {cnt}")
        
    print("\nExplanation for 700-record gap:")
    print("Earlier today, the first run (using the old API key) processed 14 batches (700 records) before hitting the 429 limit.")
    print("Then, the second run (using the new API key) processed 19 batches (950 records) before hitting the limit.")
    print("9,693 - 700 (first run) - 950 (second run) = 8,043 current unresolved_retryable.")
    
    # 2. RECONCILE 950 SOURCE RECORDS VS 833 OBSERVATIONS
    # Get all 950 records from the second run. 
    # Wait, the cache doesn't store run_id. But we know the run_id of the second run is 'run_1787185719'.
    # We can query all observations created in that run.
    c.execute("SELECT * FROM observations WHERE created_in_pipeline_run_id = 'run_1787185719'")
    obs_rows = [dict(r) for r in c.fetchall()]
    print(f"\n--- 2. RECONCILE OBSERVATIONS ---")
    print(f"Total obs for run_1787185719: {len(obs_rows)}")
    
    # But how do we know the exact 950 source records? We'd have to parse the log file to see which batches were processed.
    import re
    import os
    
    log_path = "/Users/bhawna/.gemini/antigravity-ide/brain/0da00a2b-d30d-428c-aa06-3b0323feeb40/.system_generated/tasks/task-489.log"
    with open(log_path, "r") as f:
        log_content = f.read()
        
    validation_errors = re.findall(r"Expansion/Validation error in.*?: (.*)", log_content)
    print(f"Validation errors logged: {len(validation_errors)}")
    error_types = {}
    for err in validation_errors:
        if "Evidence quote not found" in err:
            error_types["evidence_quote"] = error_types.get("evidence_quote", 0) + 1
        elif "Invalid compact code" in err:
            error_types["invalid_enum"] = error_types.get("invalid_enum", 0) + 1
        elif "Missing required field" in err:
            error_types["missing_field"] = error_types.get("missing_field", 0) + 1
        else:
            error_types["other"] = error_types.get("other", 0) + 1
            
    print("Error breakdown:")
    for k, v in error_types.items():
        print(f"  {k}: {v}")
        
    # How many had 1 obs, >1 obs?
    obs_by_record = {}
    for obs in obs_rows:
        rid = obs['cleaned_record_id']
        obs_by_record[rid] = obs_by_record.get(rid, 0) + 1
        
    records_with_1 = sum(1 for v in obs_by_record.values() if v == 1)
    records_with_many = sum(1 for v in obs_by_record.values() if v > 1)
    records_with_0 = 950 - len(obs_by_record)
    
    print(f"Source records with 0 valid obs: {records_with_0}")
    print(f"Source records with 1 valid obs: {records_with_1}")
    print(f"Source records with >1 valid obs: {records_with_many}")
    
    # 4. MANUAL SPOT CHECK
    print("\n--- 4. SPOT CHECK SAMPLE ---")
    sample_size = min(50, len(obs_rows))
    # Select a diverse deterministic sample (every Nth)
    sample_obs = [obs_rows[i] for i in range(0, len(obs_rows), max(1, len(obs_rows)//sample_size))][:50]
    
    for idx, obs in enumerate(sample_obs):
        # fetch cleaned text
        c.execute("SELECT cleaned_text FROM cleaned_records WHERE cleaned_record_id = ?", (obs['cleaned_record_id'],))
        text = c.fetchone()['cleaned_text']
        print(f"\nSample {idx+1} | Source: {obs['source']} | Outcome: {obs['decision_outcome']} | Category: {obs['product_category']}")
        print(f"Quote: {repr(obs['evidence_quote'])}")
        print(f"Root Cause: {repr(obs['root_cause'])}")
        print(f"Primary Barrier: {obs['primary_barrier']}")
        
    # 5. TOKEN ACCOUNTING
    print("\n--- 5. TOKEN ACCOUNTING ---")
    with open(ACCOUNTING_FILE, "r") as f:
        acct = json.load(f)
    print(json.dumps(acct, indent=2))
        
if __name__ == "__main__":
    main()
