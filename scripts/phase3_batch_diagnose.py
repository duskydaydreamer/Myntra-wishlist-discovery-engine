import os
import json
import time
import httpx
import sqlite3
from dotenv import load_dotenv

DB_FILE = "data/discovery_pulse.db"
CACHE_FILE = "data/phase3b_extraction_cache.json"

def expand_enum(field, code):
    if code == "?": return "unknown"
    if not code: return "unknown"
    mappings = {
        "journey_stage": {"DI": "discovery", "EV": "evaluation", "PU": "purchase", "PP": "post_purchase"},
        "wishlist_intent": {"GP": "genuine_purchase", "PT": "price_tracking", "CS": "comparison_shortlist",
                            "IN": "inspiration", "BM": "bookmarking", "AS": "aspirational_saving", "OP": "occasion_planning"},
        "purchase_intent": {"HI": "high", "LO": "low", "NO": "none"},
        "primary_barrier": {"PR": "price", "QU": "quality", "FI": "fit", "DE": "delivery", "TR": "trust"},
        "decision_outcome": {"AB": "abandoned", "BO": "bought", "DE": "delayed", "SW": "switched"},
        "secondary_barriers": {"PR": "price", "QU": "quality", "FI": "fit", "DE": "delivery", "TR": "trust"}
    }
    if field in mappings:
        if code not in mappings[field]:
            raise ValueError(f"Invalid compact code '{code}' for field '{field}'")
        return mappings[field][code]
    return code

def run_batch_diagnosis(batch_size=50):
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.cleaned_record_id, c.cleaned_text, r.raw_record_id, r.source, r.source_url
        FROM classified_records cr
        JOIN cleaned_records c ON cr.cleaned_record_id = c.cleaned_record_id
        JOIN raw_records r ON c.raw_record_id = r.raw_record_id
        WHERE cr.relevance_label IN ('highly_relevant', 'somewhat_relevant')
        AND c.is_spam = 0 AND c.is_duplicate = 0
    """)
    relevant_records = [dict(row) for row in cursor.fetchall()]

    with open(CACHE_FILE, "r") as f:
        extraction_cache = json.load(f)

    remaining_records = [r for r in relevant_records if extraction_cache.get(r["cleaned_record_id"]) == "unresolved_retryable"]
    batch = remaining_records[:batch_size]

    compact_schema = {
        "type": "array", "items": {
            "type": "object", "properties": {
                "i": {"type": "integer"}, "m": {"type": "boolean"},
                "js": {"type": "string", "enum": ["DI", "EV", "PU", "PP", "?"]},
                "wi": {"type": "string", "enum": ["GP", "PT", "CS", "IN", "BM", "AS", "OP", "?"]},
                "pi": {"type": "string", "enum": ["HI", "LO", "NO", "?"]},
                "pc": {"type": "string"}, "t": {"type": "string"},
                "pb": {"type": "string", "enum": ["PR", "QU", "FI", "DE", "TR", "?"]},
                "sb": {"type": "array", "items": {"type": "string", "enum": ["PR", "QU", "FI", "DE", "TR", "?"]}},
                "rc": {"type": "string"}, "u": {"type": "string"},
                "inf": {"type": "string"}, "wa": {"type": "string"},
                "ep": {"type": "string"}, "ac": {"type": "string"},
                "o": {"type": "string"},
                "do": {"type": "string", "enum": ["AB", "BO", "DE", "SW", "?"]},
                "ss": {"type": "string"}, "q": {"type": "string"}
            },
            "required": ["i", "q", "js", "wi", "pi", "pb", "do"]
        }
    }

    system_instruction = """
    Extract structured observations. Return an array of JSON objects.
    Each input record has an integer 'i'. Return multiple objects if multiple insights exist.
    Use '?' for unknown/unsupported values.

    Compact Keys:
    i = local index (integer, MUST match input)
    m = is_myntra_specific (boolean)
    js = journey_stage (DI=discovery, EV=evaluation, PU=purchase, PP=post_purchase)
    wi = wishlist_intent (GP=genuine_purchase, PT=price_tracking, CS=comparison_shortlist, IN=inspiration, BM=bookmarking, AS=aspirational_saving, OP=occasion_planning)
    pi = purchase_intent (HI=high, LO=low, NO=none)
    pc = product_category
    t = theme
    pb = primary_barrier (PR=price, QU=quality, FI=fit, DE=delivery, TR=trust)
    sb = secondary_barriers (array of short codes)
    rc = root_cause (free text)
    u = uncertainty (free text)
    inf = information_needed (free text)
    wa = workaround (free text)
    ep = external_platform_used
    ac = alternative_considered
    o = occasion
    do = decision_outcome (AB=abandoned, BO=bought, DE=delayed, SW=switched)
    ss = segment_signal
    q = evidence_quote (MUST be a verbatim substring of the input text)

    'q' must be an exact substring. Never invent quotes. Use compact enum codes for fixed taxonomies.
    """

    mapped_batch = [{"i": i, "text": r["cleaned_text"]} for i, r in enumerate(batch)]
    payload = {
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"parts": [{"text": json.dumps(mapped_batch)}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "responseSchema": compact_schema,
            "thinkingConfig": {"thinkingLevel": "LOW"}
        }
    }

    print(f"Submitting diagnostic Batch {batch_size} to gemini-3.6-flash...")
    start_time = time.time()
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(url, json=payload)
        lat = time.time() - start_time
        print(f"HTTP {resp.status_code} in {lat:.2f}s")
        if resp.status_code != 200:
            print(f"Error: {resp.text}")
            return

        data = resp.json()
        usage = data.get("usageMetadata", {})
        text_out = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text_out)

        print(f"\nTokens: Prompt={usage.get('promptTokenCount')}, Output={usage.get('candidatesTokenCount')}, Thinking={usage.get('thoughtsTokenCount',0)}, Total={usage.get('totalTokenCount')}")
        print(f"Tokens/record: {usage.get('totalTokenCount',0)/batch_size:.1f}")
        print(f"Objects returned: {len(parsed)}")

        schema_failures = []
        evidence_failures = []
        valid_obs = []

        for obs in parsed:
            idx = obs.get("i")
            if idx is None or idx < 0 or idx >= len(batch):
                continue
            quote = obs.get("q", "")
            original_text = batch[idx]["cleaned_text"]

            if quote != "?" and quote not in original_text:
                # Analyze the failure type
                # Is it a boundary-only issue (quote is close but differs by punctuation/whitespace)?
                stripped_quote = quote.strip().rstrip(".,!?").strip()
                is_boundary_only = stripped_quote in original_text
                evidence_failures.append({
                    "index": idx,
                    "model_quote": quote,
                    "original_text_snippet": original_text[:200],
                    "failure_type": "BOUNDARY_VARIATION" if is_boundary_only else "PARAPHRASE_OR_HALLUCINATION",
                    "stripped_quote_matches": is_boundary_only
                })
            else:
                valid_obs.append(obs)

        print(f"\n--- DIAGNOSIS RESULTS ---")
        print(f"Valid observations: {len(valid_obs)}")
        print(f"Evidence failures: {len(evidence_failures)}")
        for f in evidence_failures:
            print(f"\n  Index {f['index']} [{f['failure_type']}]:")
            print(f"  Model quote : {repr(f['model_quote'][:120])}")
            print(f"  Source text : {repr(f['original_text_snippet'][:120])}")
            print(f"  Stripped match: {f['stripped_quote_matches']}")

        boundary_only = sum(1 for f in evidence_failures if f["failure_type"] == "BOUNDARY_VARIATION")
        true_hallucinations = sum(1 for f in evidence_failures if f["failure_type"] == "PARAPHRASE_OR_HALLUCINATION")
        print(f"\nSummary: {boundary_only} boundary-only, {true_hallucinations} true paraphrase/hallucination failures")
        print(f"Effective valid rate: {len(valid_obs)}/{len(parsed)} ({100*len(valid_obs)/len(parsed):.1f}%)")

        with open("data/batch50_diagnosis.json", "w") as f:
            json.dump({"valid": valid_obs, "failures": evidence_failures, "usage": usage}, f, indent=2)
        print("\nDetailed results saved to data/batch50_diagnosis.json")

if __name__ == "__main__":
    run_batch_diagnosis(50)
