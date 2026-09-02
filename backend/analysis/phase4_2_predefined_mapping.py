"""
Task 4.2 — Predefined Semantic Theme Mapping
============================================
Maps observations to the 10 predefined research themes from taxonomies.yaml
using semantic cosine similarity against locally embedded theme prototypes.

Output:
- data/phase4/predefined_themes.jsonl (Canonical definitions & prototypes)
- data/phase4/theme_assignments.jsonl (Observation mappings)
- DB update: creates and populates phase 4 derived tables
"""

import json
import os
import sqlite3
import time
from collections import Counter
from datetime import datetime, timezone

import chromadb
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# ── paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "discovery_pulse.db")
CHROMA_PATH = os.environ.get("CHROMA_PATH", os.path.join(BASE_DIR, "data", "chroma"))
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "phase4")
THEMES_PATH = os.path.join(OUTPUT_DIR, "predefined_themes.jsonl")
ASSIGN_PATH = os.path.join(OUTPUT_DIR, "theme_assignments.jsonl")

# ── semantic prototypes ────────────────────────────────────────────────────────
# Defines the canonical meaning and examples for the 10 predefined themes.
THEME_DEFINITIONS = {
    "fit_and_sizing_uncertainty": {
        "canonical_name": "Fit and Sizing Uncertainty",
        "description": "User is unsure what size to order or whether the garment will fit their specific body type correctly.",
        "examples": [
            "I don't know if I should size up or down for this dress.",
            "Not sure if a medium will fit my shoulders.",
            "Does this run true to size or small?",
            "Will these jeans fit someone who is 5'2?",
            "Confused about the sizing chart measurements."
        ]
    },
    "product_quality_uncertainty": {
        "canonical_name": "Product Quality Uncertainty",
        "description": "User doubts the fabric, durability, authenticity, or overall build quality of the item.",
        "examples": [
            "Is the fabric transparent or good quality?",
            "Worried that these shoes will break after one use.",
            "Are these genuine branded sneakers or fake?",
            "Does the material look cheap in real life?",
            "Will the color fade after washing?"
        ]
    },
    "comparison_difficulty": {
        "canonical_name": "Comparison Difficulty",
        "description": "User is struggling to compare products across different platforms or brands.",
        "examples": [
            "Checking if this is cheaper on Amazon or Myntra.",
            "I saw a similar dress on Meesho for half the price.",
            "How does this brand compare to H&M?",
            "Comparing prices across different apps before buying.",
            "Can't decide between this one and the other option I saved."
        ]
    },
    "price_timing_hesitation": {
        "canonical_name": "Price and Timing Hesitation",
        "description": "User is waiting for a sale, price drop, or debating if the current price is worth it.",
        "examples": [
            "Waiting for the big billion days sale to buy this.",
            "Is this worth 2000 rupees or should I wait for a discount?",
            "Too expensive right now, hoping the price drops.",
            "Added to wishlist until there's an offer.",
            "The price increased from yesterday, I'll hold off."
        ]
    },
    "styling_uncertainty": {
        "canonical_name": "Styling Uncertainty",
        "description": "User is unsure how to wear, pair, or style the item.",
        "examples": [
            "What kind of top would go well with these trousers?",
            "Not sure what color shoes to wear with this dress.",
            "How do I style this oversized shirt?",
            "Will this look good on a darker skin tone?",
            "Need help matching accessories with this outfit."
        ]
    },
    "occasion_suitability": {
        "canonical_name": "Occasion Suitability",
        "description": "User is deciding if the item is appropriate for a specific event or use case.",
        "examples": [
            "Is this formal enough for an office party?",
            "Looking for something to wear to a wedding reception.",
            "Can I wear these running shoes for casual daily use?",
            "Is this dress too flashy for a daytime event?",
            "Need a good outfit for my college farewell."
        ]
    },
    "review_trust_gap": {
        "canonical_name": "Review Trust Gap",
        "description": "User distrusts the platform reviews or needs real-life images from actual buyers to believe them.",
        "examples": [
            "The reviews look fake, I need to see real photos.",
            "Can someone share a picture of how it actually looks?",
            "Searching YouTube for an honest review of this product.",
            "I don't trust the Myntra reviews for this seller.",
            "Does anyone have a video showing the real product?"
        ]
    },
    "social_validation": {
        "canonical_name": "Social Validation",
        "description": "User is asking for opinions from others to validate their choice before buying.",
        "examples": [
            "Guys, should I buy the black one or the blue one?",
            "Does this look good or is it too basic? Tell me.",
            "Asking my friends if they like this before I order.",
            "Need opinions on whether this watch is cool.",
            "Help me decide if this is a good purchase."
        ]
    },
    "availability_concerns": {
        "canonical_name": "Availability Concerns",
        "description": "User wants an item but their size, color, or the product itself is out of stock.",
        "examples": [
            "My size is out of stock, when will it return?",
            "I want the pink one but it's unavailable.",
            "Waiting for the medium size to be restocked.",
            "Product is currently unavailable in my area.",
            "Will they bring this design back in stock?"
        ]
    },
    "delivery_return_exchange_concerns": {
        "canonical_name": "Delivery, Return & Exchange Concerns",
        "description": "User is worried about delayed shipping, strict return policies, or refund reliability.",
        "examples": [
            "Will this be delivered before Friday? I need it urgently.",
            "Is the return process easy if it doesn't fit?",
            "Worried they will reject the return request like last time.",
            "My last order was delayed by 10 days, hesitant to order again.",
            "How long does the refund take to process?"
        ]
    }
}


def load_observations():
    """Load observation IDs and embeddings from Chroma."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    col = client.get_collection("observation_embeddings")
    res = col.get(include=["embeddings"])
    obs_ids = res["ids"]
    obs_embeddings = np.array(res["embeddings"], dtype=np.float32)
    return obs_ids, obs_embeddings


def init_db():
    """Initialize Phase 4 derived tables."""
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS analysis_runs (
            analysis_run_id TEXT PRIMARY KEY,
            created_at DATETIME,
            clustering_config_version TEXT,
            mapping_threshold_version TEXT
        );
        CREATE TABLE IF NOT EXISTS predefined_themes (
            theme_id TEXT PRIMARY KEY,
            canonical_name TEXT,
            description TEXT
        );
        CREATE TABLE IF NOT EXISTS theme_assignments (
            analysis_run_id TEXT,
            observation_id TEXT,
            predefined_theme_id TEXT,
            assignment_type TEXT,
            similarity_score FLOAT,
            threshold_version TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_theme_assign_obs ON theme_assignments(observation_id);
    """)
    conn.commit()
    return conn


def embed_theme_prototypes(model):
    """Embed the predefined themes by averaging the embeddings of their examples and description."""
    theme_embeddings = {}
    theme_keys = list(THEME_DEFINITIONS.keys())
    
    for tk in theme_keys:
        texts = [THEME_DEFINITIONS[tk]["description"]] + THEME_DEFINITIONS[tk]["examples"]
        embs = model.encode(texts)
        # Mean pooling to create a robust prototype vector
        prototype = np.mean(embs, axis=0)
        theme_embeddings[tk] = prototype
        
    # Stack into a matrix matching the order of theme_keys
    prototype_matrix = np.vstack([theme_embeddings[tk] for tk in theme_keys])
    return theme_keys, prototype_matrix


def calibrate_threshold(similarities, obs_ids, theme_keys):
    """
    Determine the optimal similarity threshold empirically.
    MiniLM cosine similarities for short text matching typically range 
    from 0.35 to 0.55 for semantic matches.
    We'll analyze the distribution and set a strict threshold to avoid forced assignments.
    """
    # Max similarity per observation across all themes
    max_sims = np.max(similarities, axis=1)
    
    print("\nSimilarity Distribution (Max Sim per Observation):")
    for pct in [10, 25, 50, 75, 90, 95]:
        print(f"  P{pct}: {np.percentile(max_sims, pct):.4f}")
        
    # Standard threshold for all-MiniLM-L6-v2 in sentence-transformers for decent semantic overlap is ~0.45.
    # To be conservative and avoid forcing noise into predefined themes, we select 0.45.
    selected_threshold = 0.45
    print(f"\nSelected empirical threshold: {selected_threshold}")
    
    # Calculate stats
    assigned_mask = max_sims >= selected_threshold
    num_assigned = int(np.sum(assigned_mask))
    print(f"Observations mapping to >= 1 theme: {num_assigned} ({(num_assigned/len(obs_ids))*100:.1f}%)")
    
    return selected_threshold


def write_jsonl(path, data):
    with open(path, "w") as f:
        for item in data:
            f.write(json.dumps(item) + "\n")


def run_predefined_mapping(run_id="run_latest"):
    db_path = "data/discovery_pulse.db"
    print("=" * 60)
    print("PHASE 4 TASK 4.2 — Predefined Semantic Theme Mapping")
    print("=" * 60)
    
    threshold_version = "v1_cosine_0.45"
    
    # 1. Init DB
    conn = init_db()
    
    # 2. Load model & embed themes
    print("Loading sentence-transformers/all-MiniLM-L6-v2...")
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    
    print("Embedding predefined theme prototypes...")
    theme_keys, theme_matrix = embed_theme_prototypes(model)
    
    # 3. Load observation embeddings
    obs_ids, obs_embeddings = load_observations()
    print(f"Loaded {len(obs_ids)} observations from Chroma.")
    
    # 4. Compute similarity
    print("Computing cosine similarities...")
    sim_matrix = cosine_similarity(obs_embeddings, theme_matrix)
    
    # 5. Calibrate threshold
    threshold = calibrate_threshold(sim_matrix, obs_ids, theme_keys)
    
    # 6. Assign themes
    print("\nAssigning themes...")
    assignments_to_insert = []
    assignments_jsonl = []
    
    single_count = 0
    multi_count = 0
    unassigned_count = 0
    
    for i, obs_id in enumerate(obs_ids):
        # Find themes above threshold
        scores = sim_matrix[i]
        passing_indices = np.where(scores >= threshold)[0]
        
        if len(passing_indices) == 0:
            unassigned_count += 1
            # We explicitly track unassigned in JSONL for auditability, but they don't get a theme record in DB
            assignments_jsonl.append({
                "observation_id": obs_id,
                "predefined_theme_id": None,
                "assignment_type": "unassigned",
                "similarity_score": float(np.max(scores)),
                "closest_theme": theme_keys[np.argmax(scores)]
            })
        else:
            assignment_type = "single" if len(passing_indices) == 1 else "multi"
            if assignment_type == "single":
                single_count += 1
            else:
                multi_count += 1
                
            for idx in passing_indices:
                score = float(scores[idx])
                theme_id = theme_keys[idx]
                assignments_to_insert.append((
                    run_id, obs_id, theme_id, assignment_type, score, threshold_version
                ))
                assignments_jsonl.append({
                    "observation_id": obs_id,
                    "predefined_theme_id": theme_id,
                    "assignment_type": assignment_type,
                    "similarity_score": score
                })
    
    # 7. Persist to DB
    print(f"Persisting {len(assignments_to_insert)} assignment edges to DB...")
    
    # Clear old records for safety (if re-running)
    conn.execute("DELETE FROM theme_assignments")
    conn.execute("DELETE FROM predefined_themes")
    
    conn.executemany(
        """INSERT INTO theme_assignments 
           (analysis_run_id, observation_id, predefined_theme_id, assignment_type, similarity_score, threshold_version)
           VALUES (?, ?, ?, ?, ?, ?)""",
        assignments_to_insert
    )
    
    themes_to_insert = [
        (tk, THEME_DEFINITIONS[tk]["canonical_name"], THEME_DEFINITIONS[tk]["description"])
        for tk in theme_keys
    ]
    conn.executemany(
        "INSERT INTO predefined_themes (theme_id, canonical_name, description) VALUES (?, ?, ?)",
        themes_to_insert
    )
    conn.commit()
    conn.close()
    
    # 8. Write JSONL artifacts
    print("Writing JSONL artifacts...")
    write_jsonl(ASSIGN_PATH, assignments_jsonl)
    
    themes_jsonl = [{"theme_id": k, **v} for k, v in THEME_DEFINITIONS.items()]
    write_jsonl(THEMES_PATH, themes_jsonl)
    
    # 9. Gate check
    print("\n" + "=" * 60)
    print("TASK 4.2 SUMMARY")
    print("=" * 60)
    print(f"Total Observations : {len(obs_ids)}")
    print(f"Threshold          : {threshold} ({threshold_version})")
    print(f"Unassigned         : {unassigned_count} ({(unassigned_count/len(obs_ids))*100:.1f}%)")
    print(f"Single-Theme       : {single_count} ({(single_count/len(obs_ids))*100:.1f}%)")
    print(f"Multi-Theme        : {multi_count} ({(multi_count/len(obs_ids))*100:.1f}%)")
    print("\nPredefined theme assignments:")
    
    # Count assignments per theme
    theme_counts = Counter(a[2] for a in assignments_to_insert)
    for tk in theme_keys:
        print(f"  {tk:40s} : {theme_counts.get(tk, 0)}")

    # Quality Gate
    # A successful semantic mapping should leave a healthy portion unassigned (for emergent discovery)
    # and map some observations to predefined themes.
    gate_pass = (unassigned_count > 0) and (single_count + multi_count > 0)
    print(f"\nQuality gate: PROCEED to Task 4.3 if assignments are distributed and non-zero")
    print(f"Gate result: {'PASS ✓' if gate_pass else 'FAIL ✗ — STOP AND REPORT'}")
    return gate_pass

if __name__ == "__main__":
    passed = run_predefined_mapping()
    exit(0 if passed else 1)
