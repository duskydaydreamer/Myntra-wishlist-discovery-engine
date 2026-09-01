import sqlite3
import json
import random

DB_FILE = "data/discovery_pulse.db"

def select_parity_records():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("""
        SELECT c.cleaned_record_id, c.cleaned_text, r.source, r.raw_record_id,
               o.journey_stage, o.wishlist_intent, o.primary_barrier, o.decision_outcome,
               o.evidence_quote, o.is_myntra_specific, cr.relevance_label
        FROM observations o
        JOIN cleaned_records c ON o.cleaned_record_id = c.cleaned_record_id
        JOIN raw_records r ON o.source_record_id = r.raw_record_id
        JOIN classified_records cr ON o.cleaned_record_id = cr.cleaned_record_id
    """)
    rows = [dict(row) for row in c.fetchall()]
    
    selected = []
    seen_ids = set()
    
    random.seed(42)
    random.shuffle(rows)
    
    sources = ["play_store", "youtube", "reddit_rss"]
    for src in sources:
        count = 0
        for r in rows:
            if src in r['source'] and r['cleaned_record_id'] not in seen_ids:
                selected.append(r)
                seen_ids.add(r['cleaned_record_id'])
                count += 1
                if count >= 5:
                    break
                    
    for r in rows:
        if len(selected) >= 20:
            break
        if r['cleaned_record_id'] not in seen_ids:
            selected.append(r)
            seen_ids.add(r['cleaned_record_id'])
            
    with open("data/parity_records_input.json", "w") as f:
        json.dump(selected, f, indent=2)
        
    print(f"Selected {len(selected)} records for parity testing.")
    
if __name__ == "__main__":
    select_parity_records()
