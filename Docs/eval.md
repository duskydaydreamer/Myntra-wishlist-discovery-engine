# Evaluation Plan: Myntra Wishlist Discovery Pulse

> Companion to [`implementation-plan.md`](./implementation-plan.md)
> 
> This document defines the evaluation strategy, test cases, and verification steps for each phase of the Myntra Wishlist Discovery Pulse system. The evaluation plan ensures that acceptance criteria are met and edge cases are handled before proceeding to subsequent phases.

---

## Phase 0 — Project Foundation

### 0.1 Directory & Environment Verification
- **Test:** Run a script checking for the existence of all directories listed in `architecture.md`.
- **Validation:** Ensure `.gitignore` correctly ignores `data/`, `.env`, and bytecode.
- **Criteria:** Script passes with 100% directory match.

### 0.2 Configuration Loading
- **Test:** Execute `config_loader.py` to parse `config.yaml` and `taxonomies.yaml`.
- **Validation:** Assert that all expected keys (e.g., `ingestion.reddit_threads`, `ai.extraction.model`) are present and properly typed.
- **Criteria:** Config loads without raising exceptions. All 8 Reddit threads and 11 YouTube queries are verified present.

### 0.3 Database & Migrations
- **Test:** Run `alembic upgrade head` on an empty SQLite memory database, followed by `alembic downgrade -1`.
- **Validation:** Use SQLAlchemy inspector to verify table structures, foreign keys, and indexes align with the schema definitions.
- **Criteria:** Migrations apply cleanly and revert cleanly.

### 0.4 Infrastructure Spinnup
- **Test:** Run `docker-compose up -d`.
- **Validation:** Ping `localhost:8000/health`, `localhost:3000`, and `localhost:8001` (ChromaDB).
- **Criteria:** All containers report healthy within 30 seconds.

---

## Phase 1 — Data Ingestion Pipeline

### 1.1 Play Store & App Store Adapters
- **Unit Test:** Mock `google-play-scraper` and `app-store-scraper` responses.
- **Edge Case Evaluation:** 
  - Feed mock reviews older than 12 weeks; verify they are excluded.
  - Feed mock reviews with missing text/ratings; verify they are rejected.
  - Feed mock reviews with PII in username fields; verify usernames are stripped before `normalizer.py`.
- **Criteria:** Output matches the `RawRecord` schema perfectly.

### 1.2 Reddit Thread Ingester
- **Unit Test:** Mock `praw.Reddit` submission and comment trees (including `MoreComments`).
- **Edge Case Evaluation:** 
  - Validate that `[deleted]` and `[removed]` comments are dropped.
  - Assert that `parent_post_id` links correctly to the parent for nested comments.
- **Criteria:** Complete mock thread tree is traversed; no `author` fields leak into output.

### 1.3 YouTube API Ingester
- **Unit Test:** Mock `google-api-python-client` responses for search and comment threads.
- **Edge Case Evaluation:**
  - Mock a response with `commentsDisabled` (403); verify graceful skipping.
  - Verify pagination (`pageToken`) is followed until exhaustion.
- **Criteria:** Records extracted have correct `video_id` and `video_title` without creator `authorChannelId` leaks.

### 1.4 Integration & End-to-End Ingestion
- **Integration Test:** Run `backend.pipeline.runner --step ingestion` with mocked endpoints.
- **Criteria:** `data/raw/run_{id}.jsonl` is populated correctly. `pipeline_runs` table updates state to `completed`, `partial`, `failed`, or `interrupted`. Re-running with the same mock data does not duplicate records in `raw_records`.

---

## Phase 2 — Cleaning, Normalization & Relevance Classification

### 2.1 PII Masking
- **Unit Test:** Pass strings containing synthetic names, Indian phone numbers, emails, and dummy order IDs.
- **Criteria:** `presidio-analyzer` catches all synthetic entities. The output `cleaned_text` replaces them with `[NAME]`, `[PHONE]`, etc. Original `raw_text` remains untouched.

### 2.2 Deduplication
- **Unit Test:** Provide exact duplicates and near-duplicates (typo differences).
- **Criteria:** Exact duplicates flag `is_duplicate=True` with correct `duplicate_of`. Near-duplicates correctly flag based on the `near_duplicate_similarity` threshold (e.g., cosine similarity > 0.92).

### 2.3 Spam & Normalization
- **Unit Test:** Feed short spam ("Buy now! Coupon code!"), short valid ("Sizing off"), and multi-language mixed scripts (Hinglish).
- **Criteria:** Spam classifier correctly filters promotional language but keeps short valid reviews. Text is normalized (whitespace collapsed, unicode preserved) and language tags are appropriately assigned.

### 2.4 Relevance Classification (LLM)
- **Evaluation:** Run the relevance prompt against a golden dataset of 50 manually classified reviews (highly, somewhat, not relevant).
- **Metrics:** Compute Precision, Recall, and F1 scores. Generate a confusion matrix to tune the `relevance_confidence_min` boundary.
- **Criteria:** Accuracy >= 90%. Signals detected (e.g., `fit_uncertainty`) match human labeling. Similarity thresholds are treated as initial configurable defaults subject to calibration.

---

## Phase 3 — AI Research Extraction & Evidence Store

### 3.1 Prompt Validation & Extraction Accuracy
- **Evaluation:** Feed 20 complex, multi-dimensional golden records to the extraction engine.
- **Metrics:** Calculate F1 score for behavioral signal detection against human labels. Track Hallucination Rate.
- **Criteria:** 
  - Output strictly adheres to the expected JSON array schema.
  - Every populated field is supported by a verbatim `evidence_quote` existing in `cleaned_text`. Hallucination rate MUST be 0%.
  - At least one multi-observation record correctly splits into >1 valid observation.
  - Uninferable fields correctly default to `"unknown"`.

### 3.2 Error Recovery & Pipeline Resilience
- **Test:** Mock the LLM to return malformed JSON for 10% of requests, and 503 for 5%.
- **Criteria:** Pipeline retries 503s with backoff. Attempts JSON repair for malformed responses, logs failures, and completes the run without crashing as long as `min_extraction_success_rate` > 85%.

### 3.3 Vector Store Validation
- **Test:** Verify configured embedding model generation for 100 sample observations.
- **Criteria:** Both `evidence_quote_embedding` and `observation_embedding` are inserted into ChromaDB. A semantic search query returns the inserted vectors successfully.

### 3.4 Integrity Checks
- **Test:** Run `backend.pipeline.integrity_checker`.
- **Criteria:** It successfully asserts that observation counts match vector store counts, no duplicate/spam records leaked in, and `dataset_stats` successfully records the summary.

---

## Phase 4 — Theme, Pattern & Opportunity Analysis

### 4.1 Theme Grouping
- **Test:** Run grouping over 500 extracted test observations.
- **Criteria:** 
  - Observations meeting the configured/calibrated predefined-theme similarity threshold map to `predefined_themes`.
  - The broader relevant observation corpus undergoes HDBSCAN clustering (noise is a valid output). Clusters > 10 observations create new emergent themes.
  - The aggregate statistics (e.g., `observation_count`, `source_distribution`) match manual SQL rollups of the underlying data.

### 4.2 Root Cause Synthesis
- **Evaluation:** Inspect generated root cause summaries for the top 3 themes.
- **Criteria:** The summary must not propose product solutions. It must strictly summarize "what happened" and "why it existed" grounded ONLY in the sampled evidence quotes.

### 4.3 Opportunity Area Generation
- **Test:** Verify opportunity triggers against mock themes.
- **Criteria:** Opportunities are ONLY generated if `observation_count >= min_observations_for_opportunity`, `purchase_intent IN (high, medium)`, and the synthesized area describes a user problem. `decision_outcome = unknown` must be successfully processed without being rejected.

---

## Phase 5 — Presentation Layer

### 5.1 API Contract Validation
- **Test:** Run FastAPI `TestClient` across all `/api/` endpoints against a seeded test database.
- **Criteria:** All endpoints return 200 OK. Pagination works on `/api/evidence`. Complex query params (e.g., `?theme=...&segment=...`) successfully filter results.

### 5.2 Grounded Query Engine
- **Evaluation:** Feed a benchmark set of ~15-20 standard query types (e.g., factual, subsetting, exploratory, out-of-scope) to `/api/query`.
- **Criteria:** 
  - Intent parser correctly extracts SQL filters.
  - LLM synthesis answers the question grounded ONLY in the retrieved set.
  - Hallucination check: 0% of evidence quotes in the response are fabricated.
  - If a query is fully exploratory, semantic fallback engages and the UI disclaimer is returned.

### 5.3 Frontend Component Rendering (Cypress / Playwright)
- **Test:** End-to-End tests of the Dashboard, Evidence Explorer, and Query Interface.
- **Criteria:** 
  - Dashboard loads stats without crashing and filters dynamically update charts.
  - Evidence explorer paginates and search works responsively.
  - Query Interface history persists in `localStorage` and streaming/loading states display correctly.
  - The "Dataset Scope Caveat" is visually verified on every page.

---

## Phase 6 — Deployment & Weekly Automation (Final Sign-Off)

Before deployment, the system must pass a **Full End-to-End Dry Run**:
1. Run pipeline against the live V1 sources.
2. Confirm pipeline executes cleanly from Phase 1 through Phase 4.
3. Validate Dashboard and Query Interface visually using the generated data.
4. Final manual audit to ensure zero PII leakage into `cleaned_records` or API outputs.
5. **Weekly Automation Validation:**
   - Deployed frontend/backend health checks pass.
   - Persistent storage survives redeployment.
   - Weekly scheduler invokes the shared pipeline runner successfully.
   - Rolling 12-week window is dynamically calculated correctly.
   - Canonical deduplication is preserved across runs, correctly populating `run_records`.
   - Unchanged AI artifacts are reused; only new/changed/failed evidence triggers AI.
   - Source failure and quota exhaustion are logged properly without marking a failed run as completed.
   - Partial, failed, or interrupted runs do NOT replace the latest successful dataset in the UI.
   - Zero-new-record runs complete gracefully.
   - Single-active-run protection blocks overlapping pipeline executions.
   - The latest successful dataset is correctly selected for the dashboard and API.
6. **End-to-End Production Smoke Test:** Validate one live production run works end-to-end.
