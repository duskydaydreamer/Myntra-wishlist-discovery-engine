import os
import json
import time
import httpx
from dotenv import load_dotenv

def test_round_trip():
    # 1. Valid compact output
    valid_obs = {
        "i": 0,
        "q": "I bought this and the size was off",
        "js": "PU",
        "wi": "?",
        "pi": "HI",
        "pb": "FI",
        "sb": ["QU"],
        "do": "BO"
    }
    expanded = expand_observation(valid_obs, "I bought this and the size was off, returning it.")
    assert expanded["journey_stage"] == "purchase"
    assert expanded["wishlist_intent"] == "unknown"
    assert expanded["primary_barrier"] == "fit"
    assert "quality" in expanded["secondary_barriers"]
    
    # 2. Invalid missing required field (q)
    try:
        expand_observation({"i": 0, "js": "PU"}, "some text")
        assert False, "Should fail on missing quote"
    except ValueError as e:
        assert "Missing required field" in str(e)

    # 3. Invalid out-of-range index (simulated in runner, but we check here)
    # The runner will handle checking i vs batch size

    # 4. Prose in enum field (invalid enum)
    try:
        expand_observation({"i": 0, "q": "text", "js": "I was just looking"}, "text")
        assert False, "Should fail on invalid js"
    except ValueError as e:
        assert "Invalid compact code" in str(e)
        
    # 5. Invalid evidence quote
    try:
        expand_observation({"i": 0, "q": "I bought this", "js": "PU"}, "Different text")
        assert False, "Should fail on quote mismatch"
    except ValueError as e:
        assert "Evidence quote not found" in str(e)

    print("Local round-trip tests passed.")

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

def expand_observation(obs, original_text):
    if "i" not in obs or "q" not in obs:
        raise ValueError("Missing required field 'i' or 'q'")
        
    quote = obs["q"]
    if quote != "?" and quote not in original_text:
        raise ValueError(f"Evidence quote not found in text: {quote}")
        
    expanded = {"local_index": obs["i"], "evidence_quote": quote}
    for k, v in obs.items():
        if k in ["i", "q"]: continue
        
        # Mappings
        field_map = {
            "m": "is_myntra_specific",
            "js": "journey_stage",
            "wi": "wishlist_intent",
            "pi": "purchase_intent",
            "pc": "product_category",
            "t": "theme",
            "pb": "primary_barrier",
            "sb": "secondary_barriers",
            "rc": "root_cause",
            "u": "uncertainty",
            "inf": "information_needed",
            "wa": "workaround",
            "ep": "external_platform_used",
            "ac": "alternative_considered",
            "o": "occasion",
            "do": "decision_outcome",
            "ss": "segment_signal"
        }
        
        full_field = field_map.get(k, k)
        
        if k == "sb" and isinstance(v, list):
            expanded[full_field] = [expand_enum(full_field, code) for code in v]
        elif k in ["js", "wi", "pi", "pb", "do"]:
            expanded[full_field] = expand_enum(full_field, v)
        else:
            expanded[full_field] = "unknown" if v == "?" else v
            
    return expanded

def main():
    test_round_trip()
    
    with open("data/phase3a_eval_records_v2.json", "r") as f:
        all_records = json.load(f)
        
    # Select 3 records:
    # 1. Straightforward
    # 2. Multi-signal 
    # 3. Requires unknown values
    # (Just taking first 3 for smoke test, assuming diversity)
    batch = [all_records[0], all_records[10], all_records[25]]
    
    print(f"Selected {len(batch)} records for smoke test.")
    
    mapped_batch = [{"i": i, "text": r["cleaned_text"]} for i, r in enumerate(batch)]
    
    compact_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "i": {"type": "integer"},
                "m": {"type": "boolean"},
                "js": {"type": "string", "enum": ["DI", "EV", "PU", "PP", "?"]},
                "wi": {"type": "string", "enum": ["GP", "PT", "CS", "IN", "BM", "AS", "OP", "?"]},
                "pi": {"type": "string", "enum": ["HI", "LO", "NO", "?"]},
                "pc": {"type": "string"},
                "t": {"type": "string"},
                "pb": {"type": "string", "enum": ["PR", "QU", "FI", "DE", "TR", "?"]},
                "sb": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["PR", "QU", "FI", "DE", "TR", "?"]}
                },
                "rc": {"type": "string"},
                "u": {"type": "string"},
                "inf": {"type": "string"},
                "wa": {"type": "string"},
                "ep": {"type": "string"},
                "ac": {"type": "string"},
                "o": {"type": "string"},
                "do": {"type": "string", "enum": ["AB", "BO", "DE", "SW", "?"]},
                "ss": {"type": "string"},
                "q": {"type": "string"}
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
    
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"
    
    print("Executing request...")
    start = time.time()
    try:
        with httpx.Client(timeout=90.0) as client:
            resp = client.post(url, json=payload)
            lat = time.time() - start
            
            print(f"HTTP Result: {resp.status_code}")
            resp.raise_for_status()
            
            data = resp.json()
            usage = data.get("usageMetadata", {})
            text_out = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(text_out)
            
            print(f"Latency: {lat:.2f}s")
            print(f"Observations returned: {len(parsed)}")
            print(f"Prompt Tokens: {usage.get('promptTokenCount')}")
            print(f"Candidates Tokens: {usage.get('candidatesTokenCount')}")
            print(f"Thoughts Tokens: {usage.get('thoughtsTokenCount')}")
            print(f"Total Tokens: {usage.get('totalTokenCount')}")
            
            # Validation
            schema_valid_count = 0
            invalid_enums = 0
            quote_failures = 0
            
            for obs in parsed:
                try:
                    idx = obs.get("i")
                    if idx is None or idx < 0 or idx >= len(batch):
                        raise ValueError("Invalid index")
                    orig_text = batch[idx]["cleaned_text"]
                    expand_observation(obs, orig_text)
                    schema_valid_count += 1
                except ValueError as e:
                    if "Invalid compact code" in str(e):
                        invalid_enums += 1
                        print(f"Invalid Enum Error: {e}")
                    elif "Evidence quote" in str(e) or "Missing required" in str(e):
                        quote_failures += 1
                        print(f"Quote/Required Error: {e}")
                    else:
                        print(f"Validation Error: {e}")
                        
            print(f"Schema-valid observations: {schema_valid_count}")
            print(f"Invalid enum values: {invalid_enums}")
            print(f"Quote-substring failures: {quote_failures}")
            
    except Exception as e:
        print(f"Request failed: {e}")
        try:
            print(resp.text)
        except:
            pass

if __name__ == "__main__":
    main()
