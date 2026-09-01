import os
import json
import asyncio
import httpx
from dotenv import load_dotenv

# The 6 records we successfully extracted from the first 3.7-flash run report
records = [
    {
        "id": "1",
        "text": "Meesho things are not up to the mark..In the photo it is different but in real what I ordered I didn't get I got different product .so I un subscribed the app . ...",
        "3.7_label": "highly_relevant",
        "3.7_signals": ["product quality concerns", "review/trust issues"]
    },
    {
        "id": "2",
        "text": "Haha mostly i read comment about the short length",
        "3.7_label": "highly_relevant",
        "3.7_signals": ["fit/size uncertainty", "review/trust issues"]
    },
    {
        "id": "3",
        "text": "as of my experience COD Orders only safe and fast [NAME]",
        "3.7_label": "somewhat_relevant",
        "3.7_signals": ["review/trust issues", "purchase hesitation"]
    },
    {
        "id": "4",
        "text": "such a amazing app for shopping",
        "3.7_label": "not_relevant",
        "3.7_signals": []
    },
    {
        "id": "5",
        "text": "my shopping experience so good",
        "3.7_label": "not_relevant",
        "3.7_signals": []
    },
    {
        "id": "6",
        "text": "Lipstick collection v lye aaj ka lipstick mst hai",
        "3.7_label": "not_relevant",
        "3.7_signals": []
    }
]

async def classify(client, generate_url, system_instruction, schema, r):
    payload = {
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        },
        "contents": [{
            "parts": [{"text": f"Classify this text:\n\n{r['text']}"}]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "responseSchema": schema
        }
    }
    resp = await client.post(generate_url, json=payload)
    resp.raise_for_status()
    data = resp.json()
    usage = data.get("usageMetadata", {})
    text_out = data["candidates"][0]["content"]["parts"][0]["text"]
    parsed = json.loads(text_out)
    return r, parsed, usage

async def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    target_model = "models/gemini-3.5-flash-lite"
    generate_url = f"https://generativelanguage.googleapis.com/v1beta/{target_model}:generateContent?key={api_key}"
    
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
    schema = {
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
    
    stats = {"in": 0, "out": 0, "total": 0}
    agreement = 0
    disagreements = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = [classify(client, generate_url, system_instruction, schema, r) for r in records]
        resps = await asyncio.gather(*tasks)
        
        for r, parsed, usage in resps:
            stats["in"] += usage.get("promptTokenCount", 0)
            stats["out"] += usage.get("candidatesTokenCount", 0)
            stats["total"] += usage.get("totalTokenCount", 0)
            
            new_label = parsed["relevance_label"]
            if new_label == r["3.7_label"]:
                agreement += 1
            else:
                disagreements.append({
                    "text": r["text"],
                    "3.7_label": r["3.7_label"],
                    "3.5L_label": new_label,
                    "3.7_signals": r["3.7_signals"],
                    "3.5L_signals": parsed["signals_detected"]
                })
                
    report = f"""
# Comparison Report: gemini-3.7-flash vs gemini-3.5-flash-lite

> [!NOTE]
> **Correction on Cached Records**: In my previous update, I incorrectly stated there were 21 "successful" classifications in the cache. They were actually 21 *failed* records (429 Rate Limit errors) saved by the retry loop before it was cancelled. The only truly successful 3.7-flash classifications we have are the 6 examples printed in the very first diagnostic report. I have run the comparison on those 6 exact records.

## 1. Actual Quota Information (gemini-3.5-flash-lite)
- **Quota Metric**: `generativelanguage.googleapis.com/generate_content_free_tier_requests`
- **Quota ID**: `GenerateRequestsPerMinutePerProjectPerModel-FreeTier`
- **Limit type**: **Requests Per Minute (RPM)**
- **Quota Limit**: **15 RPM** (Verified via 429 payload)

*Unlike `3.7-flash` which is severely limited to 20 requests per day, `3.5-flash-lite` gives us 15 requests per minute, which is more than enough to comfortably process the 500 calibration records using our batching script.*

## 2. Request & Token Usage
- **Records Processed**: {len(records)}
- **Malformed Outputs**: 0
- **Total Input Tokens**: {stats['in']}
- **Total Output Tokens**: {stats['out']}
- **Total Tokens**: {stats['total']}
- **Average Tokens/Record**: {stats['total']/len(records):.2f}

## 3. Classification Comparison (N=6)
- **Exact Label Agreement**: {agreement} ({(agreement/len(records))*100:.1f}%)
- **Total Disagreements**: {len(disagreements)}

### Disagreements Details
"""
    for d in disagreements:
        report += f"\n**Text:** {d['text']}\n"
        report += f"- **3.7-flash Label:** `{d['3.7_label']}` (Signals: {d['3.7_signals']})\n"
        report += f"- **3.5-flash-lite Label:** `{d['3.5L_label']}` (Signals: {d['3.5L_signals']})\n"
        
    with open("data/flash_lite_comparison.md", "w") as f:
        f.write(report)
        
    print("Report written to data/flash_lite_comparison.md")

if __name__ == "__main__":
    asyncio.run(main())
