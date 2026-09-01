import sqlite3
import json
import random
import os

def create_manifest():
    print("Creating frozen evaluation manifest...")
    conn = sqlite3.connect("data/discovery_pulse.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Find ALREADY-PROCESSED records
    # We define this as records that have an entry in run_records for completed runs
    # Specifically we can look at raw_record_id that already have observations,
    # OR were in a run and resulted in zero observations.
    
    # Let's get all raw_record_ids that were part of a completed pipeline run.
    cursor.execute("""
        SELECT DISTINCT rr.raw_record_id
        FROM run_records rr
        JOIN pipeline_runs pr ON rr.pipeline_run_id = pr.run_id
        WHERE pr.status = 'completed'
    """)
    processed_raw_ids = [row["raw_record_id"] for row in cursor.fetchall()]
    print(f"Found {len(processed_raw_ids)} processed raw_record_ids.")

    if not processed_raw_ids:
        # Fallback to observations table
        cursor.execute("SELECT DISTINCT source_record_id FROM observations")
        processed_raw_ids = [row["source_record_id"] for row in cursor.fetchall()]
        print(f"Fallback: {len(processed_raw_ids)} raw_record_ids from observations.")

    processed_set = set(processed_raw_ids)

    # Get data for selection
    cursor.execute("""
        SELECT r.raw_record_id, r.source, r.language, c.cleaned_text, cr.relevance_label
        FROM raw_records r
        JOIN cleaned_records c ON r.raw_record_id = c.raw_record_id
        JOIN classified_records cr ON c.cleaned_record_id = cr.cleaned_record_id
        WHERE r.raw_record_id IN ({})
    """.format(','.join('?' for _ in processed_raw_ids)), processed_raw_ids)
    
    candidates = [dict(row) for row in cursor.fetchall()]
    
    # Also fetch existing observations for these to find stress cases
    cursor.execute("""
        SELECT source_record_id, primary_barrier, decision_outcome, uncertainty
        FROM observations
        WHERE source_record_id IN ({})
    """.format(','.join('?' for _ in processed_raw_ids)), processed_raw_ids)
    
    obs_by_record = {}
    for row in cursor.fetchall():
        rid = row["source_record_id"]
        if rid not in obs_by_record:
            obs_by_record[rid] = []
        obs_by_record[rid].append(dict(row))

    # Helper for text length bucket
    def get_length_bucket(text):
        words = len(text.split())
        if words < 20: return "short"
        if words < 60: return "medium"
        return "long"

    # Identify stress cases
    stress_candidates = []
    representative_candidates = []
    
    for c in candidates:
        rid = c["raw_record_id"]
        obs = obs_by_record.get(rid, [])
        is_stress = False
        reason = ""
        
        # Determine if it's a stress case based on rules
        if not obs:
            is_stress = True
            reason = "zero-observation"
        elif len(obs) > 1:
            is_stress = True
            reason = "multiple observations"
        else:
            for o in obs:
                pb = o.get("primary_barrier")
                do = o.get("decision_outcome")
                if pb in ["delivery", "returns", "fit/size", "quality", "trust", "comparison"]:
                    is_stress = True
                    reason = f"barrier:{pb}"
                if do == "unknown" or not do or do == "?":
                    is_stress = True
                    reason = "ambiguous outcome"
                if o.get("uncertainty") and o.get("uncertainty") != "unknown":
                    is_stress = True
                    reason = "contains uncertainty"
        
        if is_stress:
            stress_candidates.append((c, reason))
        else:
            representative_candidates.append(c)

    random.seed(42)  # Fixed seed

    print(f"Candidates for stress: {len(stress_candidates)}, representative: {len(representative_candidates)}")

    # Ensure we can pick exactly 30 stress and 70 representative
    # If not enough representative, we can take from stress.
    
    random.shuffle(stress_candidates)
    random.shuffle(representative_candidates)
    
    manifest = []
    
    for c, reason in stress_candidates[:30]:
        manifest.append({
            "source_record_id": c["raw_record_id"],
            "subset": "stress",
            "selection_reason": reason,
            "relevance_class": c["relevance_label"],
            "source": c["source"],
            "text_length": get_length_bucket(c["cleaned_text"]),
            "original_batch": "unknown"  # Will lookup if needed
        })
        
    for c in representative_candidates[:70]:
        manifest.append({
            "source_record_id": c["raw_record_id"],
            "subset": "representative",
            "selection_reason": "random_stratified",
            "relevance_class": c["relevance_label"],
            "source": c["source"],
            "text_length": get_length_bucket(c["cleaned_text"]),
            "original_batch": "unknown"
        })
        
    # If we didn't get enough representative, fill from stress
    while len(manifest) < 100 and stress_candidates[30:]:
        c, reason = stress_candidates.pop(30)
        manifest.append({
            "source_record_id": c["raw_record_id"],
            "subset": "representative",
            "selection_reason": "filled_from_stress",
            "relevance_class": c["relevance_label"],
            "source": c["source"],
            "text_length": get_length_bucket(c["cleaned_text"]),
            "original_batch": "unknown"
        })

    print(f"Final manifest size: {len(manifest)}")
    
    with open("data/eval_manifest_100.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print("Manifest saved to data/eval_manifest_100.json")

if __name__ == "__main__":
    if not os.path.exists("data/eval_manifest_100.json"):
        create_manifest()
    else:
        print("data/eval_manifest_100.json already exists. Using frozen version.")
