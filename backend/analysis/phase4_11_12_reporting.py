"""
Task 4.11 & 4.12 — Phase 4 Evaluation & Reporting
==================================================
Generates the Phase 4 Final Report and Evaluation JSON.
"""

import json
import os
import sqlite3
from datetime import datetime, timezone

from backend.research_rules import OPPORTUNITY_RULES

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "phase4")
DB_PATH = os.path.join(BASE_DIR, "data", "discovery_pulse.db")
EVAL_PATH = os.path.join(OUTPUT_DIR, "phase4_evaluation_report.json")
REPORT_PATH = os.path.join(OUTPUT_DIR, "phase4_final_report.md")

def generate_report():
    print("=" * 60)
    print("PHASE 4 TASK 4.11 & 4.12 — Final Reporting")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    total_observations = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
    noise_observations = conn.execute(
        "SELECT COUNT(*) FROM cluster_memberships WHERE cluster_id = 'cluster_noise'"
    ).fetchone()[0]
    mapped_observations = conn.execute(
        "SELECT COUNT(DISTINCT observation_id) FROM theme_assignments"
    ).fetchone()[0]
    total_clusters = conn.execute(
        "SELECT COUNT(*) FROM semantic_clusters WHERE is_noise = 0"
    ).fetchone()[0]
    placeholder_clusters = conn.execute(
        """
        SELECT COUNT(*) FROM cluster_synthesis
        WHERE canonical_name LIKE 'Emergent Pattern %'
           OR description = 'Failed to synthesize description.'
           OR lower(primary_root_cause) = 'unknown'
           OR lower(primary_unmet_need) = 'unknown'
        """
    ).fetchone()[0]

    manual_eval_path = os.path.join(OUTPUT_DIR, "manual_validation.json")
    manual_validation_passed = False
    if os.path.exists(manual_eval_path):
        with open(manual_eval_path, "r") as f:
            manual_validation_passed = json.load(f).get("gate_passed") is True

    # Check for unreviewed clusters in opportunity_evidence
    unreviewed_evidence_count = 0
    for opp_id, rule in OPPORTUNITY_RULES.items():
        if not rule.get("cluster_ids"):
            continue
        placeholders = ",".join(["?"] * len(rule["cluster_ids"]))
        query = f"""
            SELECT COUNT(*) 
            FROM opportunity_evidence oe
            JOIN cluster_memberships cm ON cm.observation_id = oe.observation_id
            WHERE oe.opportunity_id = ? AND cm.cluster_id NOT IN ({placeholders})
        """
        params = [opp_id] + list(rule["cluster_ids"])
        count = conn.execute(query, params).fetchone()[0]
        unreviewed_evidence_count += count

    gate_reasons = []
    if placeholder_clusters:
        gate_reasons.append(f"{placeholder_clusters} cluster syntheses are failed or incomplete")
    if not manual_validation_passed:
        gate_reasons.append("manual semantic-coherence validation has not passed")
    if unreviewed_evidence_count > 0:
        gate_reasons.append(f"opportunity evidence contains {unreviewed_evidence_count} unreviewed cluster links")
        
    gate_pass = not gate_reasons

    eval_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "representation_clustering": {
            "method": "UMAP + HDBSCAN",
            "semantic_coherence": "not_evaluated" if not manual_validation_passed else "manually_validated",
            "noise_observations": noise_observations,
            "noise_percentage": round(noise_observations / total_observations * 100, 1) if total_observations else 0,
        },
        "predefined_semantic_mapping": {
            "mapped_observations": mapped_observations,
            "mapping_rate": round(mapped_observations / total_observations * 100, 1) if total_observations else 0,
            "threshold_validation": "not_manually_validated",
        },
        "emergent_clusters": {
            "total_clusters": total_clusters,
            "failed_or_placeholder_syntheses": placeholder_clusters,
            "duplicate_concept_check": "not_evaluated",
        },
        "quality_gate": {"passed": gate_pass, "reasons": gate_reasons},
    }
    with open(EVAL_PATH, "w") as f:
        json.dump(eval_data, f, indent=2)

    md = [
        "# Phase 4 Research-Safety Report",
        f"Generated at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        f"**Quality gate:** {'PASS' if gate_pass else 'FAIL'}",
        "",
        "The counts below use only reviewed issue clusters. They are directional public-feedback signals, not population estimates.",
        ""
    ]

    if gate_reasons:
        md.append("## Unresolved validation requirements")
        md.extend(f"- {reason}" for reason in gate_reasons)
        md.append("")

    md.append("## Directional investigation areas")
    for index, (opportunity_id, rule) in enumerate(OPPORTUNITY_RULES.items(), start=1):
        placeholders = ",".join("?" for _ in rule["cluster_ids"])
        count = conn.execute(
            f"""
            SELECT COUNT(DISTINCT o.source_record_id)
            FROM observations o JOIN cluster_memberships cm ON cm.observation_id = o.observation_id
            WHERE cm.cluster_id IN ({placeholders})
            """,
            rule["cluster_ids"],
        ).fetchone()[0]
        md.append(f"### {index}. {rule['title']}")
        md.append(f"**Supporting feedback records:** {count}")
        md.append(f"**Calculation:** {rule['calculation_note']}")
        quotes = conn.execute(
            f"""
            SELECT o.evidence_quote FROM observations o
            JOIN cluster_memberships cm ON cm.observation_id = o.observation_id
            WHERE cm.cluster_id IN ({placeholders}) AND o.evidence_quote NOT LIKE '%[NAME]%'
            ORDER BY length(o.evidence_quote) DESC LIMIT 2
            """,
            rule["cluster_ids"],
        ).fetchall()
        if quotes:
            md.append("\n**Representative Evidence:**")
            for q in quotes:
                md.append(f"> \"{q[0]}\"")
        md.append("\n---\n")

    with open(REPORT_PATH, "w") as f:
        f.write("\n".join(md))
    conn.close()

    print(f"Report written to {REPORT_PATH}")
    print(f"\nIntegrity gate: PROCEED TO PHASE 5 only after all validation requirements pass")
    print(f"Gate result: {'PASS ✓' if gate_pass else 'FAIL ✗ — STOP AND REPORT'}")
    for reason in gate_reasons:
        print(f"- {reason}")
    return gate_pass


if __name__ == "__main__":
    passed = generate_report()
    exit(0 if passed else 1)
