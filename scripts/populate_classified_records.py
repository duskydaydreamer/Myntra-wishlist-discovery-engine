import json
import sqlite3
import os

CACHE_FILES = ["data/phase2_calibration_cache.json", "data/phase2b_scaling_cache.json"]

def load_caches():
    cache = {}
    for f_path in CACHE_FILES:
        if os.path.exists(f_path):
            with open(f_path, "r") as f:
                try: cache.update(json.load(f))
                except: pass
    return cache

def main():
    cache = load_caches()
    db_path = "data/discovery_pulse.db"
    conn = sqlite3.connect(db_path)
    
    records = []
    import uuid
    
    for cleaned_id, v in cache.items():
        if v.get("success"):
            label = v["parsed"]["relevance_label"]
            signals = json.dumps(v["parsed"]["signals_detected"])
            classified_id = "class_" + str(uuid.uuid4())
            records.append((classified_id, cleaned_id, label, -1.0, signals))
            
    print(f"Inserting {len(records)} records into classified_records table...")
    
    conn.execute("DELETE FROM classified_records")
    conn.executemany("""
    INSERT INTO classified_records (classified_record_id, cleaned_record_id, relevance_label, relevance_confidence, signals_detected)
    VALUES (?, ?, ?, ?, ?)
    """, records)
    conn.commit()
    conn.close()
    print("Done.")

if __name__ == "__main__":
    main()
