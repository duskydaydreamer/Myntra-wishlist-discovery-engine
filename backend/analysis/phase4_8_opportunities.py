"""
Task 4.8 — Opportunity Area Generation
========================================
Groups unmet needs and uses Gemini to formulate 3-5 strategic Opportunity Areas.
Classifies the relevance of each opportunity against product metrics (DIRECT, CONTEXTUAL, LOW-UNCLEAR).

Outputs:
- data/phase4/opportunity_areas.jsonl
- DB update: opportunity_areas
"""

import json
import os
import sqlite3
import time

import google.generativeai as genai
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "discovery_pulse.db")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "phase4")
CONTEXT_PATH = os.path.join(OUTPUT_DIR, "unmet_need_context.jsonl")
OPP_PATH = os.path.join(OUTPUT_DIR, "opportunity_areas.jsonl")

load_dotenv(os.path.join(BASE_DIR, ".env"))
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env")

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-3.6-flash')

PROMPT_TEMPLATE = """
You are a Lead Product Strategist for Myntra (a fashion e-commerce platform).
I am providing you with {num_needs} unmet user needs discovered from qualitative research, 
along with their frequency (number of times observed) and associated barriers/intents.

Your task is to synthesize these into 3 to 5 strategic "Opportunity Areas".
Each opportunity should group related unmet needs into a cohesive product strategy.

For each Opportunity Area, provide:
1. opportunity_title (short, punchy)
2. description (2-3 sentences explaining the strategy)
3. supporting_unmet_needs (list of the exact unmet_need strings from the input that support this)
4. purchase_metric_relevance: Must be EXACTLY ONE of: [DIRECT, CONTEXTUAL, LOW-UNCLEAR]
5. wishlist_metric_relevance: Must be EXACTLY ONE of: [DIRECT, CONTEXTUAL, LOW-UNCLEAR]

Return ONLY a valid JSON array of objects. Do not use markdown blocks.

UNMET NEEDS CONTEXT:
{unmet_needs_json}
"""


def load_unmet_needs():
    needs = []
    if os.path.exists(CONTEXT_PATH):
        with open(CONTEXT_PATH, "r") as f:
            for line in f:
                needs.append(json.loads(line))
    return needs


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS phase4_opportunity_areas (
            opportunity_id TEXT PRIMARY KEY,
            analysis_run_id TEXT,
            title TEXT,
            description TEXT,
            purchase_metric_relevance TEXT,
            wishlist_metric_relevance TEXT,
            supporting_needs_json TEXT
        );
    """)
    conn.commit()
    return conn


def main():
    print("=" * 60)
    print("PHASE 4 TASK 4.8 — Opportunity Area Generation")
    print("=" * 60)
    
    run_id = f"run_{int(time.time())}"
    conn = init_db()
    
    needs = load_unmet_needs()
    print(f"Loaded {len(needs)} unmet needs context.")
    
    if not needs:
        print("No unmet needs to process. Exiting.")
        return False
        
    prompt = PROMPT_TEMPLATE.replace("{num_needs}", str(len(needs)))
    prompt = prompt.replace("{unmet_needs_json}", json.dumps(needs, indent=2))
    
    print("Synthesizing Opportunity Areas via Gemini API...")
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                response_mime_type="application/json"
            )
        )
        opportunities = json.loads(response.text)
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return False
        
    print(f"Generated {len(opportunities)} Opportunity Areas.")
    
    to_insert = []
    for i, opp in enumerate(opportunities):
        opp_id = f"opp_{i+1:03d}"
        opp["opportunity_id"] = opp_id
        
        # Validation
        p_rel = opp.get("purchase_metric_relevance", "LOW-UNCLEAR").upper()
        w_rel = opp.get("wishlist_metric_relevance", "LOW-UNCLEAR").upper()
        if p_rel not in ["DIRECT", "CONTEXTUAL", "LOW-UNCLEAR"]: p_rel = "LOW-UNCLEAR"
        if w_rel not in ["DIRECT", "CONTEXTUAL", "LOW-UNCLEAR"]: w_rel = "LOW-UNCLEAR"
        opp["purchase_metric_relevance"] = p_rel
        opp["wishlist_metric_relevance"] = w_rel
        
        to_insert.append((
            opp_id, run_id, opp.get("opportunity_title", "Untitled"),
            opp.get("description", ""), p_rel, w_rel,
            json.dumps(opp.get("supporting_unmet_needs", []))
        ))
        
    print("Persisting to DB...")
    conn.execute("DELETE FROM phase4_opportunity_areas")
    conn.executemany(
        """INSERT INTO phase4_opportunity_areas 
           (opportunity_id, analysis_run_id, title, description, purchase_metric_relevance, wishlist_metric_relevance, supporting_needs_json)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        to_insert
    )
    conn.commit()
    conn.close()
    
    print("Writing JSONL artifact...")
    with open(OPP_PATH, "w") as f:
        for opp in opportunities:
            f.write(json.dumps(opp) + "\n")
            
    print("\n" + "=" * 60)
    print("TASK 4.8 SUMMARY")
    print("=" * 60)
    for opp in opportunities:
        print(f"\n- {opp['opportunity_title']} (Purchase: {opp['purchase_metric_relevance']}, Wishlist: {opp['wishlist_metric_relevance']})")
        print(f"  {opp['description']}")
        
    gate_pass = len(opportunities) >= 3
    print(f"\nIntegrity gate: PROCEED to Task 4.9 if at least 3 opportunities were generated")
    print(f"Gate result: {'PASS ✓' if gate_pass else 'FAIL ✗ — STOP AND REPORT'}")
    return gate_pass


if __name__ == "__main__":
    passed = main()
    exit(0 if passed else 1)
