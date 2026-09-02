"""
Task 4.5 — LLM Naming & Root-Cause Synthesis
=============================================
Uses Gemini to automatically synthesize names, descriptions, root causes,
and unmet needs for the emergent clusters based on their representative quotes.

Outputs:
- data/phase4/cluster_synthesis.jsonl
- DB update: semantic_clusters (adds canonical_label)
"""

import json
import os
import sqlite3
import time
from datetime import datetime, timezone

import google.generativeai as genai
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "discovery_pulse.db")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "phase4")
REP_PATH = os.path.join(OUTPUT_DIR, "cluster_representatives.jsonl")
SYNTHESIS_PATH = os.path.join(OUTPUT_DIR, "cluster_synthesis.jsonl")

# Load environment
load_dotenv(os.path.join(BASE_DIR, ".env"))
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# We use gemini-3.6-flash for fast, structured synthesis
model = genai.GenerativeModel('gemini-3.6-flash')

PROMPT_TEMPLATE = """
You are an expert e-commerce qualitative researcher analyzing user feedback.
Analyze the following representative quotes from a single thematic cluster.

Based on these quotes, synthesize the cluster's core theme by providing:
1. canonical_name: A short, precise name for this cluster (3-5 words).
2. description: A clear explanation of what this cluster represents (1-2 sentences).
3. primary_root_cause: The underlying reason WHY users are experiencing this (e.g., "Lack of visual context for dimensions", "Inconsistent sizing charts").
4. primary_unmet_need: What the user actually needs to resolve this (e.g., "A way to see the product on diverse body types").

Return ONLY valid JSON with no markdown formatting or code blocks.
Format exactly like this:
{
  "canonical_name": "...",
  "description": "...",
  "primary_root_cause": "...",
  "primary_unmet_need": "..."
}

QUOTES:
{quotes_text}
"""


def load_representatives():
    clusters = {}
    if not os.path.exists(REP_PATH):
        return clusters
        
    with open(REP_PATH, "r") as f:
        for line in f:
            item = json.loads(line)
            cid = item["cluster_id"]
            clusters.setdefault(cid, []).append(item["evidence_quote"])
    return clusters


def synthesize_cluster(cluster_id, quotes):
    quotes_text = "\\n\\n".join(f"- {q}" for q in quotes)
    prompt = PROMPT_TEMPLATE.replace("{quotes_text}", quotes_text)
    
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                response_mime_type="application/json"
            )
        )
        data = json.loads(response.text)
        return data
    except Exception as e:
        print(f"Error synthesizing {cluster_id}: {e}")
        # Return fallback
        return {
            "canonical_name": f"Emergent Pattern {cluster_id.split('_')[-1]}",
            "description": "Failed to synthesize description.",
            "primary_root_cause": "Unknown",
            "primary_unmet_need": "Unknown"
        }


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS cluster_synthesis (
            analysis_run_id TEXT,
            cluster_id TEXT PRIMARY KEY,
            canonical_name TEXT,
            description TEXT,
            primary_root_cause TEXT,
            primary_unmet_need TEXT
        );
    """)
    conn.commit()
    return conn


def run_llm_synthesis(run_id="run_latest"):
    db_path = "data/discovery_pulse.db"
    print("=" * 60)
    print("PHASE 4 TASK 4.5 — LLM Naming & Root-Cause Synthesis")
    print("=" * 60)
    
    conn = init_db()
    
    print("Loading representative quotes...")
    clusters = load_representatives()
    print(f"Loaded {len(clusters)} clusters to synthesize.")
    
    synthesis_results = []
    
    print("Synthesizing via Gemini API...")
    for i, (cid, quotes) in enumerate(clusters.items()):
        print(f"  [{i+1}/{len(clusters)}] Synthesizing {cid}...")
        
        # Don't synthesize predefined themes or noise, only emergent clusters
        # Wait, the task asks to name the emergent clusters. 
        # Emergent clusters are named "cluster_000", "cluster_001", etc.
        # Predefined themes have names like "fit_and_sizing_uncertainty".
        if cid == "cluster_noise" or not cid.startswith("cluster_"):
            print(f"    Skipping predefined/noise: {cid}")
            continue
            
        data = synthesize_cluster(cid, quotes)
        
        result = {
            "cluster_id": cid,
            "canonical_name": data["canonical_name"],
            "description": data["description"],
            "primary_root_cause": data["primary_root_cause"],
            "primary_unmet_need": data["primary_unmet_need"]
        }
        synthesis_results.append(result)
        
        # Avoid rate limits
        time.sleep(1.5)
        
    print("Persisting synthesis to DB...")
    to_insert = [
        (run_id, r["cluster_id"], r["canonical_name"], r["description"], 
         r["primary_root_cause"], r["primary_unmet_need"])
        for r in synthesis_results
    ]
    
    # Update canonical labels in semantic_clusters
    for r in synthesis_results:
        conn.execute(
            "UPDATE semantic_clusters SET canonical_label = ? WHERE cluster_id = ?",
            (r["canonical_name"], r["cluster_id"])
        )
        
    # Also set canonical_labels for predefined themes in semantic_clusters
    # using the predefined_themes table
    conn.execute("""
        UPDATE semantic_clusters 
        SET canonical_label = (
            SELECT canonical_name FROM predefined_themes WHERE theme_id = semantic_clusters.cluster_id
        )
        WHERE cluster_id IN (SELECT theme_id FROM predefined_themes)
    """)
    
    conn.execute("DELETE FROM cluster_synthesis")
    conn.executemany(
        """INSERT INTO cluster_synthesis 
           (analysis_run_id, cluster_id, canonical_name, description, primary_root_cause, primary_unmet_need)
           VALUES (?, ?, ?, ?, ?, ?)""",
        to_insert
    )
    conn.commit()
    conn.close()
    
    print("Writing JSONL artifact...")
    with open(SYNTHESIS_PATH, "w") as f:
        for item in synthesis_results:
            f.write(json.dumps(item) + "\n")
            
    print("\n" + "=" * 60)
    print("TASK 4.5 SUMMARY")
    print("=" * 60)
    print(f"Clusters synthesized: {len(synthesis_results)}")
    
    failed_results = [
        result for result in synthesis_results
        if result["canonical_name"].startswith("Emergent Pattern ")
        or result["description"] == "Failed to synthesize description."
        or result["primary_root_cause"].lower() == "unknown"
        or result["primary_unmet_need"].lower() == "unknown"
    ]
    gate_pass = len(synthesis_results) == len(clusters) and not failed_results
    print(f"Failed or placeholder syntheses: {len(failed_results)}")
    print(f"\nQuality gate: PROCEED only if every emergent cluster has a complete synthesis")
    print(f"Gate result: {'PASS ✓' if gate_pass else 'FAIL ✗ — STOP AND REPORT'}")
    return gate_pass


if __name__ == "__main__":
    passed = run_llm_synthesis()
    exit(0 if passed else 1)
