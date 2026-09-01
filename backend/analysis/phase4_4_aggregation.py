"""
Task 4.4 — Theme/Cluster Aggregation & Representative Evidence
==============================================================
Computes deterministic statistics for all predefined themes and 
emergent clusters.

Selects representative quotes using semantic centrality (distance to centroid)
combined with source diversity and exact text deduplication.

Outputs:
- data/phase4/cluster_representatives.jsonl
- DB update: semantic_clusters (aggregates), cluster_representatives
"""

import json
import os
import sqlite3
import time
from collections import Counter
from datetime import datetime, timezone

import chromadb
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "discovery_pulse.db")
CHROMA_PATH = os.environ.get("CHROMA_PATH", os.path.join(BASE_DIR, "data", "chroma"))
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "phase4")
REP_PATH = os.path.join(OUTPUT_DIR, "cluster_representatives.jsonl")

NUM_REPRESENTATIVE_QUOTES = 7


def load_embeddings():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    col = client.get_collection("observation_embeddings")
    res = col.get(include=["embeddings"])
    return res["ids"], np.array(res["embeddings"], dtype=np.float32)


def get_observation_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM observations").fetchall()
    conn.close()
    return {r["observation_id"]: dict(r) for r in rows}


def get_cluster_memberships():
    conn = sqlite3.connect(DB_PATH)
    
    # Predefined themes
    pt = conn.execute("SELECT predefined_theme_id, observation_id FROM theme_assignments").fetchall()
    # Emergent clusters
    ec = conn.execute("SELECT cluster_id, observation_id FROM cluster_memberships WHERE membership_probability > 0").fetchall()
    conn.close()
    
    memberships = {}
    for theme_id, obs_id in pt:
        memberships.setdefault(theme_id, []).append(obs_id)
        
    for cluster_id, obs_id in ec:
        if cluster_id != "cluster_noise":
            memberships.setdefault(cluster_id, []).append(obs_id)
            
    return memberships


def compute_distribution(observations, key):
    counter = Counter(obs.get(key) for obs in observations)
    # Remove empty/None values for cleaner stats
    if "" in counter: del counter[""]
    if None in counter: del counter[None]
    return dict(counter)


def select_representatives(cluster_id, obs_ids, obs_data, embeddings, all_ids_list):
    """
    Select representative quotes by finding the semantic medoid (centroid),
    ranking by similarity to centroid, and filtering for exact text uniqueness
    and source diversity.
    """
    if not obs_ids:
        return []
        
    # Get indices for these obs_ids
    id_to_idx = {i_id: idx for idx, i_id in enumerate(all_ids_list)}
    indices = [id_to_idx[oid] for oid in obs_ids if oid in id_to_idx]
    
    if not indices:
        return []
        
    cluster_embs = embeddings[indices]
    centroid = np.mean(cluster_embs, axis=0).reshape(1, -1)
    
    # Cosine similarity to centroid
    sims = cosine_similarity(cluster_embs, centroid).flatten()
    
    # Sort indices by highest similarity
    ranked_local_indices = np.argsort(sims)[::-1]
    
    selected = []
    seen_quotes = set()
    seen_sources = set()
    
    # Pass 1: Try to get unique sources + unique text
    for i in ranked_local_indices:
        if len(selected) >= NUM_REPRESENTATIVE_QUOTES:
            break
            
        oid = obs_ids[i]
        obs = obs_data[oid]
        quote = obs.get("evidence_quote", "").strip()
        src = obs.get("source", "")
        
        if not quote or quote in seen_quotes:
            continue
            
        if src in seen_sources and len(seen_sources) < 3: 
            # Force source diversity if we haven't seen at least 3 sources yet
            continue
            
        selected.append(obs)
        seen_quotes.add(quote)
        seen_sources.add(src)
        
    # Pass 2: If we didn't hit the quota, relax the unique source constraint
    if len(selected) < NUM_REPRESENTATIVE_QUOTES:
        for i in ranked_local_indices:
            if len(selected) >= NUM_REPRESENTATIVE_QUOTES:
                break
                
            oid = obs_ids[i]
            obs = obs_data[oid]
            quote = obs.get("evidence_quote", "").strip()
            
            if quote and quote not in seen_quotes:
                selected.append(obs)
                seen_quotes.add(quote)
                
    # Format the selected representatives
    reps = []
    for obs in selected:
        reps.append({
            "observation_id": obs["observation_id"],
            "source_record_id": obs["source_record_id"],
            "evidence_quote": obs["evidence_quote"],
            "source": obs["source"],
            "source_url": obs["source_url"],
            "primary_barrier": obs["primary_barrier"],
            "uncertainty": obs["uncertainty"]
        })
    return reps


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS cluster_representatives (
            analysis_run_id TEXT,
            cluster_id TEXT,
            observation_id TEXT,
            source_record_id TEXT,
            evidence_quote TEXT,
            source TEXT,
            source_url TEXT,
            primary_barrier TEXT,
            uncertainty TEXT
        );
        CREATE TABLE IF NOT EXISTS cluster_aggregations (
            analysis_run_id TEXT,
            cluster_id TEXT PRIMARY KEY,
            observation_count INTEGER,
            unique_source_count INTEGER,
            distributions_json TEXT
        );
    """)
    conn.commit()
    return conn


def run_aggregation(run_id="run_latest"):
    db_path = "data/discovery_pulse.db"
    print("=" * 60)
    print("PHASE 4 TASK 4.4 — Theme/Cluster Aggregation")
    print("=" * 60)
    
        conn = init_db()
    
    print("Loading observations and memberships...")
    obs_data = get_observation_data()
    memberships = get_cluster_memberships()
    print(f"Found {len(memberships)} themes/clusters to aggregate.")
    
    print("Loading embeddings for representative selection...")
    all_ids_list, embeddings = load_embeddings()
    
    aggregations = []
    representatives_jsonl = []
    representatives_to_insert = []
    
    total_clusters = len(memberships)
    
    print("Computing aggregations and representatives...")
    for idx, (cluster_id, obs_ids) in enumerate(memberships.items()):
        if idx % 10 == 0:
            print(f"  Processed {idx}/{total_clusters}...")
            
        cluster_obs = [obs_data[oid] for oid in obs_ids]
        
        obs_count = len(cluster_obs)
        unique_sources = len(set(o["source_record_id"] for o in cluster_obs))
        
        dists = {
            "source": compute_distribution(cluster_obs, "source"),
            "primary_barrier": compute_distribution(cluster_obs, "primary_barrier"),
            "wishlist_intent": compute_distribution(cluster_obs, "wishlist_intent"),
            "purchase_intent": compute_distribution(cluster_obs, "purchase_intent"),
            "journey_stage": compute_distribution(cluster_obs, "journey_stage"),
            "decision_outcome": compute_distribution(cluster_obs, "decision_outcome"),
            "segment_signal": compute_distribution(cluster_obs, "segment_signal"),
            "product_category": compute_distribution(cluster_obs, "product_category"),
            "uncertainty": compute_distribution(cluster_obs, "uncertainty"),
            "information_needed": compute_distribution(cluster_obs, "information_needed"),
            "workaround": compute_distribution(cluster_obs, "workaround"),
            "external_platform_used": compute_distribution(cluster_obs, "external_platform_used")
        }
        
        aggregations.append((
            run_id, cluster_id, obs_count, unique_sources, json.dumps(dists)
        ))
        
        reps = select_representatives(cluster_id, obs_ids, obs_data, embeddings, all_ids_list)
        for r in reps:
            representatives_to_insert.append((
                run_id, cluster_id, r["observation_id"], r["source_record_id"],
                r["evidence_quote"], r["source"], r["source_url"],
                r["primary_barrier"], r["uncertainty"]
            ))
            r_out = dict(r)
            r_out["cluster_id"] = cluster_id
            representatives_jsonl.append(r_out)

    print("Persisting to DB...")
    conn.execute("DELETE FROM cluster_aggregations")
    conn.execute("DELETE FROM cluster_representatives")
    
    conn.executemany(
        """INSERT INTO cluster_aggregations 
           (analysis_run_id, cluster_id, observation_count, unique_source_count, distributions_json)
           VALUES (?, ?, ?, ?, ?)""",
        aggregations
    )
    conn.executemany(
        """INSERT INTO cluster_representatives 
           (analysis_run_id, cluster_id, observation_id, source_record_id, evidence_quote, source, source_url, primary_barrier, uncertainty)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        representatives_to_insert
    )
    conn.commit()
    conn.close()
    
    print("Writing JSONL artifact...")
    with open(REP_PATH, "w") as f:
        for item in representatives_jsonl:
            f.write(json.dumps(item) + "\n")
            
    print("\n" + "=" * 60)
    print("TASK 4.4 SUMMARY")
    print("=" * 60)
    print(f"Themes/Clusters processed: {len(aggregations)}")
    print(f"Total representatives selected: {len(representatives_to_insert)}")
    
    gate_pass = len(aggregations) > 0 and len(representatives_to_insert) > 0
    print(f"\nIntegrity gate: PROCEED to Task 4.5 if representatives were generated")
    print(f"Gate result: {'PASS ✓' if gate_pass else 'FAIL ✗ — STOP AND REPORT'}")
    return gate_pass


if __name__ == "__main__":
    passed = run_aggregation()
    exit(0 if passed else 1)
