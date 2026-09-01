# TOKEN-EFFICIENCY RULE — APPLY TO ALL FUTURE AI CALLS

From this point forward, minimize token usage aggressively without weakening:
- evidence faithfulness
- schema validity
- traceability
- required research fields
- retrieval quality
- evaluation quality

Follow these rules for every LLM-powered step.

## 1. LOCAL CODE FIRST
Use deterministic code/SQL for filtering, counts, sorting, aggregation, deduplication, ID mapping, enum expansion, date logic, statistics, validation. Do not ask an LLM to do deterministic work.

## 2. SEND ONLY NECESSARY INPUT
Never send full records if only `cleaned_text` is required. Never send unrelated metadata. Never send entire threads/conversations when one evidence item is sufficient. Use bounded context.

## 3. NEVER REPEAT LONG DATABASE IDS
Do not ask the model to reproduce UUIDs or long canonical record IDs. Before each request:
- map canonical IDs to short local integers: 0, 1, 2...
- send only the short index to the model
- restore the real ID in deterministic code afterward

## 4. USE COMPACT INFERENCE SCHEMAS
Use short model-facing keys and enum codes where safe (e.g. `i` for index, `rl` for relevance label). Expand them in code before persistence. The final DB/API schema must remain readable; compact schemas exist only at the LLM boundary.

## 5. KEEP VERBATIM EVIDENCE UNCHANGED
Do NOT abbreviate, summarize, compress, or paraphrase `evidence_quote`. Evidence quotes must remain verbatim substrings of `cleaned_text`.

## 6. NO UNNECESSARY PROSE
Do not request explanations, reasoning, summaries, rationale, markdown, or commentary unless the specific task requires synthesis. For classification/extraction: return structured output only.

## 7. THINKING
Use the lowest supported thinking/reasoning level by default. Do not use medium/high thinking unless an evaluation demonstrates a meaningful quality improvement that justifies the extra token usage.

## 8. BATCH WHEN SAFE
Batch multiple independent records into one request when mappings remain unambiguous, schema remains valid, and quality does not degrade. Determine batch size through a small evaluation before scaling.

## 9. CACHE EVERYTHING
Cache successful AI artifacts using at least `cleaned_text_hash`, provider, model, prompt_version, and taxonomy/schema version. Do not call the model again for unchanged inputs.

## 10. NEVER RETRY SUCCESSFUL WORK
Retries apply only to unresolved/invalid records. On partial batch failure: preserve valid results and retry only unresolved records where mapping is safe.

## 11. OUTPUT BUDGET
Keep arrays and strings bounded. Do not generate duplicate signals, repeated source text, redundant explanations, or long descriptions when an enum/value is sufficient.

## 12. PROMPT SIZE
Keep system/task instructions concise. Do not repeat large taxonomy descriptions on every request if deterministic codes or a compact vocabulary can represent them safely.

## 13. RETRIEVAL/SYNTHESIS
For later synthesis:
- retrieve only top-K relevant evidence
- deduplicate evidence first
- select representative evidence locally
- never send the whole observation corpus
- use database-derived aggregates rather than asking the LLM to count

## 14. TOKEN TELEMETRY
Persist per-request usage metadata: provider, model, prompt_version, request_id/batch_id, records_in_request, promptTokenCount, candidatesTokenCount, thoughtsTokenCount (if available), totalTokenCount, latency, retry_count, success/failure.

## 15. TOKEN GATE BEFORE SCALING
Every new AI stage must first run on a small evaluation sample. Before scaling report: input tokens/record, output tokens/record, thinking tokens/record, total tokens/record, tokens/successful observation, request count, malformed-output rate, quality metrics. Do not scale automatically.

## 16. OPTIMIZATION DECISION
If token usage appears high, first identify whether the cause is prompt size, evidence size, verbose IDs/keys/enums, excessive output fields, thinking tokens, retries, or redundant processing. Fix the actual cause instead of changing models blindly.

## 17. FREE-TIER CONSTRAINT
This project must remain operable on free-tier APIs. Prefer architectural efficiency over paid quota: local processing -> filtering -> batching -> compact schema -> caching -> evaluation -> scaling.

## 18. MOST IMPORTANT RULE
Never reduce token usage by sacrificing research correctness or evidence integrity. Optimize representation and orchestration first. For every future AI phase, include a short TOKEN EFFICIENCY section in the final report and STOP for approval before large-scale execution.
