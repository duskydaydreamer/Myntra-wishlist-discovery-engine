import sqlite3
import json

DB_PATH = 'data/discovery_pulse.db'
OUTPUT_FILE = 'data/phase4/opp_evidence_dump.json'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("""
    SELECT o.opportunity_id, o.opportunity_title, e.observation_id, obs.evidence_quote, obs.primary_barrier, obs.purchase_intent, obs.wishlist_intent, obs.source
    FROM opportunity_areas o
    JOIN opportunity_evidence e ON o.opportunity_id = e.opportunity_id
    JOIN observations obs ON e.observation_id = obs.observation_id
""")

rows = cur.fetchall()

result = {}
for row in rows:
    opp_id = row['opportunity_id']
    if opp_id not in result:
        result[opp_id] = {
            'title': row['opportunity_title'],
            'evidence': []
        }
    result[opp_id]['evidence'].append({
        'observation_id': row['observation_id'],
        'quote': row['evidence_quote'],
        'barrier': row['primary_barrier'],
        'purchase_intent': row['purchase_intent'],
        'wishlist_intent': row['wishlist_intent'],
        'source': row['source']
    })

with open(OUTPUT_FILE, 'w') as f:
    json.dump(result, f, indent=2)

print("Evidence dumped successfully")
