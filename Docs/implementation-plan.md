# Implementation Plan: Myntra Wishlist Discovery Pulse

> Derived from [`architecture.md`](./architecture.md) and [`problemStatement.md`](./problemStatement.md)
>
> **Do not begin implementation until this plan has been reviewed and approved.**

---

## Overview

The system is built in **seven sequential phases**, each producing a verified, independently testable output before the next phase begins. No phase starts until the previous phase is complete and its acceptance criteria are met.

```text
Phase 0 — Project Foundation
         ↓
Phase 1 — Data Ingestion Pipeline
         ↓
Phase 2 — Cleaning, Normalization & Relevance Classification
         ↓
Phase 3 — AI Research Extraction & Evidence Store
         ↓
Phase 4 — Theme, Pattern & Opportunity Analysis
         ↓
Phase 5 — Presentation Layer
         ↓
Phase 6 — Deployment, Weekly Automation & Demo Readiness
```

Each phase is broken into **tasks**. Every task has:
- A clear **objective**
- **Files / components** it produces
- **Acceptance criteria** that must be verified before moving on

---

## Phase 0 — Project Foundation

**Goal:** Establish the project skeleton, configuration system, database schema, and development environment so all subsequent phases have a stable, consistent base to build on.

---

### Task 0.1 — Repository & Directory Structure

**Objective:** Create the full project directory layout as specified in `architecture.md §8`.

**Create:**

```
myntra-discovery-pulse/
├── config/
│   ├── config.yaml
│   └── taxonomies.yaml
├── data/
│   ├── raw/
│   ├── cleaned/
│   ├── classified/
│   ├── observations/
│   ├── themes/
│   └── opportunities/
├── backend/
│   ├── ingestion/connectors/
│   ├── cleaning/
│   ├── classification/prompts/
│   ├── extraction/prompts/
│   ├── analysis/
│   ├── store/migrations/
│   ├── query/
│   ├── api/routers/
│   ├── api/schemas/
│   ├── pipeline/
│   └── ai/
├── frontend/
│   ├── app/dashboard/
│   ├── app/evidence/
│   ├── app/query/
│   ├── components/
│   └── lib/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── scripts/
├── docs/
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
├── requirements.txt
├── pyproject.toml
└── README.md
```

**Acceptance criteria:**
- [ ] Directory structure exists and matches `architecture.md §8`
- [ ] `.gitignore` excludes `data/`, `.env`, `__pycache__`, `*.pyc`
- [ ] `README.md` contains project name, purpose, and setup instructions stub

---

### Task 0.2 — Configuration Files

**Objective:** Create `config/config.yaml` and `config/taxonomies.yaml` with all V1 values from `architecture.md §12`.

**`config/config.yaml` must include:**

```yaml
ingestion:
  app_store_window_weeks: 12
  play_store_window_weeks: 12
  record_window_start: true
  record_window_end: true

  sources_enabled:
    - play_store        # com.myntra.android, 12-week window
    - app_store         # ID 907394059, storefront 'in', 12-week window
    - reddit            # 8 curated threads, thread-based
    - youtube           # API-discovered via search queries

  reddit_threads:
    - https://www.reddit.com/r/IndianFashionAddicts/comments/14r29cl/show_me_ur_myntra_wishlist/
    - https://www.reddit.com/r/IndianFashionAddicts/comments/14k5wqe/do_you_guys_buy_from_myntra_how_do_you_discover/
    - https://www.reddit.com/r/IndianFashionAddicts/comments/1osrk03/myntra_is_deleting_reviews_from_the_listed/
    - https://www.reddit.com/r/IndianFashionAddicts/comments/16ccycw/i_was_checking_myntra_for_a_shirt_and_came_across/
    - https://www.reddit.com/r/IndianFashionAddicts/comments/159bh63/size_difference_help/
    - https://www.reddit.com/r/IndianFashionAddicts/comments/15x8thm/recommend_me_brands_from_myntra/
    - https://www.reddit.com/r/IndianFashionAddicts/comments/132mwar/myntra_hikes_prices_after_product_is_added_to_the/
    - https://www.reddit.com/r/IndianFashionAddicts/comments/14cbt53/whats_going_on_with_myntra/

  youtube_search_queries:
    - "Myntra haul"
    - "Myntra try on haul"
    - "Myntra clothing haul"
    - "Myntra sizing review"
    - "Myntra size review"
    - "Myntra quality review"
    - "Myntra honest review"
    - "Myntra dress haul"
    - "Myntra jeans review"
    - "Myntra wedding outfits"
    - "Myntra vs AJIO"

ai:
  classification:
    provider: "configurable/approved Gemini provider"
    model: "verified configured Gemini Flash model"
  extraction:
    provider: "configurable/approved Gemini provider"
    model: "verified configured Gemini Flash model"
  synthesis:
    provider: "Gemini"
    model: "verified configured Gemini Flash model"
  embedding:
    provider: "local/configurable"
    model: "local/configurable"
  prompt_version: "v1"

# The exact Gemini model ID must be recorded only after API availability verification.
# Do not use:
# - openai/gpt-oss-120b
# - Qwen
# - random replacement models
# - unavailable Groq models
# unless explicitly approved later.

thresholds:
  relevance_confidence_min: 0.70
  observation_confidence_min: 0.60
  min_observations_for_theme: 10
  min_observations_for_opportunity: 15
  near_duplicate_similarity: 0.92
  min_extraction_success_rate: 0.85

privacy:
  pii_masking_enabled: true
  entities_to_mask:
    - PERSON
    - EMAIL
    - PHONE_NUMBER
    - LOCATION
    - URL_WITH_CREDENTIALS

storage:
  db_url: "sqlite:///data/discovery_pulse.db"
  vector_store: "chromadb"
  file_store: "local"
  file_store_path: "data/"
```

**`config/taxonomies.yaml` must include all V1 taxonomy values** for `wishlist_intents`, `purchase_barriers`, `segment_signals`, and `predefined_themes` as specified in `architecture.md §12.2`.

**Acceptance criteria:**
- [ ] `config.yaml` loads without errors and all keys are accessible
- [ ] All 8 Reddit thread URLs are present and correctly formatted
- [ ] All 11 YouTube search queries are present
- [ ] `taxonomies.yaml` contains complete initial taxonomy values
- [ ] Config can be loaded and validated via a `config_loader.py` utility

---

### Task 0.3 — Python Environment & Dependencies

**Objective:** Set up the Python environment with all required packages.

**`requirements.txt` must include:**

```
# Core
fastapi
uvicorn[standard]
pydantic>=2.0
sqlalchemy>=2.0
alembic

# Data collection
google-play-scraper
app-store-scraper
praw
google-api-python-client

# AI / ML
google-generativeai
sentence-transformers
chromadb

# PII detection
presidio-analyzer
presidio-anonymizer
spacy

# Utilities
pyyaml
structlog
python-dotenv
httpx
tenacity        # retries

# Dev
pytest
pytest-asyncio
```

**Acceptance criteria:**
- [ ] `pip install -r requirements.txt` completes without errors
- [ ] `python -c "import fastapi, sqlalchemy, praw, chromadb, google.generativeai"` succeeds
- [ ] `spacy download en_core_web_lg` completes (required for PII NER)

---

### Task 0.4 — Database Schema & Migrations

**Objective:** Create the SQLAlchemy models and Alembic migrations for all tables defined in `architecture.md §5`.

**Tables to create:**

| Table | Key columns |
|---|---|
| `pipeline_runs` | `run_id`, `triggered_by`, `started_at`, `completed_at`, `status`, `review_window_start`, `review_window_end`, `source_statuses`, `source_record_counts`, `relevant_record_count`, `observation_count`, `theme_count`, `opportunity_count`, `provider_model_versions`, `prompt_version`, `warnings`, `errors` |
| `raw_records` | Full schema from `architecture.md §5` (Canonical public-source evidence) |
| `run_records` | `run_record_id`, `pipeline_run_id FK`, `raw_record_id FK` (Many-to-many membership linking evidence to a pipeline run) |
| `cleaned_records` | `cleaned_record_id`, `raw_record_id FK`, `cleaned_text`, `is_duplicate`, `is_spam`, `cleaning_flags` |
| `classified_records` | `classified_record_id`, `cleaned_record_id FK`, `relevance_label`, `relevance_confidence`, `signals_detected` |
| `observations` | Full schema from `architecture.md §5` including `model_id`, `prompt_version`, `created_in_pipeline_run_id FK` |
| `themes` | Full schema from `architecture.md §5` |
| `theme_observations` | Junction table: `theme_id FK`, `observation_id FK` |
| `opportunity_areas` | Full schema from `architecture.md §5` |
| `opportunity_observations` | Junction table: `opportunity_id FK`, `observation_id FK` |
| `dataset_stats` | Aggregated stats per pipeline run |

**Acceptance criteria:**
- [ ] `alembic upgrade head` runs cleanly against a fresh SQLite database
- [ ] All tables exist with correct column types and foreign key constraints
- [ ] Models are importable from `backend/store/database.py`
- [ ] A rollback (`alembic downgrade -1`) also works cleanly

---

### Task 0.5 — Docker Compose & Local Environment

**Objective:** Create `docker-compose.yml` bringing up backend, frontend, database, and ChromaDB.

**Services:**

```yaml
services:
  backend:   # FastAPI on :8000
  frontend:  # Next.js on :3000
  db:        # PostgreSQL on :5432 (for prod parity; SQLite for dev)
  chromadb:  # ChromaDB on :8001
```

**Acceptance criteria:**
- [ ] `docker-compose up` starts all services without errors
- [ ] `GET http://localhost:8000/health` returns `{"status": "ok"}`
- [ ] `GET http://localhost:3000` returns the frontend shell page
- [ ] ChromaDB is reachable at `:8001`

---

### Phase 0 Completion Gate

Before proceeding to Phase 1, verify:

- [ ] All directory structure is in place
- [ ] Config loads correctly with all V1 values
- [ ] Database schema is applied and all tables exist
- [ ] Docker Compose environment runs cleanly
- [ ] A simple `pytest tests/unit/` run passes (even if no tests exist yet — the runner itself must work)

---

## Phase 1 — Data Ingestion Pipeline

**Goal:** Implement the four V1 source adapters so raw records from all sources are collected, normalized to a common schema, written to both JSONL files and the `raw_records` database table, and are ready for the cleaning layer.

> **Privacy rule:** SOURCE ACCOUNT IDENTIFIERS (reviewer usernames, Reddit usernames, YouTube commenter handles, or channel identifiers) must be removed immediately during ingestion. Strip them at the point of collection before any write.

---

### Task 1.1 — Base Ingestion Infrastructure

**Objective:** Create the shared ingestion utilities all four adapters will use.

**Files:**

- `backend/ingestion/normalizer.py` — validates and coerces any raw dict into the `RawRecord` Pydantic schema; rejects records missing `raw_text`
- `backend/ingestion/writer.py` — writes normalized records to `data/raw/run_{id}.jsonl` and inserts into `raw_records` table (upsert by `raw_record_id`)
- `backend/ingestion/run_tracker.py` — creates and updates a `pipeline_runs` row; records `started_at`, source counts, and errors
- `backend/store/database.py` — SQLAlchemy session factory (shared across all phases)

**`RawRecord` Pydantic schema fields:**
```
raw_record_id, source, source_type, source_url, published_at,
collected_at, title, raw_text, rating, product_context,
evidence_type, parent_post_id, video_id, video_title,
search_query, selection_reason, comment_sampling_rule
```

**Acceptance criteria:**
- [ ] `normalizer.py` raises `ValidationError` on records missing `raw_text`
- [ ] `writer.py` appends records to JSONL and inserts into DB without duplicates (idempotent by `raw_record_id`), and updates `run_records` junction table
- [ ] `run_tracker.py` creates a `pipeline_runs` row with `status=running` and updates it to `completed`, `partial`, `failed`, or `interrupted`

---

### Task 1.2 — PlayStoreAdapter

**Objective:** Fetch Myntra reviews from Google Play Store for the most recent 12 weeks and normalize them to the raw record schema.

**File:** `backend/ingestion/connectors/play_store.py`

**Implementation details:**

- App: `com.myntra.android`
- Library: `google-play-scraper` — `reviews()` function with `lang='en'`, `country='in'`
- Fetch reviews in batches; continue until the configured `play_store_window_weeks` cutoff date is reached
- Exclude any review where `published_at < (today - 12 weeks)` — **before** writing to any output
- **Strip** `userName` and any reviewer-identifying fields before normalization
- Map to `RawRecord`:
  - `source = "play_store"`
  - `source_type = "review"`
  - `source_url = "https://play.google.com/store/apps/details?id=com.myntra.android"`
  - `evidence_type = "myntra_specific"`
  - `product_context = "myntra"`
  - `rating` ← star rating (1–5)
  - `published_at` ← review date
  - `raw_text` ← review body
  - `parent_post_id = null`, `video_id = null`, `video_title = null`

**Acceptance criteria:**
- [ ] Adapter fetches at least some reviews without API errors
- [ ] All returned records have `published_at` within the 12-week window
- [ ] No record contains `userName` or any reviewer identifier
- [ ] All records pass `RawRecord` validation
- [ ] Records are written to `data/raw/run_{id}.jsonl` and inserted into `raw_records`
- [ ] Adapter is covered by a unit test using a mocked `google-play-scraper` response

---

### Task 1.3 — AppStoreAdapter

**Objective:** Fetch Myntra reviews from the Apple App Store (India, most recent 12 weeks).

**File:** `backend/ingestion/connectors/app_store.py`

**Implementation details:**

- App ID: `907394059`, country: `in`
- Library: `app-store-scraper` — `AppStore(country='in', app_name='myntra', app_id=907394059)`
- Paginate through reviews; stop when `published_at < (today - 12 weeks)`
- **Strip** `userName` and reviewer identity before normalization
- Map to `RawRecord`:
  - `source = "app_store"`
  - `source_type = "review"`
  - `source_url = "https://apps.apple.com/in/app/myntra-fashion-shopping-app/id907394059"`
  - `evidence_type = "myntra_specific"`
  - `product_context = "myntra"`
  - `title` ← review title (App Store reviews have titles)
  - `rating` ← star rating
  - `published_at` ← review date
  - `raw_text` ← review body

**Acceptance criteria:**
- [ ] Same criteria as Task 1.2, applied to App Store data
- [ ] `title` field is populated where present (App Store reviews include a title field)
- [ ] Unit test covers the 12-week filter cutoff boundary

---

### Task 1.4 — RedditThreadIngester

**Objective:** Ingest all posts and comments from the 8 curated Reddit threads.

**File:** `backend/ingestion/connectors/reddit.py`

**Implementation details:**

- Library: Keep Reddit ingestion behind an adapter. Support the approved access method available during implementation (e.g., PRAW or equivalent). If programmatic access is unavailable, a compliant curated import path must remain possible for the already-selected threads. Do NOT add uncontrolled Reddit crawling; strictly limit to curated threads.
- Thread list is read from `config.yaml → ingestion.reddit_threads`
- For each thread URL:
  - Extract submission ID from URL
  - Fetch submission (original post) via `reddit.submission(id=...)`
  - Call `submission.comments.replace_more(limit=None)` to expand all nested comments
  - Recurse through `submission.comments.list()` to collect all comments and replies
- **No time-window filter** — ingest all posts and comments regardless of age
- **Strip** `author` (Reddit username) before normalization; do not store it
- Map original post to `RawRecord`:
  - `source = "reddit"`, `source_type = "post"`
  - `source_url` = thread URL
  - `raw_text` = `submission.selftext`
  - `title` = `submission.title`
  - `published_at` = `datetime.utcfromtimestamp(submission.created_utc)`
  - `parent_post_id = null` (it is the root)
  - `evidence_type = "myntra_specific"` (all curated threads are Myntra-related; set `category_level` only if the specific comment contains no Myntra reference)
- Map each comment to `RawRecord`:
  - `source_type = "comment"`
  - `parent_post_id` = submission ID (for top-level) or parent comment ID (for replies)
  - `raw_text` = `comment.body`

**Acceptance criteria:**
- [ ] All 8 threads are ingested (original post + all comments + nested replies)
- [ ] No Reddit `author` field appears in any stored record
- [ ] `parent_post_id` correctly links comments to their thread submission ID
- [ ] Records with `[deleted]` or `[removed]` as body are discarded (not stored)
- [ ] Adapter is idempotent — re-running does not duplicate records (use submission/comment ID as `raw_record_id`)
- [ ] Unit test uses a mocked PRAW submission object

---

### Task 1.5 — YouTubeAPIIngester

**Objective:** Discover relevant Myntra YouTube videos via API search queries and ingest their public comments.

**File:** `backend/ingestion/connectors/youtube.py`

**Implementation details:**

- API: YouTube Data API v3 (`google-api-python-client`); requires `YOUTUBE_API_KEY` in `.env`
- Search queries are read from `config.yaml → ingestion.youtube_search_queries`
- **Discovery step** (per query):
  - Call `youtube.search().list(q=query, type='video', part='snippet', maxResults=25)`
  - Apply video selection criteria from `architecture.md §4.1.2` — only keep videos relevant to Myntra shopping, try-ons, fit/sizing, quality, styling, occasion, comparison, or purchase decisions
  - Prefer videos with `commentCount > 0` (check via `videos().list(part='statistics')`)
  - Deduplicate video IDs across queries (same video may appear in multiple searches)
- **Comment ingestion step** (per selected video):
  - Call `youtube.commentThreads().list(videoId=..., part='snippet,replies', maxResults=100)`
  - Paginate with `pageToken` until all comments are fetched
  - For threads with replies not yet loaded, call `youtube.comments().list(parentId=..., part='snippet')`
- **Strip** `authorDisplayName` and `authorChannelId` before normalization
- Map each comment to `RawRecord`:
  - `source = "youtube"`, `source_type = "video_comment"`
  - `video_id` = YouTube video ID
  - `video_title` = video title from search snippet
  - `video_url` = `https://www.youtube.com/watch?v={video_id}`
  - `source_url` = `video_url`
  - `parent_post_id` = `video_id` for top-level comments; parent comment ID for replies
  - `published_at` = comment `publishedAt`
  - `raw_text` = comment `textOriginal`
  - `evidence_type`: classify based on whether comment mentions Myntra specifically

**Acceptance criteria:**
- [ ] At least one search query successfully returns videos and comments
- [ ] No `authorDisplayName` or `authorChannelId` in any stored record
- [ ] `video_id` and `video_title` are populated on all YouTube records
- [ ] `parent_post_id` is set on reply comments
- [ ] Duplicate video IDs across search queries are deduplicated
- [ ] Records where `raw_text` is empty or purely emoji/whitespace are discarded
- [ ] Unit test mocks the YouTube API client; integration test flag guards live API calls

---

### Task 1.6 — Ingestion Runner & Pipeline Entry Point

**Objective:** Wire all four adapters into a single runnable ingestion step.

**File:** `backend/pipeline/runner.py` (ingestion step)

**CLI usage:**
```bash
python -m backend.pipeline.runner --step ingestion [--sources play_store,app_store,reddit,youtube]
```

**Behaviour:**
- Creates a `pipeline_run` row with `status=running`
- Runs each enabled adapter in sequence
- Writes all raw records to `data/raw/run_{id}.jsonl` and `raw_records` table
- Updates `pipeline_run` with total record counts and appropriate status (`completed`, `partial`, `failed`, or `interrupted`)
- Logs structured JSON per adapter: records fetched, records rejected, errors

**Acceptance criteria:**
- [ ] Running `--step ingestion` with all 4 sources produces a non-empty `data/raw/run_{id}.jsonl`
- [ ] `pipeline_runs` row is updated with correct record counts and appropriate status (`completed`, `partial`, `failed`, or `interrupted`)
- [ ] Re-running the same ingestion run does not create duplicate records
- [ ] Failure of one adapter is logged but does not abort the other adapters (resulting in a `partial` run)

---

### Phase 1 Completion Gate

**Status: COMPLETED**

Verified results:
- Total canonical raw_records: 71,963

Source distribution:
- Play Store: 44,401
- YouTube: 26,946
- App Store: 500
- Reddit: 116

Verified rules:
- all four approved V1 source groups were ingested
- source account identities/user handles were removed before raw_records storage
- canonical raw_records remain preserved
- no mock data was used as real evidence

---

## Phase 2 — Cleaning, Normalization & Relevance Classification

**Goal:** Clean raw records (dedup, PII masking, spam removal, normalization), produce inspectable `cleaned_records`, and then classify each cleaned record for research relevance.

**Execution is divided into:**
- **Phase 2A — Local Preparation**
- **Phase 2B — Relevance Classification**

---

### Phase 2A — Local Preparation (COMPLETED)

Record Phase 2A local preparation as implemented with:

- raw records evaluated: 71,963
- cleaned non-duplicate records stored: 35,313
- exact + near duplicates flagged/bypassed: 36,650
- records passed through PII masking: 35,313
- deterministic pre-filter kept: 22,790
- deterministic pre-filter skipped, excluding duplicates: 12,523
- external LLM calls: 0
- external API tokens: 0
- relevance classification: not started
- extraction: not started

Skip reason distribution:
- spam heuristic: 2,006
- other foreign languages: 6,850
- generic short/low-info: 3,430
- app technical only: 141
- URL only: 51
- pure Hindi tagged: 41
- emoji/symbol only: 4
- empty/no text: 0

Validated recall protections:
- <8 words is NOT an automatic exclusion
- emoji presence is NOT an automatic exclusion
- Hinglish/mixed-language evidence is preserved
- short records containing useful shopping signals are preserved
- meaningful emoji-containing records are preserved
- pure Hindi records are preserved canonically and tagged for unsupported-language handling
- raw_text remains untouched
- cleaned_text is the downstream privacy-safe representation

---

### Task 2.1 — PII Masking

**Objective:** Detect and mask personally identifiable information in raw text before any further processing.

**File:** `backend/cleaning/pii_masker.py`

**Implementation:**

- Use `presidio-analyzer` + `presidio-anonymizer`
- Load `en_core_web_lg` spaCy model for NER
- Detect entity types: `PERSON`, `EMAIL_ADDRESS`, `PHONE_NUMBER`, `LOCATION`, `URL` (where credential-bearing), `CREDIT_CARD`, `IN_AADHAAR`, `IN_PAN`
- Replace each detected span with a fixed placeholder: `[NAME]`, `[EMAIL]`, `[PHONE]`, `[ADDRESS]`, `[ORDER_ID]`
- **Contextual Retention:** Do NOT automatically remove useful contextual city/region mentions (e.g., "Bangalore").
- Operate on a **copy** of `raw_text` — never modify the original stored in `raw_records`. Untouched `raw_text` must be classified as restricted engineering/raw data, kept private/local, excluded from Git, APIs, UI, exports, and downstream AI processing.
- The masked version becomes `cleaned_text` in `cleaned_records`. Use `cleaned_text` exclusively for relevance classification, extraction, embeddings, evidence quotes, UI, and exports. Guarantee no personal identifiers appear in downstream datasets.

**Acceptance criteria:**
- [ ] `[NAME]` replaces reviewer name references in text (e.g., "Hi, I am Priya and…")
- [ ] Email addresses and phone numbers are masked
- [ ] `raw_text` in `raw_records` is never modified
- [ ] Masking is tested against at least 5 fixture examples covering different PII types

---

### Task 2.2 — Deduplication

**Objective:** Identify exact and near-duplicate records.

**File:** `backend/cleaning/deduplicator.py`

**Implementation:**

- **Exact duplicate:** SHA-256 hash of `raw_text` (lowercased, whitespace-normalized). If hash already exists in DB, mark `is_duplicate=True`, `duplicate_of=<first_seen_raw_record_id>`.
- **Near-duplicate:** Generate TF-IDF or sentence-transformer embedding for each record. Compute cosine similarity against candidates from the same source. Flag records above `near_duplicate_similarity` threshold (default 0.92) as near-duplicates.
- Near-duplicate detection runs per source (Play Store vs Reddit vs YouTube — do not cross-source deduplicate at this stage).

**Acceptance criteria:**
- [ ] Identical review text from two separate ingestion runs is flagged as `is_duplicate=True`
- [ ] Near-duplicate threshold is read from `config.yaml` — changing it does not require code changes
- [ ] `duplicate_of` points to the correct earlier record's ID
- [ ] Deduplication unit test uses a fixture set with known duplicates and near-duplicates

---

### Task 2.3 — Spam & Low-Information Filter

**Objective:** Identify and flag spam, advertisements, and content-free records deterministically.

**File:** `backend/cleaning/spam_filter.py`

**Implementation:**

- **Deterministic pre-filter:** Task 2.3 is a deterministic/local conservative pre-filter.
- Its role is only to remove obvious low-information material before relevance classification.
- It must NOT act as the final research relevance classifier.
- It should favor recall.
- No external LLM is required for Task 2.3.
- Records must not be excluded merely because they are: short, informal, emoji-containing, Hinglish/mixed-language, grammatically incorrect, or negative.
- Preserve borderline records for Task 2.6.
- Store result as `is_spam: bool` and `cleaning_flags: list[str]` on the `cleaned_record`

**Acceptance criteria:**
- [ ] "Best app ever!!! 🔥" is flagged `content_free` or `keep`
- [ ] "Download our coupon app now! Save 80%!" is flagged `spam`
- [ ] A short but meaningful review ("sizing is completely off, returned it") is flagged `keep`
- [ ] No external LLM is used in this task.

---

### Task 2.4 — Text Normalization

**Objective:** Normalize whitespace, encoding, and formatting in cleaned text.

**File:** `backend/cleaning/normalizer.py`

**Steps:**
1. Unicode normalization (NFC)
2. Strip leading/trailing whitespace
3. Collapse internal whitespace sequences to single space
4. Preserve newlines (useful for paragraph structure in longer reviews)
5. Detect language via `langdetect` — tag `language` field. English and Hinglish/mixed languages are processed normally. Very short text should not be discarded solely due to language uncertainty.
6. Pure non-English texts are preserved and tagged, but marked `extraction_status = unsupported_language` to exclude from AI processing.

**Acceptance criteria:**
- [ ] Text with multiple consecutive spaces is normalized
- [ ] Unicode characters (Hindi script, emoji) are preserved, not stripped
- [ ] `language` field is populated on all cleaned records
- [ ] Pure non-English records are appropriately skipped for extraction

---

### Task 2.5 — Cleaning Pipeline & `cleaned_records` Writer

**Objective:** Chain all cleaning steps into a single pass and write output for canonical non-duplicate records.

**File:** `backend/cleaning/cleaning_runner.py`

**Implementation:**

- raw_records remain the canonical evidence store
- duplicates remain preserved in raw_records
- duplicate relationships/flags remain traceable
- duplicate records do not require redundant cleaned_text artifacts
- cleaned_records are created for canonical/non-duplicate records that enter the cleaning pipeline
- downstream AI processing excludes duplicate records
- no canonical evidence is deleted

**Acceptance criteria:**
- [ ] Every canonical/non-duplicate `raw_record` processed receives a `cleaned_record`.
- [ ] Duplicates are bypassed and do not receive redundant `cleaned_records`.
- [ ] Records flagged as spam/low-info are excluded from subsequent steps.
- [ ] `data/cleaned/run_{id}.jsonl` is a valid inspectable JSONL file.

---

### Task 2.6A — Relevance Classification Calibration

**Objective:** Calibrate the relevance classifier. This is the NEXT executable project step.

**File:** `backend/classification/relevance_classifier.py`

**Requirements:**

1. Use the 22,790 pre-filter-kept candidate records as the candidate population.
2. Create a deterministic 500-record development/calibration sample.
3. Make the sample appropriately diverse across:
   - sources
   - ratings where available
   - publication dates
   - short and long records
   - strong shopping signals
   - ambiguous/borderline records
   - Hinglish/mixed-language records
   - meaningful emoji-containing records
4. Verify the exact Gemini Flash model available through the configured `GEMINI_API_KEY` before execution.
5. Do NOT guess a model ID.
6. If the intended Gemini Flash model is unavailable:
   - report available appropriate Gemini Flash model IDs
   - stop
   - require approval before switching
7. Run relevance classification only on the 500-record calibration sample.
8. Preserve the approved relevance labels:
   `highly_relevant`
   `somewhat_relevant`
   `not_relevant`
9. Keep `signals_detected`.
10. Keep output concise to reduce tokens.
11. Validate:
   - schema validity
   - failures
   - retries
   - label distribution
   - false-positive examples
   - false-negative examples
   - request usage
   - input tokens
   - output tokens
12. STOP for approval after calibration.

Do NOT classify all 22,790 records automatically.

---

### Task 2.6B — Capped Relevance Classification Scaling

**Objective:** Safely scale relevance classification. Begins only after Task 2.6A is approved.

**Requirements:**

- classify eligible remaining candidate records
- process in bounded/resumable batches
- cache successful classifications
- reuse unchanged classifications
- enforce configurable request/token/budget limits
- safely stop when limits are reached
- leave unfinished records pending instead of restarting
- invalid classifier output: validate, retry once, then `classification_status=failed`
- failed classification must not flow into extraction

---

### Phase 2B — Capped Relevance Classification Scaling (COMPLETED)

Record Phase 2B relevance classification as completed with:

- **Candidate population:** 22,790 pre-filter-kept records
- **Calibration sample (Task 2.6A):** 500-record deterministic dev sample — calibration passed, quality approved
- **Scaling (Task 2.6B):** All 22,790 records successfully classified across two processing runs
  - Run 1 (Task 303): 4,250 records — 85 batches of 50, plus 1 retry (86 requests)
  - Run 2 (Task 326): 17,990 records — 360 batches of 50, plus 1 failure and 1 retry (362 requests)
  - Close-out: 50 structurally-failed records re-processed at batch size 10 — all resolved
- **Classification model:** `gemini-3.5-flash-lite`
- **Prompt version:** `v1` relevance classification prompt

**Final label distribution:**
- highly_relevant: 2,576
- somewhat_relevant: 7,173
- not_relevant: 13,041
- unresolved / failed: 0
- **Total relevant (highly + somewhat):** 9,749

**Integrity verified:**
- Total eligible candidate IDs: 22,790
- Valid classified IDs: 22,790
- Legitimate unresolved IDs: 0
- Duplicates / hallucinations persisted: 0

---

### Phase 2 Completion Gate

**Status: COMPLETED**

Verified results:

- [x] Phase 2A local preparation is verified (35,313 canonical cleaned records; 22,790 deterministic pre-filter candidates)
- [x] Relevance classifier calibration passes (500-record dev sample, approved quality)
- [x] Classification quality reviewed and approved
- [x] All 22,790 candidate records successfully classified — no pending or unresolved records
- [x] classified_records contain valid relevance outputs with correct label distribution
- [x] Classification failures: 0
- [x] Classification distribution reported (highly_relevant: 2,576 / somewhat_relevant: 7,173 / not_relevant: 13,041)
- [x] Token and request usage recorded (auditable via phase2_calibration_report.txt and task_2_6b_report.txt)

---

## Phase 3 — AI Research Extraction & Evidence Store

**Goal:** Transform every `highly_relevant` and `somewhat_relevant` record into one or more structured behavioral observations. Persist observations in the database and generate vector embeddings for semantic retrieval.

---

### Phase 3 — Extraction Scaling (COMPLETED)

**Extraction model:** `gemini-3.6-flash`
**Prompt version:** `v2-compact-phase3b`

- **Eligible relevant records:** 9,749 (2,576 highly_relevant + 7,173 somewhat_relevant)
- **Successfully processed source records:** 9,165
- **Successfully processed (zero observations):** 576
- **Permanently failed (documented):** 8
- **Unprocessed / pending records:** 0
- **Precision repair queue:** 0

**Canonical observations persisted:** 9,171

**Embeddings:**
- Evidence-quote embeddings: 9,171
- Observation embeddings: 9,171
- DB/Chroma set equality: PASS

**Integrity Checks:**
- Global evidence integrity: PASS
- DB/cache consistency: PASS

---

### Task 3.1 — Extraction Prompt (v1)

**Objective:** Write and version the extraction prompt that instructs the LLM to extract structured multi-dimensional behavioral observations from a single user conversation.

**File:** `backend/extraction/prompts/extraction_v1.txt`

**Prompt requirements:**
- Instructs the model to extract **all** observable behavioral dimensions from a single text — not just the dominant topic
- Requires a verbatim `evidence_quote` (verifiable substring from `cleaned_text`) for every populated field
- Requires `"unknown"` for any field that cannot be reliably inferred
- Prohibits fabricating motivations, outcomes, counts, or quotes
- Specifies JSON array output format (one object per observation)
- References all taxonomy values from `taxonomies.yaml` inline
- Includes 2–3 worked examples (few-shot) with complex multi-observation extractions

**Acceptance criteria:**
- [ ] Prompt produces valid JSON array output when tested against 5 fixture reviews
- [ ] Multi-observation extraction: the sizing+YouTube example from the problem statement produces ≥4 observations
- [ ] `evidence_quote` field is populated on every observation
- [ ] No observation is produced without a supporting `evidence_quote`

---

### Task 3.2 — Observation Extractor

**Objective:** Run the extraction prompt against each relevant cleaned record and persist the resulting observations.

**File:** `backend/extraction/observation_extractor.py`

**Implementation:**

- Load records where `relevance_label IN ('highly_relevant', 'somewhat_relevant')` and `extraction_status IS NULL`
- For each record, call configured extraction model with the extraction prompt
- Parse JSON array response; validate each observation against the `Observation` Pydantic schema
- Assign a `uuid-v4` `observation_id` to each observation
- Store `extraction_model` and `prompt_version` on every observation
- On LLM failure: mark record `extraction_status = 'failed'`, log error, continue to next record
- On JSON parse failure: attempt one retry with a stricter prompt; if still failing, mark as failed
- Write to `observations` table and append to `data/observations/run_{id}.jsonl`

**LLM reliability guardrails (from `architecture.md §6.2`):**
- System prompt enforces: "Only use verbatim text from the input. Never paraphrase as a quote."
- Any observation where `evidence_quote` is empty or cannot be substring-verified against `cleaned_text` is rejected before storage
- `ai_confidence < 0.5` is allowed — do not auto-discard low-confidence observations, but flag them

**Acceptance criteria:**
- [ ] A single review produces multiple observations where the text contains multiple behavioral signals
- [ ] Every stored observation has a non-empty `evidence_quote`
- [ ] Extraction failures are logged but do not abort the pipeline
- [ ] Overall extraction success rate meets `min_extraction_success_rate` (0.85 by default)
- [ ] `data/observations/run_{id}.jsonl` is a valid, inspectable JSONL file

---

### Task 3.3 — Vector Embeddings

**Objective:** Generate and store sentence embeddings for each observation's evidence quote and combined observation text to enable semantic retrieval.

**File:** `backend/ai/embedder.py` + `backend/store/vector_store.py`

**Implementation:**

- Use configured embedding model
- Generate two embeddings per observation:
  - `evidence_quote_embedding`: embedding of `evidence_quote` alone
  - `observation_embedding`: embedding of concatenated key fields (`evidence_quote` + `uncertainty` + `information_needed` + `workaround`)
- Store both in ChromaDB with `observation_id` as the document ID and observation metadata as ChromaDB metadata
- This enables both quote-level and full-observation-level semantic retrieval

**Acceptance criteria:**
- [ ] All observations in `data/observations/run_{id}.jsonl` have embeddings stored in ChromaDB
- [ ] ChromaDB query for "user forgot about wishlisted product" returns semantically relevant observations
- [ ] Embedding generation failures are logged and retried up to 3 times before skipping

---

### Task 3.4 — Evidence Store Integrity Check

**Objective:** After extraction, verify the evidence store is internally consistent before proceeding to analysis.

**File:** `backend/pipeline/integrity_checker.py`

**Checks to run:**
- Every observation references a valid `source_record_id` in `raw_records`
- Every observation has a non-null, non-empty `evidence_quote`
- No observation references a record marked `is_duplicate=True` or `is_spam=True`
- ChromaDB embedding count matches `observations` table row count
- `dataset_stats` row is written for the run with all counts

**Acceptance criteria:**
- [ ] Integrity checker runs after extraction and logs a pass/fail report
- [ ] Any integrity failure is flagged with the offending `observation_id`
- [ ] `dataset_stats` is written and accessible via the API

---

### Phase 3 Completion Gate

**Status: COMPLETED**

- [x] All 9,749 eligible records have an explicit terminal extraction state (9,165 successfully processed)
- [x] `observations` table is populated with 9,171 valid, evidence-backed canonical records
- [x] Evidence-quote validation passes for every persisted observation (0 empty / substring mismatches)
- [x] All 9,171 observations have vector embeddings in ChromaDB (9,171 evidence-quote embeddings + 9,171 observation embeddings)
- [x] Evidence-store integrity check passes:
  - No empty/invalid evidence quotes
  - All observations map to valid canonical source records
  - No duplicates from retry/resume
  - No spam or duplicate source records in the observations table
  - Vector count reconciles with observations table count
  - Dataset stats written and verified
- [x] `data/observations/run_*.jsonl` artifacts are inspectable and reconciled

---

## Phase 4 — Theme, Pattern & Opportunity Analysis

**Goal:** Discover evidence-backed recurring user patterns, root-cause hypotheses, unmet needs, and opportunity areas that may influence wishlist→purchase behavior. Phase 4 builds a new, versioned, derived analysis layer on top of the immutable Phase 3 observation corpus. No Phase 3 canonical field (`observations.theme`, `observations.root_cause`, or any other) is modified.

**Phase 3 Foundation (IMMUTABLE):**
- Canonical observations: **9,171**
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional)
- `observation_embeddings` stored in ChromaDB — DB/Chroma ID-set equality = PASS
- Phase 3 `theme` field: 5,558 distinct strings → NOT a canonical taxonomy; treated as weak secondary signal only
- Phase 3 `root_cause` field: 6,345 empty + 789 "unknown" → NOT primary evidence
- `primary_barrier` and `evidence_quote` are the most reliable structured analytical fields

**New Derived Entities (Phase 4 only):**

All Phase 4 outputs are written to NEW derived tables with `analysis_run_id` versioning:

| Table | Purpose |
|---|---|
| `analysis_runs` | Run metadata, config version, timestamps |
| `predefined_themes` | Canonical theme definitions with semantic prototypes |
| `theme_assignments` | Observation → predefined theme mapping (cosine similarity scored) |
| `semantic_clusters` | HDBSCAN emergent cluster records |
| `cluster_memberships` | Observation → cluster membership + probability |
| `cluster_representatives` | Representative evidence quotes per cluster/theme |
| `segment_stats` | Behavioral segment cross-analysis |
| `root_cause_hypotheses` | LLM-synthesized root-cause hypotheses per cluster/theme |
| `unmet_needs` | Derived unmet-need layer (separate from theme/root-cause/opportunity) |
| `opportunities` | Final opportunity areas |
| `opportunity_evidence` | Evidence backing each opportunity |

---

### Task 4.1 — Semantic Representation & Clustering Evaluation

**Objective:** Empirically determine whether the existing `all-MiniLM-L6-v2` observation embeddings are semantically coherent enough for meaningful pattern discovery, and select the best clustering representation.

**File:** `backend/analysis/phase4_1_representation_eval.py`

**Critical constraints:**
- Do NOT use Gemini embeddings or any text-embedding API.
- Do NOT construct the primary representation from Phase 3 `theme` strings (highly fragmented).
- Do NOT assume current embeddings are clustering-ready without evaluation.
- Original 384-dimensional Chroma vectors remain the canonical semantic/retrieval vectors and must NOT be overwritten.

**Compare two baseline approaches:**

**Approach A — Direct:**
`observation_embeddings` → L2 normalization → HDBSCAN directly

**Approach B — Reduced:**
`observation_embeddings` → L2 normalization → UMAP (dimensionality reduction for clustering only) → HDBSCAN

UMAP is used only for clustering representation; it does NOT replace or overwrite the original Chroma embeddings.

**Calibrate, do not guess.** Run a bounded, documented parameter sweep across reasonable values for:

- HDBSCAN: `min_cluster_size` (e.g., 20–100), `min_samples` (e.g., 5–20), metric
- UMAP (where used): `n_neighbors` (e.g., 10–30), `n_components` (e.g., 10–30), `min_dist`

Selection criteria — evaluate using:
- Semantic coherence (manual review of cluster membership samples)
- Cluster separation and stability
- Interpretability and evidence traceability
- Useful noise behavior (noise is valid — do NOT minimize noise to select config)
- Absence of duplicate/near-duplicate concepts across clusters
- Suitability for root-cause/unmet-need discovery downstream

Do NOT select a config because it minimizes noise, maximizes or minimizes cluster count, or looks visually attractive.

**If both MiniLM approaches are poor:**
Before switching models, compare locally using the SAME MiniLM model:
- Approach A-alt: `evidence_quote`-only embedding
- Approach B-alt: existing multi-field observation embedding

Only consider a different embedding model if local alternatives are empirically inadequate. Do NOT silently switch.

**Output artifact:** `data/phase4/task_4_1_representation_eval.json` containing:
- All configurations tested
- Cluster counts, unique source support, noise rate, cluster-size distribution
- Stability observations and manual semantic coherence results
- Selected configuration with documented rationale

**Acceptance criteria:**
- [ ] Direct HDBSCAN vs UMAP→HDBSCAN compared empirically with documented results
- [ ] Selected configuration is documented with rationale
- [ ] HDBSCAN noise is retained as valid — not force-assigned
- [ ] Evaluation artifact written to `data/phase4/`
- [ ] No Chroma/Phase 3 embeddings were overwritten

---

### Task 4.2 — Predefined Semantic Theme Mapping

**Objective:** Map observations to the 10 predefined research themes from `taxonomies.yaml` using semantic similarity — NOT Phase 3 theme string matching.

**File:** `backend/analysis/phase4_2_predefined_mapping.py`

**Implementation:**
1. For each predefined theme, define:
   - Canonical theme name
   - Semantic description (what this theme covers)
   - Inclusion meaning and exclusion/boundary notes
   - Short representative semantic examples (5–8 per theme)
2. Embed theme prototypes locally using the SAME `all-MiniLM-L6-v2` model.
3. For each observation, compute cosine similarity between its embedding and all theme prototypes.
4. Apply calibrated similarity threshold(s) to assign — allow zero, one, or multiple assignments.

**DO NOT:**
- String-match Phase 3 theme values
- Force every observation to a predefined theme
- Hardcode arbitrary similarity thresholds without empirical calibration

**Threshold calibration:** Build a manually reviewed stratified validation set covering clearly matching, borderline, multi-theme, and correctly-unassigned examples across diverse sources, barriers, and intents. Measure: correct assignments, incorrect assignments, missed assignments, forced assignments. Choose threshold(s) empirically and version them.

**Storage:** All assignments go to the NEW `theme_assignments` derived table — NEVER to `observations.theme`.

```
theme_assignments:
  analysis_run_id
  observation_id
  predefined_theme_id
  assignment_type        -- single / multi / unassigned
  similarity_score
  threshold_version
```

**Acceptance criteria:**
- [ ] All 10 predefined themes have defined semantic prototypes
- [ ] Similarity threshold is empirically calibrated, documented, and versioned
- [ ] `theme_assignments` populated; assignment breakdown (single/multi/unassigned) reported
- [ ] `observations.theme` is NOT modified
- [ ] Multi-theme assignments are explicitly tracked

---

### Task 4.3 — Emergent Semantic Pattern Discovery

**Objective:** Run the selected HDBSCAN strategy across the FULL 9,171-observation corpus to discover emergent patterns not captured by predefined themes.

**File:** `backend/analysis/phase4_3_emergent_clustering.py`

**Critical rules:**
- Cluster across ALL observations — NOT only those that failed predefined mapping.
- Predefined and emergent analysis are complementary: an observation can be predefined-only, emergent-only, both, or neither.
- Do NOT use a fixed number of clusters.
- Do NOT force HDBSCAN noise to "Other" or any cluster.
- Do NOT automatically discard small/low-support clusters — retain for inspection; they must NOT become strong opportunity claims without sufficient evidence.

**Storage:**

```
semantic_clusters:
  cluster_id
  analysis_run_id
  clustering_config_version
  observation_count
  unique_source_count
  is_noise               -- boolean; true = HDBSCAN noise group
  canonical_label        -- nullable initially; populated in Task 4.6
  created_at

cluster_memberships:
  cluster_id
  observation_id
  membership_probability -- HDBSCAN soft-clustering score where available
```

**Acceptance criteria:**
- [ ] Clustering runs across all 9,171 observations
- [ ] HDBSCAN configuration matches the selection from Task 4.1
- [ ] `semantic_clusters` and `cluster_memberships` populated
- [ ] Noise is tracked as a valid group, not force-assigned
- [ ] Cluster-size distribution and unique-source support reported

---

### Task 4.4 — Theme/Cluster Aggregation & Representative Evidence

**Objective:** Compute deterministic statistics for every predefined theme and every meaningful emergent cluster BEFORE any LLM interpretation.

**File:** `backend/analysis/phase4_4_aggregation.py`

**Per theme/cluster, compute deterministically:**
- `observation_count` AND `unique_source_record_count` (both required)
- `pct_of_eligible_source_records` where methodologically valid
- `highly_relevant` vs `somewhat_relevant` distribution
- `source_distribution` (count per source)
- `myntra_specific_count` vs `category_level_count`
- `primary_barrier` distribution
- `wishlist_intent` distribution
- `purchase_intent` distribution
- `journey_stage` distribution
- `decision_outcome` distribution
- `segment_signal` distribution
- `product_category` distribution
- `uncertainty` patterns (non-empty, non-unknown values)
- `information_needed` patterns
- `workaround` patterns
- `external_platform_used` distribution
- `alternative_considered` patterns
- `occasion` patterns where relevant
- `avg_ai_confidence`

**IMPORTANT:** Use `unique_source_record_count` as the primary support/prevalence unit. Observation count and unique source count must BOTH be retained. The 4 multi-observation source records must not inflate prevalence claims.

**Representative evidence selection (NOT first-N):**
Select a small configurable set (default: 5–7 quotes per cluster/theme) using:
- Semantic centrality / medoid behavior
- Sub-pattern diversity
- Source diversity (avoid Play Store monopoly)
- Intent/outcome diversity where useful
- Non-duplication of evidence quotes
- Evidence faithfulness

Store in `cluster_representatives` with exact:
- `observation_id`, `source_record_id`, `evidence_quote` (verbatim), `source`, `source_url`, relevant structured metadata

All representative quotes must be exact verbatim `evidence_quote` values from Phase 3.

**Acceptance criteria:**
- [ ] Every predefined theme and emergent cluster (non-noise) has both `observation_count` and `unique_source_count`
- [ ] `source_distribution` sums to `observation_count`
- [ ] `representative_quotes` contains only exact Phase 3 `evidence_quote` values
- [ ] Representative selection uses centrality/diversity logic, not first-N

---

### Task 4.5 — Behavioral Segment Analysis

**Objective:** Cross-analyze observations by `segment_signal` to surface segment-level behavioral patterns.

**File:** `backend/analysis/phase4_5_segment_analysis.py`

**Notes on data reality:** 6,723 observations have empty `segment_signal`; 1,902 are "unknown". Do not force every observation into a segment. Unknown is valid. Do not treat `segment_signal` as ground truth.

**Per meaningful segment (sufficient observation support), compute:**
- Unique source-record count
- Observation count
- Predefined theme distribution
- Emergent cluster distribution
- Wishlist intent distribution
- Purchase intent distribution
- Journey-stage distribution
- Decision-outcome distribution
- Common primary barriers
- Common uncertainties
- Information needs
- Workarounds
- External platforms used
- Representative exact quotes (verbatim Phase 3 `evidence_quote`)

**Storage:** `segment_stats` table with `analysis_run_id`.

**Acceptance criteria:**
- [ ] Top 3+ segments by observation count have complete statistics
- [ ] `segment_stats` populated with `analysis_run_id`
- [ ] Unknown/empty segment signals are valid — not force-assigned
- [ ] Both observation count and unique source count retained per segment

---

### Task 4.6 — Canonical Cluster/Pattern Labeling

**Objective:** Use an LLM to generate canonical names and descriptions for meaningful emergent clusters — ONLY after deterministic characterization is complete.

**File:** `backend/analysis/phase4_6_cluster_labeling.py`

**Do NOT:** Send all 9,171 observations to an LLM. Do NOT label before aggregation is complete.

**For each meaningful cluster, construct a compact evidence package containing:**
- Representative exact quotes (from Task 4.4)
- Observation count + unique-source count
- Source distribution
- Primary barrier distribution
- Wishlist/purchase intent distribution
- Journey stage and decision outcome distribution
- Recurring uncertainties, information needs, workarounds
- External research behavior

**LLM output (per cluster):**
```json
{
  "canonical_label": "...",
  "evidence_grounded_description": "..."
}
```

Label must describe a **USER PROBLEM or BEHAVIORAL PATTERN** — never a feature/solution.

- ✅ GOOD: "Uncertainty about whether clothing will fit as expected"
- ❌ BAD: "AI Size Recommender"
- ✅ GOOD: "Cross-platform comparison before committing to purchase"
- ❌ BAD: "Comparison Assistant"

Store labels only in Phase 4 derived tables (`semantic_clusters.canonical_label`). Never overwrite Phase 3 `theme` values.

**Acceptance criteria:**
- [ ] All meaningful emergent clusters (size ≥ `min_observations_for_theme`) have canonical labels
- [ ] Labels are problem/pattern oriented — not solution-oriented
- [ ] Labels are grounded in evidence packages, not unsupported abstraction
- [ ] Phase 3 `observations.theme` is NOT overwritten

---

### Task 4.7 — Root-Cause Hypothesis Synthesis

**Objective:** Synthesize root-cause hypotheses for each meaningful theme/cluster, grounded primarily in repeated Phase 3 evidence fields.

**File:** `backend/analysis/phase4_7_root_cause.py`

**Data reality:** Phase 3 `root_cause` is 6,345 empty + 789 "unknown" → do NOT treat as canonical truth. Non-empty Phase 3 `root_cause` values may be used only as weak secondary support.

**Primary evidence for synthesis (in order of reliability):**
1. `evidence_quote` (exact validated substring)
2. `uncertainty`
3. `information_needed`
4. `workaround`
5. `decision_outcome`
6. `primary_barrier`
7. `wishlist_intent` / `purchase_intent`
8. `journey_stage`
9. `external_platform_used`
10. `alternative_considered`

**Secondary support only:**
- Phase 3 `root_cause` (non-empty values)
- Phase 3 raw `theme`

**Evidence ladder (strict):**
- LEVEL 1 — Exact user evidence (Exact `evidence_quote`)
- LEVEL 2 — Observed / inferred behavior (Reasonable interpretation directly supported by evidence)
- LEVEL 3 — Possible root-cause hypothesis (Repeated-evidence hypothesis)
- LEVEL 4 — Possible unmet need (Separate derived layer)
- LEVEL 5 — Potential solution (NOT part of V1 Discovery Engine)

Root-cause hypotheses must be synthesized from REPEATED evidence — not isolated reviews. Use appropriate uncertainty language. Do not present causal hypotheses as experimentally proven causal facts. Every hypothesis must preserve supporting `observation_id` list and unique source count.

**LLM synthesis output (per cluster/theme):**
```json
{
  "what_happened": "...",
  "what_prevented_progress": "...",
  "why_barrier_existed": "...",
  "what_information_was_missing": "...",
  "what_user_did_instead": "...",
  "root_cause_summary": "...",
  "supporting_observation_ids": [...],
  "unique_source_support": N,
  "confidence_note": "..."
}
```

**Storage:** `root_cause_hypotheses` table with `analysis_run_id`.

**Acceptance criteria:**
- [ ] Root-cause synthesis runs for all clusters/themes with `unique_source_count ≥ min_observations_for_theme`
- [ ] `root_cause_summary` is non-empty and uncertainty language is appropriate
- [ ] Supporting observation IDs and unique source counts are preserved
- [ ] Phase 3 sparse `root_cause` strings are NOT treated as canonical input

---

### Task 4.8 — Unmet-Need Discovery

**Objective:** Identify and articulate explicit unmet needs as a separate derived layer — distinct from themes, root causes, and opportunities.

**File:** `backend/analysis/phase4_8_unmet_needs.py`

**Do NOT jump:** theme → opportunity. The unmet-need layer is the bridge.

**For each meaningful repeated pattern, determine:**
- What is the user trying to accomplish?
- What prevents progress?
- What uncertainty remains unresolved?
- What information/confidence is missing?
- What workaround is used?
- What decision consequence occurs (postponed/abandoned/switched)?
- Is this behavior repeated across independent source records?
- Is the need unresolved?
- Which shopper context/segment experiences it?

A valid unmet need requires repeated evidence across sufficient unique source records.

**Storage:**
```
unmet_needs:
  unmet_need_id
  analysis_run_id
  canonical_statement          -- problem/need phrased as user goal
  supporting_cluster_ids
  supporting_theme_ids
  supporting_observation_ids
  unique_source_support
  relevant_intents
  relevant_segments
  recurring_uncertainties
  recurring_workarounds
  decision_consequences
  evidence_strength            -- strong / moderate / weak
```

Statements must be problem/need oriented:
- ✅ GOOD: "High-intent shoppers need greater confidence about expected fit before committing to purchase."
- ❌ BAD: "Users need an AI size recommender."

**Acceptance criteria:**
- [ ] At least one unmet need identified per meaningful cluster/theme with sufficient evidence
- [ ] Each unmet need has `unique_source_support` populated
- [ ] Statements are problem-oriented, not solution-oriented
- [ ] `unmet_needs` table populated with `analysis_run_id`

---

### Task 4.9 — Opportunity Generation & Metric Relevance

**Objective:** Convert evidence-backed unmet needs into opportunity areas, each classified by metric relevance to the wishlist→purchase journey.

**File:** `backend/analysis/phase4_9_opportunity_gen.py`

**An opportunity is NOT automatically:** a large cluster, a frequent complaint, a theme, or an unmet need. It requires:
- Repeated evidence across sufficient unique source records
- Identifiable unmet need (from Task 4.8)
- Meaningful unique-source support
- Relevant shopper context
- Behavioral consequence (postponed/abandoned/switched/external research)
- Plausible relationship to wishlist→purchase behavior

**Metric-relevance classification (mandatory for every opportunity):**

| Class | Definition |
|---|---|
| **DIRECT** | Evidence directly concerning wishlist behavior, saving, consideration, comparison, purchase intent, hesitation, postponement, abandonment, decision confidence |
| **CONTEXTUAL** | Prior delivery/return/trust failures that plausibly affect future willingness; not direct wishlist evidence |
| **LOW/UNCLEAR** | Generic complaints without defensible relationship to wishlist→purchase journey |

Do NOT let generic post-purchase complaint volume (e.g., Play Store delivery complaints) automatically dominate opportunity generation.

**Opportunity description rules:**
- Must describe a USER PROBLEM OR UNMET NEED — never a product feature/solution
- Must be falsifiable and traceable to evidence
- Must NOT recommend interventions, discounts, or features

**Acceptance criteria:**
- [ ] At least one DIRECT or CONTEXTUAL metric-relevance opportunity generated
- [ ] Every opportunity has an explicit metric-relevance classification with supporting evidence
- [ ] Opportunity description is problem-oriented, not solution-oriented
- [ ] `opportunities` and `opportunity_evidence` tables populated

---

### Task 4.10 — Opportunity Quantification & Prioritization

**Objective:** Quantify, contextualize, and prioritize all candidate opportunities.

**File:** `backend/analysis/phase4_10_quantification.py`

**For every candidate opportunity, report:**

*Support:* unique supporting source records | supporting observation count | dataset-scoped percentage | highly_relevant vs somewhat_relevant support

*Context:* source distribution | primary barriers | wishlist/purchase intent distribution | journey-stage distribution | decision-outcome distribution | segments | product categories | workarounds | external-platform behavior

*Evidence:* representative exact `evidence_quote` values | supporting observation IDs | supporting cluster/theme IDs | root-cause hypothesis ref | unmet need ref

*Metric:* direct / contextual / low-unclear relevance class | evidence supporting that classification

**Dataset-scoped language (hard rule):**
- ❌ Never: "X% of Myntra users..."
- ✅ Always: "Within the analyzed public-conversation dataset, X% of source records..."
- Always distinguish `observation_count` from `unique_source_record_count`
- Use unique source records for prevalence-like claims

**Prioritization — do NOT rank by cluster size alone.** Evaluate visible dimensions:
- Evidence support (unique-source recurrence)
- Direct metric relevance
- Decision consequence (abandon/postpone rate)
- Purchase-intent concentration
- Evidence diversity (source diversity — control Play Store volume dominance)
- Workaround intensity (proxy for unmet need strength)
- Unresolved-need strength

If using a composite score: document formula, weights, and component scores. Do not hide ranking logic.

**Source-volume control:** Play Store has ~61.7% of the data. Do not allow raw Play Store volume alone to elevate a problem over smaller-source but stronger/more-diverse evidence.

**Acceptance criteria:**
- [ ] All quantification is dataset-scoped (no population extrapolation)
- [ ] Both observation count and unique source count reported per opportunity
- [ ] Prioritization logic is documented, not hidden
- [ ] Play Store volume dominance has been explicitly checked and controlled
- [ ] `opportunity_evidence` table populated with exact quote provenance

---

### Task 4.11 — Phase 4 Evaluation

**Objective:** Evaluate each analytical layer independently. Phase 4 findings are NOT accepted merely because code ran successfully.

**File:** `data/phase4/phase4_evaluation_report.json`

**A. Representation/Clustering:**
- Direct HDBSCAN vs UMAP→HDBSCAN comparison summary
- Semantic coherence (manual sample review results)
- Cluster separation, stability, noise behavior
- Interpretability and evidence traceability

**B. Predefined Semantic Mapping:**
- Stratified validation results (correct / incorrect / missed / forced assignments)
- Threshold calibration evidence
- Multi-theme and unassigned counts

**C. Emergent Cluster Quality:**
- Cluster coherence (manual review)
- Overlap between clusters
- Stability under parameter variation
- Noise percentage
- Duplicate-concept check
- Over-broad / over-narrow assessment

**D. Representative Evidence:**
- Quote relevance and semantic centrality
- Diversity (sub-pattern + source diversity)
- No duplicates
- Exact Phase 3 quote provenance verified

**E. Cluster Labels:**
- Problem/pattern-oriented language check
- No unsupported abstraction
- No solution language
- Evidence grounding verified

**F. Root-Cause Hypotheses:**
- Evidence traceability check
- Repeated support verified
- Symptom vs root-cause distinction
- No unsupported causal certainty

**G. Unmet Needs:**
- Repeated evidence verified
- Identifiable user goal and unresolved friction
- Not phrased as solution
- Decision relevance where claimed

**H. Opportunities:**
- Problem (not feature) oriented
- Underlying unmet need linked
- Metric relevance classification verified
- Generic complaint volume dominance checked
- Supporting behavior/consequence present

**Acceptance criteria:**
- [ ] All 8 evaluation layers (A–H) have documented results
- [ ] No unsupported finding is advanced to Phase 4 outputs
- [ ] Provenance/integrity status: PASS

---

### Task 4.12 — Final Phase 4 Evidence/Opportunity Store

**Objective:** Persist all Phase 4 derived outputs as versioned, inspectable artifacts. Do NOT mutate Phase 3 observations.

**File:** `backend/analysis/phase4_12_persist.py`

**Required outputs:**
- `data/phase4/analysis_run_metadata.json`
- `data/phase4/predefined_themes.jsonl`
- `data/phase4/theme_assignments.jsonl`
- `data/phase4/semantic_clusters.jsonl`
- `data/phase4/cluster_memberships.jsonl`
- `data/phase4/cluster_representatives.jsonl`
- `data/phase4/segment_stats.jsonl`
- `data/phase4/root_cause_hypotheses.jsonl`
- `data/phase4/unmet_needs.jsonl`
- `data/phase4/opportunities.jsonl`
- `data/phase4/opportunity_evidence.jsonl`
- `data/phase4/phase4_evaluation_report.json`
- `data/phase4/task_4_1_representation_eval.json`

All derived tables also persisted to `discovery_pulse.db` with `analysis_run_id` versioning.

**Acceptance criteria:**
- [ ] All JSONL/JSON artifacts written to `data/phase4/`
- [ ] All derived DB tables populated with `analysis_run_id`
- [ ] Phase 3 `observations` table row count remains 9,171
- [ ] Phase 3 `observations.theme` and `observations.root_cause` are unchanged
- [ ] All artifacts are inspectable without re-running scripts

---

### Phase 4 Completion Gate

Phase 4 is COMPLETE only when ALL applicable conditions pass:

1. - [ ] 9,171 canonical Phase 3 observations remain unchanged
2. - [ ] Existing MiniLM observation embeddings evaluated as baseline semantic representation
3. - [ ] Direct HDBSCAN vs UMAP→HDBSCAN compared empirically and documented
4. - [ ] Selected clustering configuration is documented and versioned
5. - [ ] HDBSCAN noise remains valid and is not force-assigned
6. - [ ] Predefined themes use semantic cosine similarity — NOT Phase 3 theme-string matching
7. - [ ] Predefined mapping threshold empirically calibrated and versioned
8. - [ ] Emergent clustering runs across the full 9,171-observation corpus
9. - [ ] Observations may be predefined, emergent, both, or neither
10. - [ ] Theme/cluster statistics retain BOTH observation count and unique-source count
11. - [ ] Representative evidence is exact, verbatim, and traceable to Phase 3 observation IDs
12. - [ ] Behavioral segment analysis complete for meaningful segments
13. - [ ] Meaningful emergent clusters have evidence-grounded canonical labels (problem/pattern language)
14. - [ ] Root-cause hypotheses based primarily on repeated Phase 3 evidence fields
15. - [ ] Sparse Phase 3 `root_cause` values NOT treated as canonical truth
16. - [ ] Unmet needs explicitly separated from theme, root cause, opportunity, and solution
17. - [ ] Opportunities are evidence-backed and problem-oriented
18. - [ ] Direct vs contextual vs low/unclear metric relevance is explicit per opportunity
19. - [ ] Quantification uses unique source records for prevalence-like claims
20. - [ ] All claims remain scoped to the analyzed dataset
21. - [ ] Play Store source-volume dominance has been checked and controlled
22. - [ ] Phase 4 evaluation (all 8 layers) passes
23. - [ ] Phase 3 canonical data remains untouched

---

## Phase 5 — Presentation Layer

**Goal:** Build the three user-facing interfaces — Discovery Pulse Dashboard, Evidence Explorer, and Grounded Query Interface — backed by a FastAPI backend that serves the Phase 4 derived analysis layer alongside the Phase 3 observation corpus.

**Phase 4 Foundation (data contract for Phase 5):**

- Canonical observations: **9,171** (from 9,165 unique source records)
- Predefined themes: **10** (mapped via semantic similarity in `theme_assignments`)
- Emergent clusters: **37** meaningful + 1 noise group (in `semantic_clusters` / `cluster_memberships`)
- Cluster synthesis: **37** records with `canonical_name`, `description`, `primary_root_cause`, `primary_unmet_need`
- Final opportunities: **3** (in `phase4_opportunity_areas` / `opportunity_evidence`)
- Unmet needs: **8** (in `unmet_need_context`)
- Knowledge graph: `data/phase4/knowledge_graph.json` (Default knowledge graph: OPPORTUNITY → UNMET NEED → ROOT CAUSE → CLUSTER / THEME. Do NOT render all 9,171 observations as graph nodes. Representative evidence may be loaded on interaction. Full evidence belongs in Evidence Explorer.)
- Representative quotes: `cluster_representatives` table (per-cluster evidence with provenance)
- Metric relevance per opportunity: DIRECT / CONTEXTUAL / LOW-UNCLEAR
- Authoritative denominator: **9,165** successfully processed source records

*Note: The values above (9,171 observations, 10 predefined themes, 37 emergent clusters, 8 unmet needs, 3 final opportunities) represent the current analysis snapshot. Dashboard statistics, dataset-scope banners, source distributions, analysis metadata, and related counts must come dynamically from the backend and the current accepted analysis run. Phase 5 frontend business logic must NOT hardcode them.*

**Source distribution (Analyzed Evidence Corpus):**
- To be computed dynamically from the 9,165 successfully processed source records.
- Maintain the distinction between RAW INGESTION SOURCE DISTRIBUTION (methodology/provenance metadata, not to be used as opportunity-support denominators) and ANALYZED EVIDENCE SOURCE DISTRIBUTION. The Dashboard should use analyzed evidence distribution by default.
- (Raw Phase 1 ingestion distribution: Play Store 44,401; YouTube 26,946; App Store 500; Reddit 116 — show separately as methodology metadata).

---

### Task 5.1 — FastAPI Backend (REST API)

**Objective:** Implement all API endpoints required by the three frontend interfaces. Endpoints must serve data from both Phase 3 tables (`observations`, `raw_records`, `cleaned_records`, `classified_records`) and Phase 4 derived tables (`semantic_clusters`, `cluster_memberships`, `cluster_synthesis`, `theme_assignments`, `predefined_themes`, `phase4_opportunity_areas`, `opportunity_evidence`, `unmet_need_context`, `cluster_aggregations`, `cluster_representatives`, `analysis_runs`).

**File:** `backend/api/main.py` + `backend/api/routers/`

**Endpoints:**

```
GET  /api/health                         → system health check (DB reachable, Chroma reachable)

GET  /api/pipeline/runs                  → list pipeline_runs rows
GET  /api/pipeline/runs/{run_id}         → pipeline run detail + stats

# ── Dashboard endpoints (deterministic DB queries, no LLM) ────────────
GET  /api/dashboard/stats                → dataset overview:
                                            total_raw_records, relevant_records (9,749),
                                            processed_source_records (9,165),
                                            canonical_observations (9,171),
                                            source_distribution (analyzed vs raw), date_range,
                                            analysis_run metadata
GET  /api/dashboard/themes               → predefined themes (10) with observation_count,
                                            unique_source_count, mapping_rate (43.9%)
GET  /api/dashboard/clusters             → emergent clusters (37) with canonical_label,
                                            observation_count, unique_source_count
GET  /api/dashboard/opportunities        → 3 opportunity areas with:
                                            problem-oriented title, metric_relevance,
                                            unique_source_count, dataset_percentage,
                                            denominator (9,165), supporting_unmet_needs,
                                            representative_quotes
GET  /api/dashboard/barriers             → primary_barrier distribution across observations
GET  /api/dashboard/wishlist-motivations → wishlist_intent distribution
GET  /api/dashboard/purchase-intents     → purchase_intent distribution
GET  /api/dashboard/uncertainties        → top recurring uncertainty values
GET  /api/dashboard/information-needs    → top recurring information_needed values
GET  /api/dashboard/workarounds          → top recurring workaround values
GET  /api/dashboard/segments             → segment_signal distribution
GET  /api/dashboard/journey-stages       → journey_stage distribution
GET  /api/dashboard/decision-outcomes    → decision_outcome distribution

# ── Evidence endpoints ────────────────────────────────────────────────
GET  /api/evidence                       → paginated, filterable observations list
GET  /api/evidence/{observation_id}      → single observation with all fields +
                                            Phase 4 assignments (theme, cluster, opportunity)
GET  /api/evidence/export                → CSV or JSON export of filtered observations (downstream-safe data only)

# ── Phase 4 derived entity endpoints ──────────────────────────────────
GET  /api/themes                         → predefined_themes list with prototypes
GET  /api/themes/{theme_id}              → theme detail with supporting observations
                                            (via theme_assignments)
GET  /api/clusters                       → semantic_clusters list
GET  /api/clusters/{cluster_id}          → cluster detail: synthesis, aggregation stats,
                                            representative quotes, cluster members
GET  /api/opportunities                  → phase4_opportunity_areas list
GET  /api/opportunities/{opportunity_id} → opportunity detail: evidence hierarchy
                                            (opportunities → unmet needs → root causes → clusters → evidence),
                                            supporting observation IDs, representative quotes,
                                            metric relevance, source distribution
GET  /api/knowledge-graph                → knowledge_graph.json for visualization (bounded, lean)
GET  /api/unmet-needs                    → unmet_need_context list

# ── Query endpoint ────────────────────────────────────────────────────
POST /api/query                          → submit natural language query, returning: answer, query_type, retrieval_mode, applied_filters, evidence_count, unique_source_count, dataset_scope_caveat, evidence[] (safe traceable fields: observation_id, source_record_id, evidence_quote, source, source_url, relevant theme/cluster context). For numeric queries, return numerator, denominator, denominator_definition, denominator_scope.
# GET  /api/query/history                  → Do not add backend persistence merely to satisfy endpoint list. For V1 use client-side localStorage.

# ── Filter metadata ───────────────────────────────────────────────────
GET  /api/meta/filter-options            → Return valid filter options from the canonical DB/configuration. Invalid filters return HTTP 400.

# ── Pipeline trigger ──────────────────────────────────────────────────
POST /api/pipeline/run                   → trigger pipeline run (protected, if already part of approved architecture. Do not expand Phase 5 into pipeline orchestration/scheduling work.)
```

**Shared filter parameters** (applied to `/api/evidence` and `/api/dashboard/*`).
*Note: Frontend filter controls should consume `GET /api/meta/filter-options` rather than maintain independent hardcoded option lists. Valid canonical `unknown` values remain valid where supported. Invalid filter values must return HTTP 400:*
```
?source=play_store,reddit,youtube,app_store
?wishlist_intent=genuine_purchase,comparison_shortlist,inspiration,price_tracking,occasion_planning,aspirational_saving,bookmarking,unknown
?purchase_intent=high,medium,low,none,unknown
?primary_barrier=fit,quality,price,trust,delivery,unknown
?predefined_theme=fit_and_sizing_uncertainty,review_trust_gap,...
?cluster_id=cluster_012,cluster_023,...
?segment_signal=...
?evidence_type=myntra_specific,category_level
?journey_stage=discovery,research,evaluation,purchase,post_purchase,unknown
?decision_outcome=bought,postponed,abandoned,switched,delayed,unknown
?published_after=2026-01-01
?published_before=2026-08-01
?relevance_label=highly_relevant,somewhat_relevant
```

**Dataset scope rules (enforced in all API responses):**
- All percentage values must explicitly expose: `numerator`, `denominator`, `denominator_definition`, `denominator_scope`, and `active_filters`.
- `denominator_scope = "global"` when referring to the accepted analysis-run population (e.g., the 9,165 source records).
- `denominator_scope = "filtered"` only for intentionally filtered statistics.
- When filters are active, clearly distinguish GLOBAL SUPPORT from FILTERED MATCHING EVIDENCE. Do not silently replace the accepted global opportunity percentage with a filtered percentage.
- Never silently change denominator semantics. Keep all wording dataset-scoped rather than population-generalized.
- Never return language like "X% of Myntra users"
- Always scope to "Within the analyzed public-conversation dataset"

**Acceptance criteria:**
- [ ] All GET endpoints return correctly structured JSON with appropriate HTTP status codes
- [ ] Filter parameters correctly reduce response sets
- [ ] Pagination works on `/api/evidence` (default page size: 20)
- [ ] `/api/health` returns 200 even if analysis has not been run yet
- [ ] `/api/opportunities/{id}` returns the full evidence hierarchy (clusters → root causes → unmet needs → opportunity)
- [ ] All percentage responses include explicit denominator

---

### Task 5.2 — Grounded Query Engine

**Objective:** Implement the retrieval + synthesis pipeline that powers the Query Interface, using the existing ChromaDB `observation_embeddings` and `evidence_quote_embeddings` collections.

**Files:**

- `backend/query/intent_parser.py` — extract research intent and implied filters from a natural-language question
- `backend/query/filter_builder.py` — translate implied filters to SQLAlchemy WHERE clauses against `observations` + Phase 4 derived tables
- `backend/query/retriever.py` — structured DB query → ChromaDB semantic re-ranking within the filtered set (using `all-MiniLM-L6-v2` embeddings)
- `backend/query/synthesizer.py` — LLM grounded synthesis with evidence ladder

**Retrieval routing logic:**
1. **QUERY TYPE 1 — Deterministic Count / Filter Question**
   - Examples: "How many observations mention fit?", "What percentage of evidence is classified as price?"
   - Logic: Use deterministic SQL / Phase 4 aggregates directly. DO NOT call the synthesis LLM merely to calculate a known count.
   - Return: answer, numerator, denominator (where relevant), applied filters, provenance.
2. **QUERY TYPE 2 — Evidence / Explanatory Question**
   - Examples: "Why are shoppers uncertain about fit?", "What workarounds do users use?"
   - Logic: Intent parsing → structured filters → construct eligible observation-ID subset → semantic retrieval/reranking WITHIN that eligible subset → evidence package → grounded synthesis → output validation.
   - Guardrail: Do NOT retrieve globally and filter afterward. Structured constraints must come first.

**ChromaDB integration (for Type 2 Queries):**
- Use existing `observation_embeddings` collection (9,171 vectors, 384-dim, `all-MiniLM-L6-v2`)
- Embed user question with the same `all-MiniLM-L6-v2` model locally
- Retrieve top-K candidates (configurable, default K=20) from the *already filtered* subset, then re-rank
- Return verbatim `evidence_quote` values — never paraphrase

**Synthesis prompt guardrails & UX:**
- "Answer ONLY from the provided observations. Do not use external knowledge."
- Keep the interface solution-free. The system stops at OPPORTUNITY AREA. Do not automatically generate product solutions (e.g. "AI size recommender"). If asked "What feature should Myntra build?", explain the system's role.
- Explicitly label each evidence item: 📌 What users said / 🔍 Observed / inferred behavior / 💡 Possible unmet need / evidence-backed insight. (No solution layer/icon).
- Never fabricate quotes, counts, or percentages.
- LLM synthesis must NEVER generate numeric counts from prose; counts must come from deterministic DB computation.
- Do not send restricted `raw_text` to the synthesis model.

**Final query output validation:**
- Before returning the response, validate: every displayed quote resolves to canonical evidence_quote, numeric claims match deterministic values, raw_text is absent, restricted/private engineering fields are absent, provenance IDs resolve, dataset-scope caveat is present, and no unsupported product-solution content is presented. Fail safely if validation does not pass.

**Empty / Exploratory query handling:**
- **Empty Retrieval:** If a recognized explicit filter produces zero evidence, return an honest no-evidence result. (e.g., source=reddit + fit query + zero matches must NOT silently search other sources). Do not use semantic-only fallback simply to avoid an empty result.
- **Semantic Fallback:** If semantic_only is used: expose `retrieval_mode="semantic_only"`, caveat it explicitly, preserve exact evidence quotes, and do not claim structured-filter support existed.

**Task 5.2.1 — Query Retrieval Evaluation (REQUIRED GATE)**
- Create a benchmark of 15–20 representative PM questions covering: wishlist motivation, high purchase intent, fit/sizing, price trust, delivery/returns, comparison behavior, external research, predefined themes, emergent clusters, source filters, no-result cases, and ambiguous exploratory questions.
- For each, manually evaluate: structured filter correctness, top-K relevance, quote faithfulness, answer faithfulness, count accuracy, unsupported claims, empty-result behavior, provenance correctness.

**Acceptance criteria:**
- [ ] "Why do users add products to wishlists?" returns a grounded answer with evidence quotes and source references
- [ ] "What prevents high-intent users from purchasing?" returns observations filtered by `purchase_intent=high`
- [ ] "What are the main sizing issues?" returns observations from the fit_and_sizing_uncertainty theme/clusters
- [ ] A fabricated quote is never present in any response (tested by checking all quotes against the `observations.evidence_quote` column)
- [ ] Every response includes at least one dataset-scope caveat
- [ ] Query embedding uses the same `all-MiniLM-L6-v2` model as Phase 3
- [ ] Query benchmark passes on 15–20 representative PM questions
- [ ] Query engine correctly routes deterministic count/filter questions without unnecessary LLM calls
- [ ] Empty retrieval produces an honest empty-evidence response

---

### Task 5.3 — Discovery Pulse Dashboard (Frontend)

**Objective:** Build the Discovery Pulse Dashboard as a Next.js page consuming the backend API. The dashboard must present Phase 4 findings with full evidence traceability and dataset-scoped language.

**File:** `frontend/app/dashboard/page.tsx` + components in `frontend/components/`

**Components to build:**

| Component | Data Source | Chart Type | Notes |
|---|---|---|---|
| Dataset Stats Card | `/api/dashboard/stats` | Numbers with labels | Show: 9,165 processed sources, 9,171 observations, 4 source channels |
| Source Distribution | `/api/dashboard/stats` | Donut chart | Play Store / YouTube / App Store / Reddit with counts |
| Analysis Run Info | `/api/dashboard/stats` | Badge / metadata | Analysis run ID, timestamp, clustering config |
| **Opportunity Areas** | `/api/dashboard/opportunities` | Card list (top section) | 3 opportunities with problem-oriented titles, metric relevance badges (DIRECT/CONTEXTUAL), unique source count, dataset %, representative quotes |
| Predefined Themes | `/api/dashboard/themes` | Card grid with bars | 10 themes, mapping rate, observation count |
| Emergent Clusters | `/api/dashboard/clusters` | Sortable table or card grid | 37 clusters with canonical labels, observation/source counts |
| Data Journey / Evidence Pipeline | Pipeline metadata | Funnel, pipeline, or connected cards | Visual explanation of how evidence was built (collected → cleaned → filtered → classified → extracted → analyzed). |
| Knowledge Graph | `/api/knowledge-graph` | Interactive network diagram | OPPORTUNITY → UNMET NEED → ROOT CAUSE → CLUSTER / THEME hierarchy |
| Purchase Barriers | `/api/dashboard/barriers` | Horizontal bar | Distribution across all observations |
| Wishlist Motivations | `/api/dashboard/wishlist-motivations` | Horizontal bar | Distribution of wishlist_intent |
| Purchase Intent | `/api/dashboard/purchase-intents` | Horizontal bar | Distribution of purchase_intent |
| User Uncertainties | `/api/dashboard/uncertainties` | Tag cloud or ranked list | Top recurring uncertainty values |
| Information Needs | `/api/dashboard/information-needs` | Ranked list | Top recurring information_needed values |
| Workarounds | `/api/dashboard/workarounds` | Ranked list | Top recurring workaround values |
| Behavioral Segments | `/api/dashboard/segments` | Card grid | Segment distribution (note: 6,723 empty + 1,902 unknown) |
| Journey Stages | `/api/dashboard/journey-stages` | Horizontal bar | Journey-stage distribution |
| Decision Outcomes | `/api/dashboard/decision-outcomes` | Horizontal bar | purchased/postponed/abandoned/switched |
| Representative Quotes | Embedded in opportunity/theme/cluster cards | Quote carousel | Exact Phase 3 `evidence_quote` values with source provenance |

**Data Journey / Evidence Pipeline Visual:**
Include a clear visual explaining how the final analyzed evidence corpus was produced from the original public conversation collection to improve transparency and traceability. Place this lower in the Dashboard under a heading such as "How this evidence was built" or "Data journey".
- *Semantic rules:* Do NOT present this as "71,963 users → 9,171 users". These are records/observations, not unique users. The visual must communicate a data-processing lineage (COLLECTED → CLEANED → PRE-FILTERED → CLASSIFIED RELEVANT → EXTRACTED → ANALYZED). Do not imply records were arbitrarily discarded. Add a tooltip explaining why 9,171 observations > 9,165 source records ("A source record may produce more than one valid canonical observation").
- *Corpus distinction:* Keep the RAW INGESTION CORPUS (71,963 records) distinct from the ANALYZED EVIDENCE CORPUS (used for downstream analysis). Do not use the raw 71,963 records as the denominator for opportunity support.
- *Visual design intent:* May be implemented as a responsive funnel, horizontal/vertical pipeline, stepped flow, or connected cards. Show the four source channels feeding into the pipeline. Must be responsive (desktop, tablet, mobile), preferring a vertically stacked pipeline on smaller screens instead of forcing a wide horizontal diagram. No horizontal page overflow.
- *Runtime Data:* While the snapshot counts (71,963 raw, 44,401 Play Store, etc.) may be documented here, do NOT require the frontend to hardcode them. Obtain stage counts from backend/pipeline metadata or the current accepted run where practical. If historical Phase 1/2 counts are not exposed, document them as current analysis metadata rather than over-engineering a new backend subsystem just for this visual.

**Opportunity card design:**
Each opportunity card must show:
- Problem-oriented title (e.g., "High-intent shoppers experience fit uncertainty...") (use the evidence-corrected Phase 4 versions, NOT older solution-oriented names)
- Metric relevance badge: `DIRECT` (green) / `CONTEXTUAL` (amber) / `LOW-UNCLEAR` (grey)
- Unique source support count and dataset-scoped percentage
- Explicit denominator label: "of 9,165 processed source records"
- Supporting unmet needs (collapsed list)
- 3–5 representative exact evidence quotes with source attribution
- Click-through to opportunity detail page

**Dashboard Information Hierarchy:**
Do NOT treat all dashboard components as equally important. Prioritize:
1. Dataset / Analysis Context
2. Final Opportunity Areas
3. Key Patterns (predefined themes, meaningful emergent clusters)
4. Behavior / Decision Signals (barriers, wishlist intent, purchase intent, etc.)
5. Segments
6. Data Journey / Methodology / Knowledge Graph / Run Metadata

The Data Journey should strengthen trust and explain provenance, but should not push the opportunity areas out of the primary visual hierarchy. Avoid turning the Dashboard into a wall of charts.

**Filter panel:** Sidebar or top-bar with all filter parameters from Task 5.1. Selecting a filter re-fetches all dashboard components. Filter options populated dynamically from actual canonical data values.

**Dataset scope caveat:** A persistent banner states: *"All figures refer to the analyzed public-conversation dataset of 9,171 observations from 9,165 source records across Play Store, App Store, Reddit, and YouTube. These findings should not be generalized to all Myntra users."*

**Acceptance criteria:**
- [ ] Dashboard renders without errors when data exists
- [ ] Dashboard shows an empty-state message (not an error) when no analysis run exists
- [ ] Filters correctly update all charts simultaneously
- [ ] All chart values match the raw API responses exactly (no rounding or fabrication)
- [ ] Dataset scope caveat is visible on every page load
- [ ] Opportunity cards display problem-oriented titles and metric relevance badges
- [ ] Representative quotes are exact `evidence_quote` values from Phase 3
- [ ] Knowledge graph renders the opportunity → unmet need → cluster hierarchy
- [ ] Dashboard includes a Data Journey / "How this evidence was built" section
- [ ] All four collection sources are represented with current snapshot counts
- [ ] Pipeline stages reconcile with accepted Phase 1–4 counts
- [ ] Raw records, source records, and observations are correctly labeled (not as unique users)
- [ ] Data journey visual is responsive and avoids horizontal page overflow

---

### Task 5.4 — Evidence Explorer (Frontend)

**Objective:** Build the Evidence Explorer as a paginated, filterable interface for observations with Phase 4 derived metadata.

**File:** `frontend/app/evidence/page.tsx`

**Features:**
- Paginated table (20 rows/page). Total result count and pagination must come from runtime API data, not a frontend-hardcoded 9,171.
- Columns:
  - `observation_id` (truncated UUID)
  - `source` (Play Store / App Store / Reddit / YouTube)
  - `evidence_quote` (truncated; click to expand)
  - `primary_barrier`
  - `wishlist_intent`
  - `purchase_intent`
  - `journey_stage`
  - `decision_outcome`
  - `uncertainty` (truncated)
  - Predefined theme assignment(s) (from `theme_assignments`)
  - Emergent cluster membership (from `cluster_memberships`)
- Evidence quote shown truncated; click to expand full observation detail in a slide-over panel visually separating PHASE 3 — CANONICAL EVIDENCE from PHASE 4 — DERIVED ANALYSIS.
  - Phase 3 shows: All approved downstream-safe Phase 3 canonical observation fields. Explicitly exclude raw_text, restricted/private engineering fields, internal-only identifiers not approved for downstream display.
  - Phase 4 shows: Theme, cluster, similarity and opportunity metadata (must never appear as though it was part of the user's original statement). Similarity scores are assignment/matching scores, not probabilities of truth.
  - AI confidence shown only inside Evidence Detail as secondary technical metadata explicitly labelled: "AI extraction confidence — uncalibrated" (do not use truth-like colours, default sorting, evidence-strength semantics, or calibrated-probability language).
  - Source URL (clickable external link)
  - `source_record_id` for provenance
  - Every displayed evidence quote must resolve exactly to the canonical observations.evidence_quote value.
- Full-text search within `evidence_quote` that applies to the complete eligible evidence corpus through the backend/API (not only the currently loaded 20-row page). Keep debounced search, minimum 3 characters.
- All Evidence Explorer filter controls must consume canonical values from `GET /api/meta/filter-options`. Do not maintain independent hardcoded frontend taxonomies.
- Evidence Explorer filter/search state must be deep-linkable, preferably through URL query parameters (to allow Dashboard, Opportunity Detail, and theme/cluster investigation links to open Evidence Explorer with relevant filters already applied). Do not invent analytical relationships just to support navigation.
- Explicit UI states for: loading, API error, empty dataset, no search results, invalid filter response (surfaced from HTTP 400), and export failure where applicable.
- Responsiveness: Must remain usable on desktop, laptop, tablet, and mobile where reasonable. Desktop may use a research table. On smaller screens: adapt to responsive cards or another readable layout, keep filters usable, keep evidence_quote readable, avoid unintended horizontal page overflow, preserve access to Evidence Detail.
- Export: Support safe CSV and JSON export for the active filtered result set. Exports may include approved canonical observation fields + Phase 4 assignments. Never include raw_text or engineering-only fields.

**Acceptance criteria:**
- [ ] Total result count and pagination come from runtime API data, not a frontend-hardcoded 9,171
- [ ] Search operates across the full eligible evidence corpus, not only the current page
- [ ] Filter options come from /api/meta/filter-options
- [ ] Invalid filters are handled clearly
- [ ] Filter/search state is deep-linkable
- [ ] Every displayed quote exactly matches canonical evidence_quote
- [ ] Evidence Detail exposes only approved downstream-safe canonical fields
- [ ] raw_text is absent from UI/API/export
- [ ] Phase 3 canonical and Phase 4 derived sections are visually distinct
- [ ] Similarity scores are not presented as truth probabilities
- [ ] AI confidence remains secondary and explicitly uncalibrated
- [ ] CSV export works for the active filter set
- [ ] JSON export works for the active filter set
- [ ] Loading/error/empty/no-results states work
- [ ] Evidence Explorer is usable responsively without unintended page overflow

---

### Task 5.5 — Grounded Query Interface (Frontend)

**Objective:** Build the Grounded Query Interface for natural-language evidence investigation consuming the existing `POST /api/query` response.

**File:** `frontend/app/query/page.tsx`

**Features & Requirements:**
- **Query Input & History:**
  - Text input with "Ask" button (Enter to submit).
  - Query history panel (last 10 queries, clickable to re-load; client-side localStorage only).
  - Empty or very short queries show an inline validation message rather than calling the API.
  - Usable suggested starter-question chips (derived from Phase 4 findings).
- **Query Response Contract (No Frontend Calculation):**
  - The frontend must consume and display values directly from the backend. It must not calculate or invent values itself.
  - Display where applicable: answer, `query_type`, `retrieval_mode`, applied filters, `evidence_count`, `unique_source_count`, dataset scope caveat, and supporting evidence list.
- **Deterministic Query UX:**
  - Support deterministic research questions (e.g., "What are the top themes?", "How many observations mention fit?", "What percentage of the evidence has price as the primary barrier?").
  - Deterministic answers must clearly present backend-computed values (e.g., numerator, denominator, denominator_definition, denominator_scope).
  - Do not make LLM-generated prose appear to be the source of counts/rankings.
- **Explanatory Query UX:**
  - For evidence/explanatory questions, preserve the pipeline: structured filters → eligible evidence subset → semantic retrieval → grounded synthesis.
  - Show retrieval mode, applied filters, evidence count, unique source count, and supporting evidence so a PM/evaluator can understand how the answer was produced.
- **Empty / No-Evidence State:**
  - Add explicit handling for: "No supporting evidence was found for the current filters."
  - Do not present an empty retrieval as an application error.
  - If `retrieval_mode="semantic_only"`, clearly indicate that mode and show the associated caveat.
  - Explicit filters must never appear to have been silently relaxed.
- **Provider / Query Failure State:**
  - The Query Interface must fail gracefully if the synthesis provider is temporarily unavailable or rate-limited.
  - Show a clear user-facing error state rather than crashing the page (no provider/fallback architecture changes in this task).
- **Evidence Traceability:**
  - Collapsible evidence cards must show: observation_id, source_record_id, exact canonical evidence_quote, source, source_url where available, and relevant theme/cluster context where supplied by the API.
  - Where useful, evidence should link/open the Evidence Explorer using the existing deep-linkable state.
  - Do not invent relationships in the frontend.
- **Solution-Free Behavior:**
  - Explicitly include the case: "What feature should Myntra build?"
  - Preserve the verified V1 behavior: do not generate a product solution as an evidence-backed finding.
  - Explain that the Discovery Engine surfaces evidence, patterns, root-cause hypotheses, unmet needs and opportunity areas.
  - Use only: 📌 What users said, 🔍 Observed / inferred behavior, 💡 Possible unmet need / evidence-backed insight.
  - No solution layer.
- **Safety:**
  - No `raw_text` in UI.
  - No engineering-only/private fields.
  - Displayed quotes must come exclusively from canonical `evidence_quote`.
  - Numeric values must come from deterministic backend fields.
  - Dataset-scope caveat remains visible.
- **Responsiveness:**
  - Require the Query Interface to remain usable on: desktop, laptop, tablet, mobile.
  - Ensure readable answer content, readable evidence cards, usable starter-question chips, usable query input, collapsible evidence remains accessible, and no unintended horizontal page overflow.

**Acceptance criteria:**
- [ ] Deterministic count/ranking/percentage queries display backend-computed values
- [ ] query_type and retrieval_mode are correctly represented
- [ ] applied filters are visible
- [ ] evidence_count and unique_source_count are shown where applicable
- [ ] numeric responses preserve numerator/denominator semantics
- [ ] explanatory responses show inspectable canonical evidence
- [ ] every displayed quote matches canonical evidence_quote
- [ ] evidence can navigate to Evidence Explorer where appropriate
- [ ] empty retrieval shows an honest no-evidence state
- [ ] semantic_only mode is explicitly identified and caveated
- [ ] solution-seeking questions preserve the V1 solution-free boundary
- [ ] no raw_text is exposed
- [ ] provider/rate-limit failures show a graceful error state
- [ ] loading/error/empty states work
- [ ] query history remains client-side localStorage only
- [ ] Query Interface is responsive without unintended page overflow

---

### Task 5.6 — Opportunity Detail View (Frontend)

**Objective:** Build a dedicated opportunity detail page that shows the full evidence hierarchy, driven dynamically by existing Phase 5 backend APIs and runtime data. Do not hardcode opportunity content or observations in the frontend.

**File:** `frontend/app/dashboard/opportunities/[opportunity_id]/page.tsx`

**Features & Requirements:**

- **Approved Opportunity Presentation:**
  - Display the final evidence-corrected problem statement as the main page title/statement.
  - Old solution-oriented labels (if present in API) may only appear as internal metadata, not as user-facing primary titles.
- **Dataset-Scoped Quantification:**
  - Display all supplied statistics: numerator, denominator, denominator_definition, denominator_scope, dataset percentage, unique source count, and global support.
  - Dataset percentages must not be generalized to Myntra's full user population (e.g., do not say "X% of Myntra users...").
- **Metric Relevance Boundary:**
  - Display the metric relevance classification (DIRECT, CONTEXTUAL, or LOW-UNCLEAR) with its explanation.
  - Make it clear that CONTEXTUAL or LOW-UNCLEAR evidence does not prove causal impact on wishlist-to-purchase conversion.
- **Evidence Hierarchy & Derived vs. Canonical Distinction:**
  - Preserve and visually distinguish the Phase 4 derived analysis (Opportunity → Unmet Need → Root Cause → Cluster/Theme) from Phase 3 canonical evidence.
  - Hierarchy must be top-down traceable to canonical evidence. Do not invent missing analytical relationships in the frontend.
- **Representative Quotes:**
  - Display 3–5 strongly relevant representative quotes where available.
  - Quotes must be exact `evidence_quote` values (no paraphrasing).
  - Include provenance for trust: `observation_id`, `source_record_id` (if available), `source`, `source_url` (if available), and a deep link to the Evidence Explorer.
- **Full Supporting Evidence:**
  - The full list of supporting observation IDs must be collapsible, lazy-loaded, or paginated to avoid rendering thousands of items by default.
  - Provide a "View all supporting evidence" link to `/evidence?opportunity_id=...`.
- **Source Distribution:**
  - Show opportunity-specific source distribution (Play Store, YouTube, App Store, Reddit).
  - If Play Store > 80%, show a clear dominance caveat (do not treat source volume dominance as user-population dominance).
- **No Solutions:**
  - The page must stop at quantified support and metric relevance.
  - Do not show product solutions, feature ideas, MVP concepts, or recommendations.
- **Navigation:**
  - Link back to Dashboard.
  - Link representative quotes and full evidence sets to Evidence Explorer.
  - Link to specific themes/clusters where routes exist.
- **States & Responsiveness:**
  - Explicitly handle loading, API error, opportunity not found / invalid id, missing optional relationship data, empty supporting evidence, and export/link failure states.
  - Must remain usable across desktop, laptop, tablet, and mobile (readable hierarchy/quotes, no horizontal overflow).

**Acceptance criteria:**
- [ ] All opportunity detail pages are API-driven, not frontend-hardcoded
- [ ] Final evidence-corrected problem statement is the primary title/statement
- [ ] Old solution-like labels are not user-facing primary titles
- [ ] Metric relevance explanation is displayed without implying causal proof
- [ ] Numerator, denominator, denominator_definition and denominator_scope are preserved
- [ ] Dataset percentages are not generalized to Myntra's full user population
- [ ] Evidence hierarchy is visible and traceable to canonical evidence
- [ ] No missing analytical relationships are invented in the frontend
- [ ] Representative quotes exactly match canonical evidence_quote
- [ ] Representative quotes include provenance and Evidence Explorer links
- [ ] Full supporting evidence is collapsible/lazy/paginated or linked through Evidence Explorer
- [ ] `/evidence?opportunity_id=...` deep link works
- [ ] Source distribution is opportunity-specific
- [ ] Play Store >80% dominance caveat appears when applicable
- [ ] Phase 4 derived analysis and Phase 3 canonical evidence are visually distinct
- [ ] No product solutions are shown
- [ ] Loading/error/not-found/empty states work
- [ ] Opportunity Detail is responsive without unintended horizontal overflow

### Task 5.7 — Navigation & Layout

**Objective:** Create the shared application layout, navigation, and responsiveness rules for all user-facing interfaces without performing a final visual/aesthetic redesign.

**Files:** `frontend/app/layout.tsx`, `frontend/components/nav.tsx`

**1. Canonical Routes:**
The current canonical user-facing routes are:
- `/dashboard` (Discovery Pulse / Dashboard, the default landing destination)
- `/evidence` (Evidence Explorer)
- `/query` (Query Interface)
- `/dashboard/opportunities/[opportunity_id]` (Opportunity Detail, a contextual drill-down)

**2. Navigation Items:**
- Primary shared navigation contains: "Discovery Pulse", "Evidence Explorer", "Query Interface".
- Do not create a duplicate top-level navigation item for Opportunity Detail.
- Active state must work for `/dashboard`, `/evidence`, `/query`, and the nested `/dashboard/opportunities/[opportunity_id]`.
- For Opportunity Detail, "Discovery Pulse" may remain the active parent section.

**3. Page Titles / Metadata:**
- Ensure correct Next.js page metadata/browser titles are set (not just visible H1 text).
- Use descriptive titles: "Discovery Pulse — Dashboard", "Discovery Pulse — Evidence Explorer", "Discovery Pulse — Query Interface", "Discovery Pulse — Opportunity Detail".
- Dynamic Opportunity Detail metadata may include the opportunity title if practical, but must use the evidence-corrected problem presentation (no old solution-oriented labels).

**4. Dataset Scope Banner:**
- The shared layout must display a persistent dataset-scope caveat across all four surfaces (Dashboard, Evidence Explorer, Query Interface, Opportunity Detail).
- It must communicate that findings are based on the collected public conversation dataset and should not be generalized to Myntra's total user population.
- The wording should be concise. Do not hardcode analytical counts unless they are runtime/API-driven.

**5. Mobile Navigation:**
- Desktop/laptop: persistent sidebar/navigation where appropriate.
- Tablet/mobile: collapsible menu/drawer with a clear open/close control.
- The menu must close after route selection.
- Content remains accessible when the menu is closed.
- Navigation must not cause whole-page horizontal overflow.

**6. Accessibility Basics:**
- Use semantic navigation elements.
- Ensure accessible labels for mobile menu toggle.
- Ensure keyboard-accessible links/buttons and visible focus behavior.
- Active states must not rely only on color.
- Ensure reasonable touch targets on small screens.
- Do not perform a large accessibility redesign.

**7. Shared Layout Consistency:**
- The shared layout must own only common application chrome.
- It must not duplicate dataset banners, navigation bars, or page wrappers on nested routes such as Opportunity Detail.
- Individual pages remain responsible for their own page-specific content and states.

**8. Responsiveness:**
- Retain the existing responsiveness contract for Dashboard, Evidence Explorer, Query Interface, and Opportunity Detail.
- Sidebar/drawer must not cover unusable content.
- Content width adapts correctly and page headers wrap cleanly.
- No unintended body-level horizontal overflow exists.
- Navigation remains usable at representative desktop, tablet and mobile widths.
- Internal horizontal scrolling inside intentionally wide Evidence Explorer tables remains acceptable.

**9. Offline / Build Compatibility:**
- Do not reintroduce `next/font/google` or another network-dependent runtime/build dependency solely for styling.
- Typography can be revisited during the later visual-polish pass.

**10. Visual Polish Boundary:**
- Keep Task 5.7 focused on shared layout, navigation, route consistency, metadata, dataset caveat, and responsiveness.
- Do not perform the final aesthetic redesign/polish yet.

**Acceptance criteria:**
- [ ] `/dashboard` is the canonical default landing destination
- [ ] Shared navigation contains Discovery Pulse, Evidence Explorer and Query Interface
- [ ] Navigation renders correctly on Opportunity Detail without adding a duplicate top-level item
- [ ] Nested Opportunity Detail route preserves the appropriate active parent state
- [ ] All navigation links resolve to canonical routes
- [ ] Browser/page metadata titles are descriptive and correct
- [ ] Dataset-scope caveat persists across all four user-facing surfaces
- [ ] Dataset caveat does not imply findings represent Myntra's entire user population
- [ ] Mobile navigation opens, closes and navigates correctly
- [ ] Mobile menu closes appropriately after navigation
- [ ] Navigation is keyboard accessible and has basic accessible labels/focus behavior
- [ ] Shared layout does not duplicate application chrome on nested pages
- [ ] Existing responsive behavior of Tasks 5.3–5.6 is preserved
- [ ] No unintended whole-page horizontal overflow exists
- [ ] No network-dependent font/build dependency is reintroduced
- [ ] No final visual redesign is performed during Task 5.7

---

### Phase 5 Completion Gate (FUNCTIONAL BASELINE FROZEN)

**Task Status:**
- Task 5.1 = COMPLETE
- Task 5.2 = COMPLETE
- Task 5.3 = COMPLETE
- Task 5.4 = COMPLETE
- Task 5.5 = COMPLETE
- Task 5.6 = COMPLETE
- Task 5.7 = COMPLETE

**Canonical User-Facing Routes:**
- `/dashboard`
- `/evidence`
- `/query`
- `/dashboard/opportunities/[opportunity_id]`

**Functional Baseline Rules:**
- Phase 3 canonical evidence remains immutable
- Phase 4 derived analysis remains immutable
- frontend/API data must remain runtime-driven
- raw_text remains restricted
- Query Interface remains solution-free
- dataset-scoped quantification must not be generalized to Myntra's full user population
- known local sandbox port/build limitations are environment constraints, not product defects
- final visual/UI polish will be handled as a separate pass and must preserve functional behavior

Phase 5 completion checklist:

- [x] Phase 3 canonical data unchanged
- [x] Phase 4 accepted findings unchanged
- [x] runtime values are not frontend-hardcoded
- [x] API/dashboard metrics reconcile with DB
- [x] raw vs analyzed source distributions are distinct
- [x] percentage denominator semantics are explicit
- [x] global opportunity support is distinct from filtered evidence
- [x] filter options come from canonical DB/config
- [x] invalid filters return explicit errors
- [x] deterministic queries bypass unnecessary LLM synthesis
- [x] structured filtering precedes semantic retrieval
- [x] explicit filters are never silently relaxed
- [x] semantic-only fallback is explicit
- [x] empty retrieval is honest
- [x] query response contract is implemented
- [x] final synthesis output validation exists
- [x] query benchmark passes
- [x] all displayed quotes resolve to canonical evidence_quote
- [x] zero fabricated quotes
- [x] zero unsupported numeric counts
- [x] zero raw_text exposure
- [x] no solution-generation layer
- [x] AI confidence remains explicitly uncalibrated
- [x] canonical vs derived evidence is distinguishable
- [x] opportunity hierarchy is correct
- [x] knowledge graph is bounded
- [x] safe export contains downstream-safe fields only
- [x] dataset caveat remains visible
- [x] loading/empty/error states work
- [x] interfaces meet responsive requirements
- [x] opportunity claims remain traceable to evidence

---

## Phase 6 — Deployment, Weekly Automation & Demo Readiness

**Goal:** Ensure the pipeline can be run automatically on a regular schedule and the application is production-ready, acting as a lean deployment and automation layer around the existing working system.

---

### 1. FROZEN BASELINE

Record explicitly:
- Phase 3 canonical evidence is frozen.
- Phase 4 derived analysis is frozen.
- Phase 5 product behavior is frozen.
- Current backend behavior/API contracts are frozen.
- Current Codex frontend is frozen.

Phase 6 may add deployment/automation/infrastructure behavior, but must not change existing product semantics. Frontend changes are NOT part of Phase 6 except for the smallest read-only demo-readiness status fields already required by Task 6.6, if those fields do not already exist.

---

### Task 6.1 — Production Configuration & Persistence

- Use environment variables for all provider/API secrets.
- No secrets committed to Git.
- Persistent relational database required.
- Preserve existing Chroma/vector storage.
- Do not introduce pgvector unless there is a proven deployment constraint.
- Deployment must preserve pipeline_runs, run_records, observations, Phase 4 derived outputs, and vector data across restart/redeployment.
- Production paths/config should be environment-driven, not hardcoded to local machine paths.
- Log/config differences between local and production should not alter data semantics.
- Do not restructure the backend merely for deployment.

---

### Task 6.2 — Deployment

Verify deployed stack:
- Backend health endpoint works.
- Frontend is reachable.
- Frontend points to deployed backend through environment config.
- Dashboard works.
- Evidence Explorer works.
- Query Interface works.
- Opportunity Detail works.
- Canonical routes remain unchanged.
- Do not perform visual redesign during deployment.

---

### Task 6.3 — Weekly Refresh Scheduler

Scheduler must be ADDITIVE.

Preferred V1: GitHub Actions cron or similarly simple scheduler.
The scheduler must invoke the SAME existing pipeline runner used for manual runs.

DO NOT:
- Duplicate pipeline logic in workflow YAML.
- Create a second extraction/classification pipeline.
- Create scheduler-specific business logic.
- Reimplement Phase 1–4 inside automation code.

The scheduler is only responsible for:
trigger → invoke existing runner → record run provenance → capture success/partial/failure

Every scheduled execution must create:
- New unique `run_id`
- `triggered_by = scheduled` / equivalent canonical value
- `started_at`
- Terminal status

Rolling 12-week window must be calculated dynamically at runtime. Do not hardcode dates.

---

### Incremental Reuse

Preserve existing run/reuse semantics:
- Canonical duplicate raw records must not be recreated.
- Existing valid records receive run_records membership for the new run.
- Unchanged records reuse existing valid AI artifacts where permitted.
- Canonical Phase 3 observations are not duplicated unnecessarily.
- Embeddings are reused when evidence has not changed.
- Failed prior artifacts must not be silently treated as valid reusable outputs.
- A zero-new-record run must still complete successfully and record that no new records were found.

---

### Quota / Provider Failure

Scheduled runs must not corrupt the current production dataset if:
- Provider quota is exhausted.
- Classification/extraction provider fails.
- Source ingestion fails.
- Embedding generation fails.
- Analysis fails.

Record the failure/partial state and reason.
Do NOT replace the current latest successful dataset with a failed or partial run.
Provider quota exhaustion must be treated as an operational run condition, not as permission to fabricate/skip analytical outputs. Do not change provider/model configuration merely to make scheduler execution pass. Provider fallback architecture, if added later, must be separately approved.

---

### Task 6.4 — Concurrency Safety & Latest Successful Dataset

#### Concurrency Safety
Only one pipeline run may execute at a time.
Define a simple V1 lock mechanism using the existing persistence layer or another minimal durable mechanism.

Requirements:
- Detect an active/running pipeline run.
- Safely reject or skip a second invocation.
- Record the reason.
- Avoid duplicate writes.
- Stale/interrupted runs must not permanently block future runs.

Do not introduce Redis, queues, Kubernetes, or distributed orchestration unless there is a demonstrated deployment need.

#### Latest Successful Dataset
Define one canonical resolver for: LATEST SUCCESSFULLY COMPLETED RUN.

All production UI/API surfaces should use this accepted run by default where run-scoped data is required.
Failed, partial, interrupted, or running runs must never replace it.
Preserve run history for debugging. Do not delete failed/partial runs.
Clarify exact accepted statuses and ordering logic.

#### Observability
For each scheduled run, record enough operational metadata to diagnose:
- Trigger type, run_id, start/end time, status, analysis window.
- Sources attempted, source failures.
- Quota/provider errors.
- Record counts.
- Zero-new-record case.
- Final selected successful run.

Keep this lean. Do not build a full monitoring platform.

---

### Task 6.5 — Production Smoke Test

Run ONE controlled live end-to-end production smoke test.

Verify:
ingestion → cleaning/privacy → relevance → extraction → embeddings/evidence store → theme assignment → emergent clustering → root-cause/unmet-need/opportunity analysis → API → Dashboard → Evidence Explorer → Query Interface → Opportunity Detail

- Do not consume unnecessary provider quota.
- Use the smallest safe live refresh/smoke path that still proves the deployed pipeline works.
- If free-tier quota prevents a full live refresh, report that honestly and distinguish infrastructure success from provider-quota limitation.
- Do not fabricate a production-pass result.

---

### Task 6.6 — Demo Readiness

Verify the UI clearly exposes:
- Last successful refresh date/time
- Active analysis window
- Included sources
- Analyzed dataset count
- Persistent dataset-scope caveat

Required caveat:
"Findings reflect the analyzed public dataset and should not be generalized to all Myntra users."

If these fields already exist, reuse them. If a frontend change is genuinely needed, make ONLY the smallest read-only display addition.
Do not redesign the Codex frontend.
Do not add a scheduler admin dashboard, "Run Now" button, schedule editor, or pipeline control center unless explicitly approved later.

---

### Phase 6 Completion Gate

Add/reconcile:

- [ ] Production configuration uses environment-driven secrets and paths
- [ ] Persistent DB and vector data survive redeployment
- [ ] Backend deployed and health endpoint passes
- [ ] Frontend deployed against production backend
- [ ] Dashboard works
- [ ] Evidence Explorer works
- [ ] Query Interface works
- [ ] Opportunity Detail works
- [ ] Weekly scheduler invokes the existing pipeline runner
- [ ] No duplicate scheduled pipeline implementation exists
- [ ] Every scheduled run creates correct provenance/run_id
- [ ] Rolling 12-week window is dynamic
- [ ] Incremental reuse is preserved
- [ ] Zero-new-record run completes safely
- [ ] Provider/source failures are recorded
- [ ] Failed/partial runs never replace latest successful dataset
- [ ] Concurrent runs are prevented
- [ ] Stale/interrupted run behavior is safe
- [ ] Latest successful run resolver is canonical and used consistently
- [ ] Run history remains available
- [ ] One deployed smoke test is performed honestly
- [ ] Demo-readiness dataset metadata is visible
- [ ] Dataset-scope caveat is visible
- [ ] Frozen frontend/backend behavior remains preserved
- [ ] No unnecessary infrastructure was introduced

---

## Cross-Phase Requirements

These requirements apply across all phases and must be verified at each phase gate.

### AI Usage & Token Efficiency

**Implementation Principle:**
LOCAL / DETERMINISTIC WORK FIRST
        ↓
LLM ONLY WHERE JUDGMENT IS REQUIRED
        ↓
SAMPLE
        ↓
EVALUATE
        ↓
SCALE
        ↓
CACHE & REUSE

Never send the entire corpus blindly to an LLM.
Use deterministic SQL/code for counts, filtering, sorting and aggregations.

This project is intended to operate using free-tier AI APIs.
The system must minimize unnecessary requests and tokens without reducing research quality.

**Required rules:**
1. Deduplicate before AI processing.
2. AI processing should happen once per canonical piece of evidence whenever possible.
3. Unchanged records must NOT be reclassified, re-extracted, or re-embedded during every weekly refresh.
4. Reuse successful existing: cleaned records, relevance classifications, structured observations, and embeddings for unchanged canonical records.
5. Only process with AI when a record is: new, materially changed, previously failed, or invalidated because the relevant model/prompt/taxonomy version changed.
6. Use deterministic code rather than LLMs for: date windows, deduplication, counts, percentages, filtering, sorting, source distributions, aggregations, and run statistics.
7. Keep prompts concise and schema-driven.
8. Send only the evidence required for the specific AI task.
9. Do not send entire Reddit threads or YouTube discussions to the model when an individual post/comment contains sufficient evidence.
10. Query Interface synthesis should retrieve only a small configurable top-K evidence set.
11. Root-cause and opportunity synthesis should use a bounded, representative evidence subset rather than the full evidence corpus.
12. Where provider usage information is available, track: `request_count`, `input_tokens`, `output_tokens`, `retries`, `provider`, and `model`.
13. Quota exhaustion must NOT result in a run being marked successfully completed if required AI processing is unfinished.

**Token optimization must never weaken:** verbatim evidence integrity, correct use of unknown, source traceability, extraction quality, or retrieval grounding.

### Configurable Thresholds

Values such as `relevance_confidence_min`, `observation_confidence_min`, theme similarity, near duplicate similarity, `min_observations_for_theme`, and `min_observations_for_opportunity` must be treated as INITIAL CONFIGURABLE DEFAULTS, not universal truths. They may later be calibrated using golden datasets, first real-data runs, error analysis, or evaluation results.

### Auditability

- [ ] Every pipeline step writes a JSONL file to `data/{step}/run_{id}.jsonl`
- [ ] Every AI-generated value stores `extraction_model`, `prompt_version`, and where relevant `provider`, `model_id`, and `created_in_pipeline_run_id`
- [ ] Re-running any step produces the same output given the same input (idempotent)

### Privacy

- [ ] Source identity metadata (usernames, reviewer handles, author IDs, commenter identifiers) must never be stored
- [ ] Restricted `raw_text` may contain text-level PII from the original public conversation
- [ ] `cleaned_text` must mask text-level PII before downstream research/AI use
- [ ] No personal identifiers may appear in cleaned research data, observations, evidence quotes, embeddings, API responses, UI, Query Interface responses, or exports
- [ ] Synthetic test fixtures in `tests/fixtures/` are never mixed into the `data/` directory

### Evidence Integrity

- [ ] No quote in the system is fabricated or paraphrased — all must be verbatim from `cleaned_text`
- [ ] All counts and percentages are database-derived, never LLM-generated
- [ ] Every percentage shown in the UI is labelled as referring to the analyzed dataset

### Configuration

- [ ] Changing `play_store_window_weeks` in `config.yaml` changes the ingestion window without code changes
- [ ] Changing `min_observations_for_theme` changes the theme creation threshold without code changes
- [ ] Adding a new Reddit thread URL to `config.yaml → reddit_threads` is sufficient to include it in the next ingestion run

---

## Deliverables Checklist

| Deliverable | Phase | Acceptance Criteria |
|---|---|---|
| Project skeleton + config | Phase 0 | Directory structure, config loads, DB schema applied |
| PlayStoreAdapter | Phase 1 | 12-week filtered reviews in `raw_records` |
| AppStoreAdapter | Phase 1 | 12-week filtered reviews in `raw_records` |
| RedditThreadIngester | Phase 1 | All 8 threads + comments in `raw_records` |
| YouTubeAPIIngester | Phase 1 | API-discovered video comments in `raw_records` |
| PII Masker | Phase 2 | PII masked in `cleaned_records.cleaned_text` |
| Deduplicator | Phase 2 | Duplicates flagged |
| Spam Filter | Phase 2 | Spam and ads flagged |
| Relevance Classifier | Phase 2 | All records labeled with relevance + confidence |
| Extraction Prompt v1 | Phase 3 | Multi-observation extraction tested on fixtures |
| Observation Extractor | Phase 3 | `observations` table populated |
| Vector Embeddings | Phase 3 | All observations embedded in ChromaDB |
| Theme Grouper | Phase 4 | Predefined/emergent themes created; valid HDBSCAN noise/unassigned observations retained for inspection |
| Root Cause Synthesizer | Phase 4 | Root cause synthesis on all qualifying themes |
| Opportunity Generator | Phase 4 | Opportunity areas in DB |
| FastAPI Backend | Phase 5 | All endpoints returning correct data, including Phase 4 derived entities |
| Grounded Query Engine | Phase 5 | Evidence-grounded NL query responses using ChromaDB retrieval |
| Discovery Pulse Dashboard | Phase 5 | Dashboard renders with real data, opportunity cards with metric relevance |
| Evidence Explorer | Phase 5 | Paginated, filterable, exportable with Phase 4 metadata |
| Grounded Query Interface | Phase 5 | Evidence-grounded interface with evidence cards and caveats |
| Opportunity Detail View | Phase 5 | Evidence hierarchy per opportunity (clusters → root causes → unmet needs) |

---

## What This Plan Does Not Cover

The following are explicitly out of scope for this implementation plan, consistent with the non-goals in `problemStatement.md`:

- Building any Myntra product feature or wishlist improvement
- Integrating with Myntra's internal systems
- Replacing primary user research
- Performing sentiment analysis as the primary output
- Generating statistics claimed to represent all Myntra users
- Recommending discounts, coupons, or monetary interventions
- Fabricating or synthesizing user quotes
- Inferring demographic characteristics not supported by evidence

---

*This implementation plan is derived from [`problemStatement.md`](./problemStatement.md) and [`architecture.md`](./architecture.md). Both documents should be consulted as the authoritative reference during implementation.*
