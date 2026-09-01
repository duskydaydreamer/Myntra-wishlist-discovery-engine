import json
import os
import httpx
import asyncio
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, ".env"))
OLLAMA_ENDPOINT = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

SYNTHESIS_PROMPT = """
You are a factual synthesis assistant for a qualitative user research system.
A Product Manager has asked a question. You have been provided with exactly matched user observations from the database.

CRITICAL INSTRUCTIONS:
- Answer ONLY from the provided observations. Do not use external knowledge.
- Keep the interface solution-free. Do not automatically generate product solutions (e.g. "AI size recommender"). If asked "What feature should Myntra build?", politely explain that you can only provide the root causes and unmet needs.
- Explicitly label each evidence item with:
  📌 What users said
  🔍 Inferred behavior
  💡 Possible unmet need
- Never fabricate quotes, counts, or percentages. Use the EXACT verbatim quote provided.
- Do NOT generate numeric counts from prose.

Provided Observations:
{evidence}

User Question: {question}

Synthesize a response that directly answers the user's question, supported by the exact evidence provided. 
Return your response in standard Markdown.
"""

def _fallback_answer(evidence_records: list) -> str:
    """Return a transparent evidence-only summary when the local model service is unavailable."""
    quoted_records = [record for record in evidence_records if record.get("evidence_quote")][:3]
    if not quoted_records:
        return "No readable customer quotes were available for this question."

    barriers = []
    for record in evidence_records:
        barrier = record.get("primary_barrier")
        if barrier and barrier not in barriers and barrier not in {"unknown", "none"}:
            barriers.append(barrier)

    if barriers:
        readable_barriers = ", ".join(barrier.replace("_", " ").title() for barrier in barriers[:3])
        introduction = f"The retrieved customer evidence most clearly points to: {readable_barriers}."
    else:
        introduction = "The retrieved customer evidence contains the following relevant feedback."

    evidence_lines = []
    for record in quoted_records:
        quote = record["evidence_quote"].strip()
        source = str(record.get("source") or "public feedback").replace("_", " ").title()
        evidence_lines.append(f'- “{quote}” — {source}')

    return introduction + "\n\nWhat customers wrote:\n" + "\n".join(evidence_lines)

async def synthesize_answer(question: str, evidence_records: list) -> str:
    if not evidence_records:
        return "No supporting evidence was found for the current filters."
        
    # Format evidence
    evidence_text = ""
    for idx, record in enumerate(evidence_records):
        evidence_text += f"Observation {idx+1}:\n"
        evidence_text += f"- Verbatim Quote: \"{record.get('evidence_quote', '')}\"\n"
        evidence_text += f"- Primary Barrier: {record.get('primary_barrier', 'N/A')}\n"
        evidence_text += f"- Workaround: {record.get('workaround', 'N/A')}\n"
        evidence_text += f"- Source: {record.get('source', 'N/A')}\n\n"
        
    prompt = SYNTHESIS_PROMPT.replace("{evidence}", evidence_text).replace("{question}", question)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OLLAMA_ENDPOINT}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.0
                    }
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response") or _fallback_answer(evidence_records)
    except Exception as e:
        print(f"Error in local model synthesis: {e}")
        return _fallback_answer(evidence_records)

