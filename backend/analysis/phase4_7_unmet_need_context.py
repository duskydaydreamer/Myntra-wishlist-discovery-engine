"""
Task 4.7 — Unmet-Need Contextualization
=========================================
Expands the raw unmet_need_taxonomy into a rich, contextualized dataset.
For each unmet need, aggregates frequency, associated barriers, intents, 
and representative quotes from the clusters that share it.

Outputs:
- data/phase4/unmet_need_context.jsonl
- DB update: unmet_need_context
"""

import json
import os
import sqlite3
from collections import Counter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "discovery_pulse.db")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "phase4")
CONTEXT_PATH = os.path.join(OUTPUT_DIR, "unmet_need_context.jsonl")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS unmet_need_context (
            unmet_need TEXT PRIMARY KEY,
            observation_count INTEGER,
            associated_barriers_json TEXT,
            associated_intents_json TEXT
        );
    """)
    conn.commit()
    return conn


def get_unmet_needs(conn):
    rows = conn.execute("SELECT cluster_id, primary_unmet_need FROM cluster_synthesis").fetchall()
    
    # map unmet_need -> list of cluster_ids
    needs = {}
    for cid, un in rows:
        if un and un.lower() != "unknown":
            needs.setdefault(un.strip(), []).append(cid)
    return needs


def process_unmet_need(conn, un, cluster_ids):
    placeholders = ",".join(["?"] * len(cluster_ids))
    
    # Frequency
    count_row = conn.execute(
        f"SELECT SUM(observation_count) FROM cluster_aggregations WHERE cluster_id IN ({placeholders})",
        cluster_ids
    ).fetchone()
    frequency = count_row[0] or 0
    
    # Aggregated distributions
    dists = conn.execute(
        f"SELECT distributions_json FROM cluster_aggregations WHERE cluster_id IN ({placeholders})",
        cluster_ids
    ).fetchall()
    
    barrier_counter = Counter()
    intent_counter = Counter()
    
    for (d_json,) in dists:
        if not d_json: continue
        d = json.loads(d_json)
        
        for k, v in d.get("primary_barrier", {}).items():
            barrier_counter[k] += v
            
        for k, v in d.get("wishlist_intent", {}).items():
            intent_counter[k] += v
        for k, v in d.get("purchase_intent", {}).items():
            intent_counter[k] += v
            
    # Quotes
    quotes = conn.execute(
        f"SELECT evidence_quote FROM cluster_representatives WHERE cluster_id IN ({placeholders}) LIMIT 3",
        cluster_ids
    ).fetchall()
    
    return {
        "unmet_need": un,
        "frequency": frequency,
        "associated_barriers": [k for k, _ in barrier_counter.most_common(5)],
        "associated_intents": [k for k, _ in intent_counter.most_common(5)],
        "supporting_quotes": [q[0] for q in quotes]
    }


def run_unmet_need_context(run_id="run_latest"):
    db_path = "data/discovery_pulse.db"
    print("=" * 60)
    print("PHASE 4 TASK 4.7 — Unmet-Need Contextualization")
    print("=" * 60)
    
    conn = init_db()
    needs_map = get_unmet_needs(conn)
    print(f"Found {len(needs_map)} unmet needs to contextualize.")
    
    context_data = []
    to_insert = []
    
    for un, cluster_ids in needs_map.items():
        ctx = process_unmet_need(conn, un, cluster_ids)
        context_data.append(ctx)
        
        to_insert.append((
            ctx["unmet_need"],
            ctx["frequency"],
            json.dumps(ctx["associated_barriers"]),
            json.dumps(ctx["associated_intents"])
        ))
        
    print("Persisting to DB...")
    conn.execute("DELETE FROM unmet_need_context")
    conn.executemany(
        """INSERT INTO unmet_need_context 
           (unmet_need, observation_count, associated_barriers_json, associated_intents_json)
           VALUES (?, ?, ?, ?)""",
        to_insert
    )
    conn.commit()
    conn.close()
    
    print("Writing JSONL artifact...")
    with open(CONTEXT_PATH, "w") as f:
        for item in context_data:
            f.write(json.dumps(item) + "\n")
            
    print("\n" + "=" * 60)
    print("TASK 4.7 SUMMARY")
    print("=" * 60)
    print(f"Contextualized Needs: {len(context_data)}")
    
    gate_pass = len(context_data) > 0
    print(f"\nIntegrity gate: PROCEED to Task 4.8")
    print(f"Gate result: {'PASS ✓' if gate_pass else 'FAIL ✗ — STOP AND REPORT'}")
    return gate_pass


if __name__ == "__main__":
    passed = run_unmet_need_context()
    exit(0 if passed else 1)
