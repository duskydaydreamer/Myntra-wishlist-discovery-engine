import json
import sqlite3
import uuid
from datetime import datetime

DB_FILE = "data/discovery_pulse.db"
RUN_ID = "phase3a_migration"

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

def insert_obs(obs):
    obs_id = uuid.uuid4().hex
    # check if evidence_quote matches cleaned_text
    cursor.execute("SELECT cleaned_text, cleaned_records.raw_record_id, source, source_url FROM cleaned_records JOIN raw_records ON cleaned_records.raw_record_id = raw_records.raw_record_id WHERE cleaned_record_id = ?", (obs["source_record_id"],))
    row = cursor.fetchone()
    if not row: return False
    cleaned_text, raw_record_id, source, source_url = row
    
    quote = obs["extracted"].get("evidence_quote")
    if quote != "?" and quote not in cleaned_text:
        return False
        
    db_obs = {
        "observation_id": obs_id,
        "source_record_id": raw_record_id,
        "cleaned_record_id": obs["source_record_id"],
        "source": source,
        "source_url": source_url,
        "evidence_quote": quote,
        "extracted_at": datetime.utcnow().isoformat(),
        "model_id": "gemini-3.6-flash",
        "prompt_version": "v2-compact-phase3a",
        "created_in_pipeline_run_id": RUN_ID,
    }
    
    for k, v in obs["extracted"].items():
        if k not in ["evidence_quote", "local_index"]:
            if isinstance(v, list): v = json.dumps(v)
            db_obs[k] = v
            
    cols = list(db_obs.keys())
    sql = f"INSERT INTO observations ({','.join(cols)}) VALUES ({','.join(['?' for _ in cols])})"
    cursor.execute(sql, [db_obs[c] for c in cols])
    return True

cache = {}
count = 0
for f in ["data/phase3a_eval_results.json", "data/phase3a_remaining_results.json"]:
    try:
        with open(f, "r") as fh:
            data = json.load(fh)
            for d in data:
                if insert_obs(d):
                    cache[d["source_record_id"]] = "successfully_extracted"
                    count += 1
    except Exception as e:
        print(f, e)

conn.commit()
with open("data/phase3b_extraction_cache.json", "w") as fh:
    json.dump(cache, fh)

print(f"Migrated {count} valid observations.")
conn.close()
