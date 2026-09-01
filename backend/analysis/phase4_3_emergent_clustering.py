"""
Task 4.3 — Emergent Semantic Pattern Discovery
==============================================
Runs the optimal HDBSCAN clustering strategy (selected in Task 4.1) across
ALL 9,171 observations to discover emergent patterns.

Selected Config (from Task 4.1):
  UMAP: n_neighbors=30, n_components=25, min_dist=0.1
  HDBSCAN: min_cluster_size=50, min_samples=5

Outputs:
- data/phase4/semantic_clusters.jsonl
- data/phase4/cluster_memberships.jsonl
- DB update: semantic_clusters, cluster_memberships
"""

import json
import os
import sqlite3
import time
from collections import Counter
from datetime import datetime, timezone

import chromadb
import hdbscan
import numpy as np
import umap
from sklearn.preprocessing import normalize

# ── paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "discovery_pulse.db")
CHROMA_PATH = os.environ.get("CHROMA_PATH", os.path.join(BASE_DIR, "data", "chroma"))
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "phase4")
CLUSTERS_PATH = os.path.join(OUTPUT_DIR, "semantic_clusters.jsonl")
MEMBERSHIPS_PATH = os.path.join(OUTPUT_DIR, "cluster_memberships.jsonl")

# ── config (from task 4.1) ─────────────────────────────────────────────────────
UMAP_PARAMS = {"n_neighbors": 30, "n_components": 25, "min_dist": 0.1}
HDBSCAN_PARAMS = {"min_cluster_size": 50, "min_samples": 5}
RANDOM_SEED = 42
CONFIG_VERSION = "v1_umap30_25_hdbscan50_5"


def load_observations():
    """Load observation IDs and embeddings from Chroma."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    col = client.get_collection("observation_embeddings")
    res = col.get(include=["embeddings"])
    obs_ids = res["ids"]
    obs_embeddings = np.array(res["embeddings"], dtype=np.float32)
    return obs_ids, obs_embeddings


def load_unique_sources(obs_ids):
    """Load the source_record_id for each observation to compute unique source support."""
    conn = sqlite3.connect(DB_PATH)
    placeholders = ",".join(["?"] * len(obs_ids))
    rows = conn.execute(
        f"SELECT observation_id, source_record_id FROM observations WHERE observation_id IN ({placeholders})",
        obs_ids
    ).fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS semantic_clusters (
            cluster_id TEXT PRIMARY KEY,
            analysis_run_id TEXT,
            clustering_config_version TEXT,
            observation_count INTEGER,
            unique_source_count INTEGER,
            is_noise BOOLEAN,
            canonical_label TEXT,
            created_at DATETIME
        );
        CREATE TABLE IF NOT EXISTS cluster_memberships (
            cluster_id TEXT,
            observation_id TEXT,
            membership_probability FLOAT
        );
        CREATE INDEX IF NOT EXISTS idx_cluster_membership_obs ON cluster_memberships(observation_id);
        CREATE INDEX IF NOT EXISTS idx_cluster_membership_cid ON cluster_memberships(cluster_id);
    """)
    conn.commit()
    return conn


def write_jsonl(path, data):
    with open(path, "w") as f:
        for item in data:
            f.write(json.dumps(item) + "\n")


def run_emergent_clustering(run_id="run_latest"):
    db_path = "data/discovery_pulse.db"
    print("=" * 60)
    print("PHASE 4 TASK 4.3 — Emergent Semantic Pattern Discovery")
    print("=" * 60)
    
        now_iso = datetime.now(timezone.utc).isoformat()
    
    # 1. DB setup
    conn = init_db()
    
    # 2. Load data
    print("Loading observation embeddings from Chroma...")
    obs_ids, obs_embeddings = load_observations()
    print(f"Loaded {len(obs_ids)} observations.")
    
    source_map = load_unique_sources(obs_ids)
    
    # 3. L2 Normalize
    print("Normalizing embeddings...")
    embeddings_normed = normalize(obs_embeddings, norm="l2")
    
    # 4. Dimensionality Reduction (UMAP)
    print(f"Running UMAP (n_neighbors={UMAP_PARAMS['n_neighbors']}, n_components={UMAP_PARAMS['n_components']})...")
    t0 = time.time()
    reducer = umap.UMAP(
        n_neighbors=UMAP_PARAMS["n_neighbors"],
        n_components=UMAP_PARAMS["n_components"],
        min_dist=UMAP_PARAMS["min_dist"],
        metric="cosine",
        random_state=RANDOM_SEED,
        low_memory=False
    )
    reduced = reducer.fit_transform(embeddings_normed)
    print(f"UMAP finished in {time.time()-t0:.1f}s")
    
    # 5. Clustering (HDBSCAN)
    print(f"Running HDBSCAN (min_cluster_size={HDBSCAN_PARAMS['min_cluster_size']}, min_samples={HDBSCAN_PARAMS['min_samples']})...")
    t0 = time.time()
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=HDBSCAN_PARAMS["min_cluster_size"],
        min_samples=HDBSCAN_PARAMS["min_samples"],
        metric="euclidean",
        cluster_selection_method="eom",
        prediction_data=True
    )
    labels = clusterer.fit_predict(reduced)
    probs = clusterer.probabilities_
    print(f"HDBSCAN finished in {time.time()-t0:.1f}s")
    
    # 6. Aggregate cluster statistics
    print("Aggregating cluster statistics...")
    
    # Map cluster index (-1 to N) to unique cluster IDs
    # -1 is HDBSCAN noise
    cluster_records = {}
    membership_records = []
    
    for i, (label, prob) in enumerate(zip(labels, probs)):
        obs_id = obs_ids[i]
        src_id = source_map.get(obs_id)
        
        if label == -1:
            cid = "cluster_noise"
            is_noise = True
        else:
            cid = f"cluster_{label:03d}"
            is_noise = False
            
        if cid not in cluster_records:
            cluster_records[cid] = {
                "observation_count": 0,
                "sources": set(),
                "is_noise": is_noise
            }
            
        cluster_records[cid]["observation_count"] += 1
        if src_id:
            cluster_records[cid]["sources"].add(src_id)
            
        membership_records.append({
            "cluster_id": cid,
            "observation_id": obs_id,
            "membership_probability": float(prob) if not is_noise else 0.0
        })
        
    # Prepare inserts
    clusters_to_insert = []
    clusters_jsonl = []
    
    for cid, data in cluster_records.items():
        obs_count = data["observation_count"]
        src_count = len(data["sources"])
        is_noise = data["is_noise"]
        
        clusters_to_insert.append((
            cid, run_id, CONFIG_VERSION, obs_count, src_count, is_noise, None, now_iso
        ))
        
        clusters_jsonl.append({
            "cluster_id": cid,
            "observation_count": obs_count,
            "unique_source_count": src_count,
            "is_noise": is_noise,
            "clustering_config_version": CONFIG_VERSION
        })
        
    memberships_to_insert = [
        (m["cluster_id"], m["observation_id"], m["membership_probability"])
        for m in membership_records
    ]
    
    # 7. Persist to DB
    print(f"Persisting {len(clusters_to_insert)} clusters and {len(memberships_to_insert)} memberships to DB...")
    conn.execute("DELETE FROM semantic_clusters")
    conn.execute("DELETE FROM cluster_memberships")
    
    conn.executemany(
        """INSERT INTO semantic_clusters 
           (cluster_id, analysis_run_id, clustering_config_version, observation_count, unique_source_count, is_noise, canonical_label, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        clusters_to_insert
    )
    conn.executemany(
        """INSERT INTO cluster_memberships 
           (cluster_id, observation_id, membership_probability)
           VALUES (?, ?, ?)""",
        memberships_to_insert
    )
    conn.commit()
    conn.close()
    
    # 8. Write JSONL artifacts
    print("Writing JSONL artifacts...")
    write_jsonl(CLUSTERS_PATH, clusters_jsonl)
    write_jsonl(MEMBERSHIPS_PATH, membership_records)
    
    # 9. Gate check
    n_clusters = len([c for c in clusters_jsonl if not c["is_noise"]])
    noise_cluster = next((c for c in clusters_jsonl if c["is_noise"]), None)
    noise_count = noise_cluster["observation_count"] if noise_cluster else 0
    noise_rate = noise_count / len(obs_ids)
    
    print("\n" + "=" * 60)
    print("TASK 4.3 SUMMARY")
    print("=" * 60)
    print(f"Total Observations : {len(obs_ids)}")
    print(f"Clusters Found     : {n_clusters}")
    print(f"Noise Observations : {noise_count} ({noise_rate*100:.1f}%)")
    
    gate_pass = (n_clusters > 0) and (noise_rate > 0)
    print(f"\nQuality gate: PROCEED to Task 4.4 if clustering produces valid emergent clusters and preserves noise")
    print(f"Gate result: {'PASS ✓' if gate_pass else 'FAIL ✗ — STOP AND REPORT'}")
    return gate_pass


if __name__ == "__main__":
    passed = run_emergent_clustering()
    exit(0 if passed else 1)
