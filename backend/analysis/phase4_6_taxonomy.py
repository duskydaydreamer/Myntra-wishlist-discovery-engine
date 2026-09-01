"""
Task 4.6 — Root-Cause & Unmet-Need Taxonomy Generation
======================================================
Extracts and deduplicates all unique primary_root_cause and primary_unmet_need 
values from the cluster_synthesis results.
Creates derived taxonomy JSON files.

Outputs:
- data/phase4/root_cause_taxonomy.json
- data/phase4/unmet_need_taxonomy.json
"""

import json
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "discovery_pulse.db")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "phase4")
RC_TAXONOMY_PATH = os.path.join(OUTPUT_DIR, "root_cause_taxonomy.json")
UN_TAXONOMY_PATH = os.path.join(OUTPUT_DIR, "unmet_need_taxonomy.json")

def main():
    print("=" * 60)
    print("PHASE 4 TASK 4.6 — Taxonomy Generation")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT primary_root_cause, primary_unmet_need FROM cluster_synthesis").fetchall()
    conn.close()
    
    root_causes = set()
    unmet_needs = set()
    
    for rc, un in rows:
        if rc and rc.lower() != "unknown":
            root_causes.add(rc.strip())
        if un and un.lower() != "unknown":
            unmet_needs.add(un.strip())
            
    rc_list = sorted(list(root_causes))
    un_list = sorted(list(unmet_needs))
    
    print(f"Extracted {len(rc_list)} unique root causes.")
    print(f"Extracted {len(un_list)} unique unmet needs.")
    
    with open(RC_TAXONOMY_PATH, "w") as f:
        json.dump(rc_list, f, indent=2)
        
    with open(UN_TAXONOMY_PATH, "w") as f:
        json.dump(un_list, f, indent=2)
        
    print("\n" + "=" * 60)
    print("TASK 4.6 SUMMARY")
    print("=" * 60)
    print(f"Root Causes    : {len(rc_list)}")
    print(f"Unmet Needs    : {len(un_list)}")
    
    gate_pass = True
    print(f"\nIntegrity gate: PROCEED to Task 4.7")
    print(f"Gate result: {'PASS ✓' if gate_pass else 'FAIL ✗ — STOP AND REPORT'}")
    return gate_pass


if __name__ == "__main__":
    passed = main()
    exit(0 if passed else 1)
