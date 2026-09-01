"""
Task 4.10 — Opportunity Quantification & Prioritization
=======================================================
Quantifies support for each opportunity area (unique sources, observation counts)
and persists evidence links.
"""

import json
import os
import sqlite3

from backend.research_rules import OPPORTUNITY_RULES

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "discovery_pulse.db")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "phase4")
QUANT_PATH = os.path.join(OUTPUT_DIR, "opportunity_quantification.json")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS opportunity_evidence (
            opportunity_id TEXT,
            observation_id TEXT,
            PRIMARY KEY (opportunity_id, observation_id)
        );
    """)
    conn.commit()
    return conn


def run_quantification(run_id="run_latest"):
    db_path = "data/discovery_pulse.db"
    print("=" * 60)
    print("PHASE 4 TASK 4.10 — Quantification & Prioritization")
    print("=" * 60)
    
    conn = init_db()
    conn.row_factory = sqlite3.Row
    
    # Total unique sources in Phase 3
    total_sources = conn.execute("SELECT COUNT(DISTINCT source_record_id) FROM observations").fetchone()[0]
    total_obs = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
    
    opps = conn.execute("SELECT * FROM phase4_opportunity_areas").fetchall()
    
    # Clear all legacy links before inserting corrected ones to ensure 
    # no unreviewed opportunity maintains contaminated evidence links.
    conn.execute("DELETE FROM opportunity_evidence")
    
    results = []
    
    for opp in opps:
        opp_id = opp["opportunity_id"]
        rule = OPPORTUNITY_RULES.get(opp_id)
        if not rule:
            continue

        needs = list(rule["supporting_needs"])
        # Generated unmet-need text previously combined praise, mixed experiences,
        # and explicit problems. Quantify only the reviewed issue clusters.
        cluster_ids = list(rule["cluster_ids"])
        
        if not cluster_ids:
            continue
            
        c_placeholders = ",".join(["?"] * len(cluster_ids))
        
        from backend.research_rules import PATTERN_EVIDENCE_ROLES
        exclude_clusters = [cid for cid, role in PATTERN_EVIDENCE_ROLES.items() if role in ("positive", "mixed")]
        ex_placeholders = ",".join(["?"] * len(exclude_clusters))
        
        # 2. Get all observation_ids in these clusters
        query = f"""
            SELECT DISTINCT observation_id 
            FROM cluster_memberships 
            WHERE cluster_id IN ({c_placeholders})
            AND observation_id NOT IN (
                SELECT observation_id 
                FROM cluster_memberships 
                WHERE cluster_id IN ({ex_placeholders})
            )
        """
        params = cluster_ids + exclude_clusters
        obs_rows = conn.execute(query, params).fetchall()
        
        obs_ids = [r[0] for r in obs_rows]
        
        if not obs_ids:
            continue
            
        # 3. Get unique source count and metrics for these observations
        obs_placeholders = ",".join(["?"] * len(obs_ids))
        stats = conn.execute(
            f"SELECT COUNT(DISTINCT source_record_id) as unique_sources FROM observations WHERE observation_id IN ({obs_placeholders})",
            obs_ids
        ).fetchone()
        
        unique_sources = stats["unique_sources"]
        
        # Directional ordering by supporting feedback volume. Do not multiply by
        # generated "DIRECT" labels that have not been independently validated.
        score = unique_sources
        
        results.append({
            "opportunity_id": opp_id,
            "title": rule["title"],
            "description": rule["description"],
            "supporting_unmet_needs": needs,
            "metrics": {
                "observation_count": len(obs_ids),
                "unique_source_count": unique_sources,
                "dataset_prevalence_pct": round((unique_sources / total_sources) * 100, 2) if total_sources else 0
            },
            "relevance": {
                "purchase": "directional",
                "wishlist": "directional"
            },
            "prioritization_score": round(score, 2),
            "calculation_note": rule["calculation_note"],
            "validation_status": "directional_reviewed_clusters"
        })
        
        # Replace legacy links so positive or mixed clusters cannot remain attached.
        conn.execute("DELETE FROM opportunity_evidence WHERE opportunity_id = ?", (opp_id,))
        conn.executemany(
            "INSERT OR IGNORE INTO opportunity_evidence (opportunity_id, observation_id) VALUES (?, ?)",
            [(opp_id, oid) for oid in obs_ids]
        )
        
    conn.commit()
    conn.close()
    
    # Sort by prioritization score descending
    results.sort(key=lambda x: x["prioritization_score"], reverse=True)
    
    with open(QUANT_PATH, "w") as f:
        json.dump(results, f, indent=2)
        
    print(f"Quantified {len(results)} opportunities.")
    for r in results:
        m = r['metrics']
        print(f"- {r['title']} (Score: {r['prioritization_score']}) -> {m['unique_source_count']} sources ({m['dataset_prevalence_pct']}%)")
        
    gate_pass = len(results) > 0
    print(f"\nIntegrity gate: PROCEED to Task 4.11")
    print(f"Gate result: {'PASS ✓' if gate_pass else 'FAIL ✗ — STOP AND REPORT'}")
    return gate_pass


if __name__ == "__main__":
    passed = run_quantification()
    exit(0 if passed else 1)
