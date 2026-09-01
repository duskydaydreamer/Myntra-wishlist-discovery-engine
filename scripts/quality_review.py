import json
import sqlite3
import random

CACHE_FILE = "data/phase2_calibration_cache.json"

def get_completed():
    with open(CACHE_FILE, "r") as f:
        cache = json.load(f)
        
    db_path = "data/discovery_pulse.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    query = "SELECT c.cleaned_record_id, c.cleaned_text, r.source, r.raw_text FROM cleaned_records c JOIN raw_records r ON c.raw_record_id = r.raw_record_id"
    rows = conn.execute(query).fetchall()
    
    text_map = {r["cleaned_record_id"]: dict(r) for r in rows}
    
    completed = []
    for k, v in cache.items():
        if v.get("success"):
            rec = text_map[k]
            rec["label"] = v["parsed"]["relevance_label"]
            rec["signals"] = v["parsed"]["signals_detected"]
            completed.append(rec)
            
    return completed

def main():
    completed = get_completed()
    print(f"Total completed: {len(completed)}")
    
    # 1. Look for Meesho record
    meesho = [c for c in completed if "meesho" in c["cleaned_text"].lower() or "meesho" in c["raw_text"].lower()]
    print("\n--- MEESHO PROVENANCE CHECK ---")
    for m in meesho:
        print(f"ID: {m['cleaned_record_id']}")
        print(f"Source: {m['source']}")
        print(f"Text: {m['cleaned_text']}")
        print(f"Label: {m['label']} - {m['signals']}\n")
        
    # 2. Extract specific samples
    highly = [c for c in completed if c["label"] == "highly_relevant"]
    somewhat = [c for c in completed if c["label"] == "somewhat_relevant"]
    not_rel = [c for c in completed if c["label"] == "not_relevant"]
    
    random.seed(10)
    def s(lst, k): return random.sample(lst, min(k, len(lst)))
    
    highly_sample = s(highly, 15)
    somewhat_sample = s(somewhat, 15)
    not_sample = s(not_rel, 15)
    
    # Identify specific edge cases
    # Borderline/ambiguous: could be "somewhat_relevant" or short text or specific keywords
    borderline = s(somewhat, 20)
    
    # Find Hinglish (heuristics: 'hai', 'bhi', 'kya', 'mast')
    hinglish_keywords = [' hai', ' nhi', ' kya', ' bhi', ' kar', ' bahut', ' mast', ' bakwas']
    hinglish = [c for c in completed if any(k in c["cleaned_text"].lower() for k in hinglish_keywords)]
    
    # Short text (words < 5)
    short = [c for c in completed if len(c["cleaned_text"].split()) < 5]
    
    # Competitor mentions
    alt = [c for c in completed if any(k in c["cleaned_text"].lower() for k in ['amazon', 'flipkart', 'ajio', 'meesho', 'zara', 'nykaa'])]
    
    samples_out = {
        "highly": highly_sample,
        "somewhat": somewhat_sample,
        "not_relevant": not_sample,
        "borderline": borderline,
        "hinglish": s(hinglish, 5),
        "short": s(short, 5),
        "competitors": s(alt, 5)
    }
    
    with open("data/quality_review_samples.json", "w") as f:
        json.dump(samples_out, f, indent=2)
        
    print("\nSamples saved to data/quality_review_samples.json")

if __name__ == "__main__":
    main()
