import os
import json
import time
import httpx
from dotenv import load_dotenv

INPUT_FILE = "data/parity_records_input.json"
OUTPUT_FILE = "data/parity_evaluation_results.json"
TELEMETRY_FILE = "data/parity_telemetry.json"

def run_parity():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={api_key}"
    
    with open(INPUT_FILE, "r") as f:
        records = json.load(f)
        
    compact_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
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
    
    batch_size = 10
    chunks = [records[i:i+batch_size] for i in range(0, len(records), batch_size)]
    
    telemetry = {
        "GenerateContent_calls": 0,
        "successful_calls": 0,
        "failed_calls": 0,
        "http_429s": 0,
        "http_503s": 0,
        "timeouts": 0,
        "total_elapsed_time": 0,
        "tokens": {"prompt": 0, "candidate": 0, "thinking": 0, "total": 0}
    }
    
    results = []
    
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
            if code not in mappings[field]: return code
            return mappings[field][code]
        return code

    def expand_observation(obs, original_text):
        if "i" not in obs or "q" not in obs: return None
        expanded = {"local_index": obs["i"], "evidence_quote": obs["q"]}
        for k, v in obs.items():
            if k in ["i", "q"]: continue
            field_map = {
                "m": "is_myntra_specific", "js": "journey_stage", "wi": "wishlist_intent",
                "pi": "purchase_intent", "pc": "product_category", "t": "theme",
                "pb": "primary_barrier", "sb": "secondary_barriers", "rc": "root_cause",
                "u": "uncertainty", "inf": "information_needed", "wa": "workaround",
                "ep": "external_platform_used", "ac": "alternative_considered",
                "o": "occasion", "do": "decision_outcome", "ss": "segment_signal"
            }
            full_field = field_map.get(k, k)
            if k == "sb" and isinstance(v, list):
                expanded[full_field] = [expand_enum(full_field, code) for code in v]
            elif k in ["js", "wi", "pi", "pb", "do"]:
                expanded[full_field] = expand_enum(full_field, v)
            else:
                expanded[full_field] = "unknown" if v == "?" else v
        return expanded

    overall_start = time.time()
    
    with httpx.Client(timeout=90.0) as client:
        for batch_idx, batch in enumerate(chunks):
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
            
            telemetry["GenerateContent_calls"] += 1
            print(f"Sending request for batch {batch_idx}...")
            
            try:
                resp = client.post(url, json=payload)
                if resp.status_code == 429:
                    telemetry["failed_calls"] += 1
                    telemetry["http_429s"] += 1
                    print(f"429 Hit: {resp.text}")
                    continue
                elif resp.status_code == 503:
                    telemetry["failed_calls"] += 1
                    telemetry["http_503s"] += 1
                    print(f"503 Hit: {resp.text}")
                    continue
                    
                resp.raise_for_status()
                telemetry["successful_calls"] += 1
                
                data = resp.json()
                usage = data.get("usageMetadata", {})
                telemetry["tokens"]["prompt"] += usage.get("promptTokenCount", 0)
                telemetry["tokens"]["candidate"] += usage.get("candidatesTokenCount", 0)
                telemetry["tokens"]["thinking"] += usage.get("thoughtsTokenCount", 0)
                telemetry["tokens"]["total"] += usage.get("totalTokenCount", 0)
                
                text_out = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text_out)
                
                # Expand and map back to records
                for obs in parsed:
                    idx = obs.get("i")
                    if idx is not None and 0 <= idx < len(batch):
                        record = batch[idx]
                        expanded = expand_observation(obs, record["cleaned_text"])
                        if expanded:
                            results.append({
                                "cleaned_record_id": record["cleaned_record_id"],
                                "cleaned_text": record["cleaned_text"],
                                "original_3_6_obs": {k:v for k,v in record.items() if k not in ["cleaned_record_id", "cleaned_text", "source", "raw_record_id", "relevance_label"]},
                                "new_3_5_obs": expanded
                            })
                            
            except httpx.ReadTimeout:
                telemetry["failed_calls"] += 1
                telemetry["timeouts"] += 1
                print("Timeout hit")
            except Exception as e:
                telemetry["failed_calls"] += 1
                print(f"Exception: {e}")
                
            time.sleep(2.0)
            
    telemetry["total_elapsed_time"] = time.time() - overall_start
    
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)
        
    with open(TELEMETRY_FILE, "w") as f:
        json.dump(telemetry, f, indent=2)
        
    print("Parity execution finished.")

if __name__ == "__main__":
    run_parity()
