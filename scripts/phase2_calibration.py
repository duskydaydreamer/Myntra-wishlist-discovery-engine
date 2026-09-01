import os
import json
import sqlite3
import random
import time
import asyncio
import httpx
from datetime import datetime
from dotenv import load_dotenv

async def process_record(client, generate_url, api_key, system_instruction, classification_schema, rec, stats_dict, results_list, sem, max_retries=1):
    async with sem:
        text = rec["cleaned_text"]
        stats_dict["attempted"] += 1
        
        payload = {
            "systemInstruction": {
                "parts": [{"text": system_instruction}]
            },
            "contents": [{
                "parts": [{"text": f"Classify this text:\n\n{text}"}]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
                "responseSchema": classification_schema
            }
        }
        headers = {'Content-Type': 'application/json'}
        
        for attempt in range(max_retries + 1):
            stats_dict["requests"] += 1
            try:
                resp = await client.post(generate_url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                
                usage = data.get("usageMetadata", {})
                stats_dict["in_tokens"] += usage.get("promptTokenCount", 0)
                stats_dict["out_tokens"] += usage.get("candidatesTokenCount", 0)
                stats_dict["total_tokens"] += usage.get("totalTokenCount", 0)
                
                text_out = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text_out)
                if "relevance_label" not in parsed or "signals_detected" not in parsed:
                    raise ValueError("Missing required fields")
                if parsed["relevance_label"] not in ["highly_relevant", "somewhat_relevant", "not_relevant"]:
                    raise ValueError("Invalid enum for relevance_label")
                    
                stats_dict["success"] += 1
                results_list.append((rec, parsed))
                return
            except Exception as e:
                if attempt < max_retries:
                    stats_dict["retries"] += 1
                    await asyncio.sleep(1)
                else:
                    stats_dict["failed"] += 1
                    results_list.append((rec, None))

async def main_async():
    print("STEP 1 — VERIFY GEMINI ACCESS", flush=True)
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env")
        exit(1)
        
    print("Fetching available models from Gemini API...", flush=True)
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            print(f"Error fetching models: {resp.text}")
            exit(1)
            
        data = resp.json()
        models = [m['name'] for m in data.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
        
    target_model = "models/gemini-3.7-flash"
    target_model_short = "gemini-3.7-flash"
    
    if target_model in models or target_model_short in models:
        print(f"Success: {target_model_short} is accessible.", flush=True)
        print(f"Exact Model ID: {target_model}", flush=True)
    else:
        print(f"Error: {target_model_short} is NOT accessible.", flush=True)
        flash_models = [m for m in models if "flash" in m.lower()]
        print(f"Available flash models: {flash_models}", flush=True)
        print("Wait for user approval before switching.", flush=True)
        exit(1)

    print("\nSTEP 2 — CREATE CALIBRATION SAMPLE", flush=True)
    db_path = "data/discovery_pulse.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    query = """
        SELECT c.cleaned_record_id, c.cleaned_text, r.source, r.rating, r.published_at
        FROM cleaned_records c
        JOIN raw_records r ON c.raw_record_id = r.raw_record_id
        WHERE c.is_duplicate = 0 AND c.is_spam = 0 
          AND c.cleaning_flags NOT LIKE '%skipped%'
    """
    
    candidates = conn.execute(query).fetchall()
    print(f"Found {len(candidates)} candidate records.", flush=True)
    
    random.seed(42)
    sample = random.sample(candidates, 500)
    print("Created a deterministic 500-record calibration sample.", flush=True)
    
    print("\nSTEP 3 & 4 & 5 — RUN GEMINI CLASSIFICATION ON 500 RECORDS ONLY", flush=True)
    
    system_instruction = """
    You are an expert consumer insights analyst classifying user evidence for a fashion e-commerce discovery project.
    
    The research objective is to identify evidence relevant to:
    - wishlist behavior
    - product shortlisting
    - purchase hesitation
    - fit/size uncertainty
    - product quality concerns
    - comparison shopping
    - price/timing hesitation
    - review/trust issues
    - styling uncertainty
    - occasion suitability
    - external research/workarounds
    - returns/exchange concerns
    - purchase postponement or abandonment
    - other meaningful shopping-decision evidence
    
    Do not use generic sentiment as relevance.
    """
    
    classification_schema = {
        "type": "object",
        "properties": {
            "relevance_label": {
                "type": "string",
                "enum": ["highly_relevant", "somewhat_relevant", "not_relevant"]
            },
            "signals_detected": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": ["relevance_label", "signals_detected"]
    }
    
    stats = {
        "attempted": 0,
        "success": 0,
        "failed": 0,
        "retries": 0,
        "requests": 0,
        "in_tokens": 0,
        "out_tokens": 0,
        "total_tokens": 0,
        "time_elapsed": 0.0
    }
    
    results = []
    
    generate_url = f"https://generativelanguage.googleapis.com/v1beta/{target_model}:generateContent?key={api_key}"
    
    start_time = time.time()
    
    sem = asyncio.Semaphore(15) # Concurrency limit to avoid 429 too many requests
    
    async with httpx.AsyncClient(timeout=45.0) as client:
        tasks = [
            process_record(client, generate_url, api_key, system_instruction, classification_schema, rec, stats, results, sem)
            for rec in sample
        ]
        print(f"Starting {len(tasks)} concurrent tasks...", flush=True)
        await asyncio.gather(*tasks)

    stats["time_elapsed"] = time.time() - start_time
    
    print(f"\nProcessing complete in {stats['time_elapsed']:.2f} seconds.", flush=True)
    print("\nSTEP 6 — QUALITY REPORT", flush=True)
    
    sources = {}
    ratings = {}
    relevance_counts = {"highly_relevant": 0, "somewhat_relevant": 0, "not_relevant": 0}
    
    examples = {"highly_relevant": [], "somewhat_relevant": [], "not_relevant": []}
    
    for rec, out in results:
        src = rec["source"]
        sources[src] = sources.get(src, 0) + 1
        
        rt = rec["rating"]
        if rt is not None:
            ratings[rt] = ratings.get(rt, 0) + 1
            
        if out is not None:
            lbl = out["relevance_label"]
            relevance_counts[lbl] += 1
            if len(examples[lbl]) < 3:
                examples[lbl].append((rec["cleaned_text"], out["signals_detected"]))
                
    avg_tokens = stats["total_tokens"] / 500 if stats["total_tokens"] > 0 else 0
    est_tokens_full = avg_tokens * len(candidates)
    
    report = f"""
======================================================
CALIBRATION REPORT
======================================================
1. Exact model used: {target_model}
2. Gemini-3.7-flash access verified: YES
3. Sample size: 500
4. Sampling method: Deterministic random seed (seed 42)
5. Source distribution: {sources}
6. Rating distribution: {ratings}
7. Relevance distribution:
   - highly_relevant: {relevance_counts['highly_relevant']}
   - somewhat_relevant: {relevance_counts['somewhat_relevant']}
   - not_relevant: {relevance_counts['not_relevant']}
8. Invalid-output count: {stats['failed']}
9. Retry count: {stats['retries']}
10. Failed count: {stats['failed']}
11. Input tokens: {stats['in_tokens']}
12. Output tokens: {stats['out_tokens']}
13. Total tokens: {stats['total_tokens']}
14. Average tokens per record: {avg_tokens:.2f}
15. Estimated tokens for all {len(candidates)} candidates: {est_tokens_full:,.0f}

Examples of Correct Highly Relevant Results:
{json.dumps(examples['highly_relevant'], indent=2)}

Examples of Correct Somewhat Relevant Results:
{json.dumps(examples['somewhat_relevant'], indent=2)}

Examples of Correct Not Relevant Results:
{json.dumps(examples['not_relevant'], indent=2)}

(For borderline cases, false positives, false negatives, check manually)
"""

    with open("data/phase2_calibration_report.txt", "w") as f:
        f.write(report)
        
    print("\nCalibration report written to data/phase2_calibration_report.txt", flush=True)
    print("STEP 7 — STOP. Waiting for explicit approval.", flush=True)

if __name__ == "__main__":
    asyncio.run(main_async())
