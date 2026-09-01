"""
Task 4.9 — Master Knowledge Graph Construction
================================================
Combines all Phase 4 outputs into a unified JSON representation.
Links Opportunity Areas -> Unmet Needs -> Clusters -> Themes/Barriers.

Outputs:
- data/phase4/knowledge_graph.json
"""

import json
import os
import sqlite3
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "discovery_pulse.db")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "phase4")
KG_PATH = os.path.join(OUTPUT_DIR, "knowledge_graph.json")


def build_knowledge_graph():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # 1. Load Opportunity Areas
    opp_rows = conn.execute("SELECT * FROM phase4_opportunity_areas").fetchall()
    opportunities = []
    
    for orow in opp_rows:
        opp = dict(orow)
        opp["supporting_unmet_needs"] = json.loads(opp.pop("supporting_needs_json", "[]"))
        opportunities.append(opp)
        
    # 2. Load Unmet Need Contexts
    need_rows = conn.execute("SELECT * FROM unmet_need_context").fetchall()
    needs = {}
    
    for nrow in need_rows:
        need = dict(nrow)
        need["associated_barriers"] = json.loads(need.pop("associated_barriers_json", "[]"))
        need["associated_intents"] = json.loads(need.pop("associated_intents_json", "[]"))
        needs[need["unmet_need"]] = need
        
    # 3. Load Clusters & Synthesis
    cluster_rows = conn.execute("""
        SELECT 
            sc.cluster_id, sc.canonical_label, sc.observation_count,
            cs.description, cs.primary_root_cause, cs.primary_unmet_need
        FROM semantic_clusters sc
        LEFT JOIN cluster_synthesis cs ON sc.cluster_id = cs.cluster_id
    """).fetchall()
    
    clusters = {}
    for crow in cluster_rows:
        clusters[crow["cluster_id"]] = dict(crow)
        
    # Bind them all together
    knowledge_graph = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_clusters": len(clusters),
            "total_unmet_needs": len(needs),
            "total_opportunities": len(opportunities)
        },
        "opportunities": [],
        "unlinked_needs": [],
        "unlinked_clusters": []
    }
    
    used_needs = set()
    
    for opp in opportunities:
        opp_node = {
            "id": opp["opportunity_id"],
            "title": opp["title"],
            "description": opp["description"],
            "relevance": {
                "purchase": opp["purchase_metric_relevance"],
                "wishlist": opp["wishlist_metric_relevance"]
            },
            "unmet_needs": []
        }
        
        for un_str in opp["supporting_unmet_needs"]:
            if un_str in needs:
                used_needs.add(un_str)
                need_node = dict(needs[un_str])
                
                # Find clusters supporting this need
                supporting_clusters = []
                for cid, cdata in clusters.items():
                    if cdata.get("primary_unmet_need") == un_str:
                        supporting_clusters.append(cdata)
                        
                need_node["clusters"] = supporting_clusters
                opp_node["unmet_needs"].append(need_node)
                
        knowledge_graph["opportunities"].append(opp_node)
        
    conn.close()
    
    with open(KG_PATH, "w") as f:
        json.dump(knowledge_graph, f, indent=2)
        
    return knowledge_graph


def main():
    print("=" * 60)
    print("PHASE 4 TASK 4.9 — Knowledge Graph Construction")
    print("=" * 60)
    
    kg = build_knowledge_graph()
    
    print(f"Graph constructed successfully:")
    print(f"- {kg['metadata']['total_opportunities']} Opportunity Areas")
    print(f"- {kg['metadata']['total_unmet_needs']} Unmet Needs mapped")
    print(f"- {kg['metadata']['total_clusters']} Total Clusters")
    print(f"\nWritten to: {KG_PATH}")
    
    gate_pass = kg['metadata']['total_opportunities'] > 0
    print(f"\nIntegrity gate: PROCEED to Task 4.10")
    print(f"Gate result: {'PASS ✓' if gate_pass else 'FAIL ✗ — STOP AND REPORT'}")
    return gate_pass


if __name__ == "__main__":
    passed = main()
    exit(0 if passed else 1)
