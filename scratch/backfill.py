import json
import sqlite3
import datetime

def run_backfill():
    db_path = "data/discovery_pulse.db"
    conn = sqlite3.connect(db_path)
    
    # Load canonical observation counts per record
    obs_counts_raw = conn.execute("""
        SELECT source_record_id, count(*) 
        FROM observations 
        GROUP BY source_record_id
    """).fetchall()
    
    obs_counts = {row[0]: row[1] for row in obs_counts_raw}
    
    now = datetime.datetime.utcnow().isoformat()
    
    with open("data/phase3b_extraction_cache.json", "r") as f:
        cache = json.load(f)
        
    upsert_data = []
    
    for record_id, status in cache.items():
        if status == "successfully_extracted":
            # Rule 1
            count = obs_counts.get(record_id, 0)
            upsert_data.append((record_id, "successfully_extracted", count, now))
        elif status == "successfully_processed_zero_observations":
            # Rule 2
            upsert_data.append((record_id, "successfully_processed_zero_observations", 0, now))
        else:
            # Rule 3 (failures)
            upsert_data.append((record_id, "failed", 0, now))
            
    conn.executemany("""
        INSERT INTO extraction_tracker (cleaned_record_id, status, observation_count, completed_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(cleaned_record_id) DO UPDATE SET
            status = excluded.status,
            observation_count = excluded.observation_count,
            completed_at = excluded.completed_at
    """, upsert_data)
    conn.commit()
    
    # Final check
    total = conn.execute("SELECT count(*) FROM extraction_tracker").fetchone()[0]
    total_success = conn.execute("SELECT count(*) FROM extraction_tracker WHERE status = 'successfully_extracted'").fetchone()[0]
    total_zero = conn.execute("SELECT count(*) FROM extraction_tracker WHERE status = 'successfully_processed_zero_observations'").fetchone()[0]
    total_fail = conn.execute("SELECT count(*) FROM extraction_tracker WHERE status = 'failed'").fetchone()[0]
    
    print(f"EXTRACTION_TRACKER TOTAL: {total}")
    print(f"SUCCESSFULLY_EXTRACTED: {total_success}")
    print(f"SUCCESSFULLY_PROCESSED_ZERO_OBSERVATIONS: {total_zero}")
    print(f"FAILED / RETRY-ELIGIBLE: {total_fail}")
    print(f"TRACKER COVERAGE OF PHASE3 ELIGIBLE: {total}/9749")
    
run_backfill()
