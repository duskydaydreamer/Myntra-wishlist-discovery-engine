# Edge Cases: Myntra Wishlist Discovery Pulse

> Companion to [`architecture.md`](./architecture.md) and [`implementation-plan.md`](./implementation-plan.md)
>
> This document catalogs every known edge case, corner scenario, and boundary condition across all pipeline layers. Each entry describes the scenario, its risk, and the required handling behavior. Engineers must address every listed case before the corresponding phase is considered complete.

---

## Table of Contents

1. [Data Ingestion Layer](#1-data-ingestion-layer)
   - [1.1 Play Store Adapter](#11-play-store-adapter)
   - [1.2 App Store Adapter](#12-app-store-adapter)
   - [1.3 Reddit Thread Ingester](#13-reddit-thread-ingester)
   - [1.4 YouTube API Ingester](#14-youtube-api-ingester)
   - [1.5 Cross-Source & General Ingestion](#15-cross-source--general-ingestion)
2. [Data Cleaning & Normalization Layer](#2-data-cleaning--normalization-layer)
   - [2.1 Deduplication](#21-deduplication)
   - [2.2 PII Masking](#22-pii-masking)
   - [2.3 Spam & Ad Filtering](#23-spam--ad-filtering)
   - [2.4 Text Normalization](#24-text-normalization)
   - [2.5 Language Detection](#25-language-detection)
3. [Relevance Classification Layer](#3-relevance-classification-layer)
4. [AI Research Extraction Layer](#4-ai-research-extraction-layer)
   - [4.1 Observation Extraction](#41-observation-extraction)
   - [4.2 Schema Integrity & Field Validation](#42-schema-integrity--field-validation)
   - [4.3 LLM Failure & Degradation](#43-llm-failure--degradation)
5. [Theme Grouping & Pattern Discovery Layer](#5-theme-grouping--pattern-discovery-layer)
6. [Root Cause & Opportunity Layer](#6-root-cause--opportunity-layer)
7. [Evidence Store & Database](#7-evidence-store--database)
   - [7.1 Relational Database](#71-relational-database)
   - [7.2 Vector Store](#72-vector-store)
8. [Grounded Query Interface](#8-grounded-query-interface)
9. [Discovery Pulse Dashboard & Evidence Explorer](#9-discovery-pulse-dashboard--evidence-explorer)
10. [Privacy & Compliance](#10-privacy--compliance)
11. [Pipeline Orchestration & Re-Runability](#11-pipeline-orchestration--re-runability)
12. [Configuration & Taxonomy Edge Cases](#12-configuration--taxonomy-edge-cases)
13. [Cross-Cutting Concerns](#13-cross-cutting-concerns)

---

## 1. Data Ingestion Layer

### 1.1 Play Store Adapter

| # | Scenario | Risk | Required Handling |
|---|---|---|---|
| 1.1.1 | **Review returned with no `raw_text`** — scraper returns a review dict with an empty, null, or whitespace-only body | Silent data loss; downstream NLP fails on empty input | Reject the record at normalizer; log `raw_record_id` and reason; do not write to DB |
| 1.1.2 | **Review `published_at` is null or unparseable** | Cannot enforce 12-week window; record may silently bypass the time filter | Log warning; **exclude** the record (do not ingest without a valid date); record exclusion count in pipeline run metadata |
| 1.1.3 | **Scraper returns reviews beyond the 12-week cutoff** | Stale data dilutes recent signal; violates window constraint | Filter `published_at < cutoff_date` **before** any write — this is a hard pre-storage filter, not a post-storage label |
| 1.1.4 | **Scraper API rate-limit or temporary block (HTTP 429 / 503)** | Incomplete ingestion if adapter crashes mid-run | Implement exponential backoff with jitter; retry up to configurable max attempts; if still failing, log the failure, mark `pipeline_runs.status = "partial"`, and continue with other sources |
| 1.1.5 | **`userName` field is nested or appears under a different key in scraper response** | PII accidentally stored before Phase 2 masking | Strip all reviewer-identifying fields (any key containing `user`, `author`, `name`, `id`) at point of collection, before `normalizer.py` is called |
| 1.1.6 | **Duplicate `raw_record_id` across runs** (same review re-fetched in a later run) | Duplicate records inflate counts and skew theme percentages | `writer.py` must upsert by `raw_record_id`; second ingest of the same record is a no-op |
| 1.1.7 | **Zero reviews returned** (scraper blackout, package ID change, or app de-listed) | Silent empty run; dashboard shows stale data from previous run | Distinguish zero-reviews-in-window (normal) from scraper error (abnormal); log both; alert if total fetched is zero with no API error |
| 1.1.8 | **Non-English reviews returned** (Tamil, Hindi, etc.) | LLM extraction quality drops; may produce hallucinated observations | Tag `language` field at ingestion; English-only extraction in V1; flag non-English records with `language_skipped: true` |
| 1.1.9 | **Star rating is missing or outside 1–5 range** | Invalid rating stored; UI may display NaN or out-of-range values | Coerce to `null` if absent or invalid; never fabricate a rating |
| 1.1.10 | **Very long review text** (>10,000 characters — unlikely but possible for a copy-paste haul post) | LLM token limits exceeded during extraction; API call fails | Truncate `raw_text` to a configurable max character limit before extraction (not before storage); log truncation; preserve full original in `raw_records.raw_text` |

---

### 1.2 App Store Adapter

| # | Scenario | Risk | Required Handling |
|---|---|---|---|
| 1.2.1 | **Review has `title` but empty `review_body`** | Partial data; title alone may not carry behavioral signal | Store `title` as `raw_text` if body is empty; flag `cleaning_flags: ["title_only"]`; do not discard — a title like *"Sizing completely off"* is valid behavioral evidence |
| 1.2.2 | **App Store returns only aggregate ratings, no individual reviews** (scraper limitation for some storefronts) | No textual data for analysis | Log the failure explicitly; do not produce an empty observation set silently; raise a pipeline warning |
| 1.2.3 | **India storefront (`in`) returns no results** (geo-restriction or scraper bug) | Entire App Store source is silently empty | Fall back to a permissive storefront only if explicitly configured; otherwise, log and skip |
| 1.2.4 | **`published_at` is returned in a non-ISO format** (e.g., `"3 days ago"`, `"Aug 2024"`) | Time window filter fails or incorrectly excludes records | Normalize to ISO-8601 before comparison; if unparseable, **exclude** the record (same as 1.1.2) |
| 1.2.5 | **App Store review duplicated across runs at different scrape timestamps** | Same user review counted multiple times | Canonical `raw_record_id` must be derived from content + source, not from scrape timestamp; upsert by this deterministic ID |
| 1.2.6 | **Rating-only review** (user left 1 or 5 stars with no text) | Empty `raw_text` with valid metadata | Exclude from AI extraction; store in `raw_records` with `is_spam: false` and `cleaning_flags: ["no_text"]`; do not count toward relevant observations |

---

### 1.3 Reddit Thread Ingester

| # | Scenario | Risk | Required Handling |
|---|---|---|---|
| 1.3.1 | **Thread is deleted or private at time of ingestion** | Entire thread is missing from the evidence corpus | PRAW raises `NotFound` or `Forbidden`; catch and log the specific thread URL; mark `pipeline_runs.errors[]` with the thread URL; continue with remaining threads |
| 1.3.2 | **Reddit API rate limit reached mid-thread** | Partial comment set ingested; thread appears complete but is truncated | Log the last successfully retrieved comment; implement backoff; on final failure, mark thread as `partially_ingested: true` in run metadata |
| 1.3.3 | **`MoreComments` object not expanded** (PRAW's lazy comment tree) | Hidden comments (those behind "load more" buttons) silently absent | Call `replace_more(limit=None)` to fully expand comment trees before iteration; handle PRAW's API call limit gracefully |
| 1.3.4 | **Deleted or removed comments** (`[deleted]` or `[removed]` body) | Noise records with no behavioral content | Detect `body == "[deleted]"` or `body == "[removed]"` and discard before normalization |
| 1.3.5 | **Automoderator and bot comments** (common in fashion subreddits) | Systematic noise; skews relevance classification | Identify known bot patterns (e.g., `AutoModerator`, `bot_` prefix); discard before normalization; log count |
| 1.3.6 | **Username appears inline in comment body** (e.g., "Thanks u/username123!") | PII leak — username survives into cleaned text even after `author` field is stripped | Phase 2 PII masking must catch Reddit username patterns (`u/[A-Za-z0-9_-]+`); replace with `[USERNAME]` |
| 1.3.7 | **Comment `body` contains only a URL or emoji** | No behavioral text to analyze | Detect records where stripped `body` contains no alphabetic content; flag `cleaning_flags: ["no_text"]`; exclude from AI extraction |
| 1.3.8 | **Deeply nested comment thread** (replies to replies to replies) | Thread parent–child mapping becomes incorrect; duplicate parent IDs | Store parent_post_id as the Reddit submission ID for top-level comments, and direct parent comment ID for replies. Do not introduce a second comment_parent_id field. |
| 1.3.9 | **Thread URL changes format** (old vs. new Reddit URL scheme) | `submission.id` extraction fails | Normalize URL before submitting to PRAW; test both `reddit.com/r/.../comments/ID/` and `old.reddit.com` formats |
| 1.3.10 | **Submission post body is empty** (link-only posts) | Original post has no text; only comments carry evidence | Store with `raw_text = ""` and `source_type = "post"`; mark `cleaning_flags: ["no_text"]`; do not exclude — comments are still ingested |
| 1.3.11 | **Subreddit requires age-verification or is quarantined** | PRAW raises auth error | Catch specific PRAW errors; log and skip; do not retry silently |

---

### 1.4 YouTube API Ingester

| # | Scenario | Risk | Required Handling |
|---|---|---|---|
| 1.4.1 | **YouTube Data API daily quota exhausted** | Ingestion stops mid-run; partial video/comment set | Track quota units consumed per call; estimate remaining budget before each call; if quota is low, prioritize comments over additional video discovery; log quota exhaustion |
| 1.4.2 | **Search query returns zero results** | Some queries may return nothing for regional/language reasons | Log zero-result queries; do not fail the pipeline; continue with remaining queries |
| 1.4.3 | **Comments disabled on a selected video** | `commentThreads.list` returns HTTP 403 `commentsDisabled` | Catch and log; skip the video's comment ingestion; still store video metadata |
| 1.4.4 | **Video is private or removed at time of ingestion** | `videos.list` returns empty `items[]` | Detect empty response; log video ID; skip gracefully |
| 1.4.5 | **Commenter name appears in `comment_text`** (e.g., "@Priya exactly what I was thinking!") | PII in stored comment text | Phase 2 PII masking must catch YouTube mention patterns (`@[A-Za-z0-9_]+`); replace with `[USERNAME]` |
| 1.4.6 | **Creator's own response comment** mixed with user comments | Creator marketing claims should not be treated as user evidence | Detect creator comments by matching `authorChannelId` with the `video.snippet.channelId`; tag `source_type: "creator_comment"`; exclude from behavioral analysis |
| 1.4.7 | **Duplicate videos returned across overlapping search queries** (e.g., "Myntra haul" and "Myntra clothing haul" returning the same video) | Same video's comments ingested and analyzed twice | Deduplicate videos by `video_id` before comment retrieval |
| 1.4.8 | **Comment `textOriginal` vs `textDisplay` mismatch** (HTML entities, links, emoji in display version) | AI extraction receives HTML-encoded text | Always use `textOriginal` for storage; clean HTML entities in normalization |
| 1.4.9 | **Highly promotional video comment section** (giveaway, affiliate link spam) | Spam comments dominate; skew theme analysis | Spam filter in Phase 2 handles this; YouTube-specific heuristic: comments consisting mainly of emoji or shortened URLs are spam candidates |
| 1.4.10 | **Video `published_at` before API epoch or returns null** | Missing temporal metadata | Store `video_published_at: null`; do not exclude video; publication date is informational, not a filter criterion for YouTube |
| 1.4.11 | **Reply comment threads not fully paginated** (`nextPageToken` exists but not followed) | Deep reply threads silently truncated | Always follow `nextPageToken` for both `commentThreads.list` and `comments.list` (replies); stop only when `nextPageToken` is absent |
| 1.4.12 | **Video has >10,000 comments** (viral video) | API quota exhausted on single video; unbalanced source distribution | Cap comments per video at a configurable limit (e.g., 500 top-level + top replies); sample by `likeCount` descending if available |

---

### 1.5 Cross-Source & General Ingestion

| # | Scenario | Risk | Required Handling |
|---|---|---|---|
| 1.5.1 | **`collected_at` clock skew** between ingestion machine and source server | Time window filtering based on local clock may differ from server timestamps | Always use source-provided `published_at` for window filtering, not `collected_at` |
| 1.5.2 | **All four sources return zero records** in a single run | Dashboard appears empty; no errors surfaced | Pipeline must explicitly detect and log this; surface a warning in `pipeline_runs`; do not silently succeed |
| 1.5.3 | **`raw_record_id` collision across sources** (if using a non-UUID deterministic ID scheme) | Record from one source overwrites record from another | Use UUIDv4 or a source-scoped hash (`source + source_native_id`); ensure global uniqueness |
| 1.5.4 | **Record `raw_text` exceeds DB column limit** | DB write fails; record silently dropped | Truncate `raw_text` at storage to a safe max (e.g., 50,000 characters); log truncation; store full text in JSONL file |
| 1.5.5 | **`evidence_type` cannot be determined at ingestion** | Downstream filter on `myntra_specific` vs `category_level` is unreliable | Default to `"unknown"` where not determinable; re-classify during cleaning if possible; never fabricate |
| 1.5.6 | **Pipeline is interrupted mid-ingestion** (crash, OOM, SIGKILL) | Partial run; `pipeline_runs.status` stuck at `"running"` | On startup, detect stale `"running"` runs older than a configurable timeout; mark them `"interrupted"`; allow manual or automatic re-run |

---

## 2. Data Cleaning & Normalization Layer

### 2.1 Deduplication

| # | Scenario | Risk | Required Handling |
|---|---|---|---|
| 2.1.1 | **Exact duplicate within same run** (same review fetched twice in one API call) | Double-counted observation | Hash `raw_text` + `source`; mark second as `is_duplicate: true`, `duplicate_of: <first_raw_record_id>` |
| 2.1.2 | **Exact duplicate across runs** (same review re-fetched in a later ingestion run) | Observation counted again in new run; inflates theme counts | `writer.py` upserts by `raw_record_id`; deduplication check spans all runs, not just the current run |
| 2.1.3 | **Near-duplicate with minor edit** (e.g., reviewer corrects a typo in a re-post) | Both versions extracted; similar but not identical observations | Cosine similarity on TF-IDF or embedding vectors; flag the lower-information copy as near-duplicate; **preserve the richer version** |
| 2.1.4 | **Near-duplicate threshold too aggressive** (0.92 similarity incorrectly groups two distinct short reviews) | Legitimate behavioral signal discarded | Use near-duplicate flagging for **human/audit review**, not automatic deletion; configurable threshold; default behavior = keep both, flag for inspection |
| 2.1.5 | **Copy-paste threads** (Reddit user cross-posts identical comment to multiple threads) | Same behavioral evidence counted multiple times across threads | Cross-thread near-duplicate detection; mark one as primary, others as near-duplicates |

---

### 2.2 PII Masking

| # | Scenario | Risk | Required Handling |
|---|---|---|---|
| 2.2.1 | **Order ID mentioned in review** (`"Order #MYN123456789 was never delivered"`) | Quasi-identifier that could identify a specific transaction | NER or regex must catch Myntra order ID patterns (`MYN[0-9]+`, `#[0-9]{10,}`); replace with `[ORDER_ID]` |
| 2.2.2 | **Phone number in Hinglish format** (`"called on +91-98xxxxxxxx"`) | International format variations not caught by standard NER | Include `+91`, `0`-prefixed, and space/hyphen-separated patterns in PII regex library |
| 2.2.3 | **Masked token breaks meaningful sentence** (e.g., name is part of brand name: "Louis Vuitton") | `[NAME]` token replaces brand name; destroys product context for extraction | Configure NER entity types carefully; mask `PERSON` entities only, not brand or organization names; test on fashion brand names |
| 2.2.4 | **PII masking fails silently** (presidio returns empty result, no exception) | Unmasked PII stored and surfaced in dashboard quotes | Validate masking output is non-null and non-empty; if masking fails, do not proceed — quarantine the record with `pii_status: "masking_failed"` |
| 2.2.5 | **Evidence quote in AI output contains PII** (LLM re-generates unmasked version from context) | PII surfaced in dashboard via AI-generated text | Always feed **masked** `cleaned_text` to the LLM, never `raw_text`; `evidence_quote` must be sourced from `cleaned_text` only |
| 2.2.6 | **Instagram handle mentioned inline** (`"saw this on @priya_fashion"`) | Social handle is a personal identifier | Regex for `@[A-Za-z0-9._]+` patterns; replace with `[USERNAME]` |
| 2.2.7 | **Location PII in fashion context** ("I wore this to a wedding in Bangalore") | "Bangalore" is not PII — it is contextually useful location data | Configure `LOCATION` masking to apply only to specific addresses or residential locations, not to cities or regions used as shopping/occasion context |

---

### 2.3 Spam & Ad Filtering

| # | Scenario | Risk | Required Handling |
|---|---|---|---|
| 2.3.1 | **Short negative review misclassified as spam** (`"Worst app ever, returns don't work"`) | Legitimate behavioral signal removed | Spam classifier must not treat short or negative reviews as spam; evaluate on a labeled sample; precision over recall for spam detection |
| 2.3.2 | **Promotional influencer comment** ("Use my code PRIYA10 for 10% off!") | Advertiser content treated as user evidence | Heuristic: reviews containing discount codes, referral links, or promotional call-to-action phrases → `is_spam: true` |
| 2.3.3 | **App Store fake review clusters** (multiple identical 5-star reviews from suspected bot accounts) | Inflates positive signals; distorts theme distribution | Near-duplicate detection catches identical text; spam filter catches suspiciously high-volume identical patterns |
| 2.3.4 | **Genuine complaint that uses promotional language** ("the sale prices were amazing but sizing was off") | Sale language triggers spam heuristic | Spam filter should detect promotional origin (URL, discount code), not promotional topic (sale, price) |

---

### 2.4 Text Normalization

| # | Scenario | Risk | Required Handling |
|---|---|---|---|
| 2.4.1 | **Excessive line breaks and whitespace** (copy-pasted from a formatted source) | Tokenization artifacts; embedding quality degraded | Strip excess whitespace; collapse multiple newlines to single newline; preserve paragraph breaks |
| 2.4.2 | **Unicode special characters** (curly quotes, em-dashes, zero-width joiners) | Tokenizer treats these as unknown tokens; embeddings degrade | Unicode normalize to NFC; replace typographic quotes with ASCII equivalents; strip zero-width characters |
| 2.4.3 | **Emoji-heavy text** ("loved it 😍😍😍 but sizing is off 😭") | Emoji provides sentiment signal but may confuse NER and token limits | Preserve emoji in `cleaned_text` (they carry sentiment); strip only in contexts where token limits are a concern |
| 2.4.4 | **Mixed script text** (Hinglish — Roman-script Hindi mixed with English) | English-only LLM may partially understand; extraction quality varies | Tag as `language: "hinglish"`; treat as English-adjacent in V1; log extraction confidence; low-confidence observations flagged |
| 2.4.5 | **URLs in review text** (e.g., a Reddit comment linking to an image) | URL may contain PII (username in URL path) or be scraped by LLM | Strip URLs during normalization (after URL PII check); replace with `[URL]` placeholder if contextually relevant |

---

### 2.5 Language Detection

| # | Scenario | Risk | Required Handling |
|---|---|---|---|
| 2.5.1 | **Very short text** (< 20 characters) makes language detection unreliable | Misclassified language; incorrectly skipped or included | For texts below the reliable detection threshold, default to `language: "unknown"`; do not skip |
| 2.5.2 | **True bilingual text** (first sentence in Hindi, second in English) | Detected language = Hindi; English behavioral content excluded | In V1, detect at document level; tag `language: "mixed"`; attempt extraction regardless if English content is present |
| 2.5.3 | **Language detector library unavailable** (import error at runtime) | All records processed without language tagging | Language detection must be non-blocking; if detector fails, tag `language: "unknown"` and continue |

---

## 3. Relevance Classification Layer

| # | Scenario | Risk | Required Handling |
|---|---|---|---|
| 3.1 | **Ambiguous record on the relevance boundary** (e.g., "app crashed while I was trying to checkout") | Misclassified as `not_relevant`; a checkout failure can be a purchase barrier | LLM classifier should detect `checkout` as a journey stage signal; `checkout_failure` may qualify as `delivery_concern` or `platform_trust` barrier |
| 3.2 | **Generic positive review with no behavioral content** (`"Great app! Love it!"`) | Classified as relevant due to surface positivity | Relevance must depend on shopping-decision signals, not sentiment; positive sentiment alone → `not_relevant` |
| 3.3 | **LLM classifier returns a label not in the allowed set** | Downstream filter crashes on unexpected label | Validate classifier output against `{highly_relevant, somewhat_relevant, not_relevant}`; default to `somewhat_relevant` on invalid output; log the anomaly |
| 3.4 | **Classifier confidence is exactly at threshold** (e.g., 0.70 when `relevance_confidence_min = 0.70`) | Boundary case excluded or included inconsistently | Use `>=` comparison (inclusive threshold); document this consistently in classifier code |
| 3.5 | **All records classified as `not_relevant`** (classifier regression or prompt issue) | Empty observation corpus; downstream pipeline silently produces nothing | Detect this; log a pipeline warning; surface in `pipeline_runs.errors[]`; do not proceed to extraction |
| 3.6 | **Record that is relevant in multiple dimensions** (wishlist + sizing + external research all in one comment) | Only one signal detected; others missed | Classification prompt must list all 12 signal types; `signals_detected[]` should be multi-valued, not single-label |
| 3.7 | **Classifier timeout or API error for a single record** | Record silently excluded from downstream extraction | Log `classification_status: "failed"` per record; include in `extraction_failure_count`; do not block pipeline |

---

## 4. AI Research Extraction Layer

### 4.1 Observation Extraction

| # | Scenario | Risk | Required Handling |
|---|---|---|---|
| 4.1.1 | **Single source record produces 0 observations** (LLM finds nothing extractable) | Relevant record contributes nothing to the corpus | Log as `extracted_observation_count: 0`; do not treat as failure; `somewhat_relevant` records are expected to have low yield |
| 4.1.2 | **Single source record produces an unusually high number of observations** (e.g., > 15 from one comment) | LLM hallucinating observations; inflating counts | Cap observations per source record at a configurable limit (e.g., 10); log when cap is reached; review flagged records manually |
| 4.1.3 | **`evidence_quote` in extracted observation does not appear verbatim in `cleaned_text`** | LLM paraphrased or fabricated the quote | Validate every `evidence_quote` with a substring check against `cleaned_text`; if check fails, set `ai_confidence: 0.0` and flag `evidence_quote_unverified: true` |
| 4.1.4 | **LLM sets a field to a value outside the allowed taxonomy** (e.g., `wishlist_intent: "maybe"`) | Downstream filters and aggregations break | Validate all enum fields against `taxonomies.yaml`; unknown values → coerce to `"other"` if an `other` category exists, else `"unknown"` |
| 4.1.5 | **All extracted fields are `"unknown"`** | Zero-information observation stored and counted | Observations where every analytical field is `"unknown"` should be discarded; only `evidence_quote` + `source` are insufficient |
| 4.1.6 | **LLM outputs non-JSON or malformed JSON** | JSON parser raises an exception; record is lost | Wrap extraction call in try-except; attempt JSON repair; if repair fails, log and set `extraction_status: "failed"` for that record |
| 4.1.7 | **Observation quote is longer than the original source text** (LLM expanded the quote) | Evidence fabrication | Reject observations where `len(evidence_quote) > len(cleaned_text)`; flag and log |
| 4.1.8 | **Same behavioral signal extracted as multiple observations** from one sentence | Observation count inflated; theme percentages skewed | Extraction prompt must instruct the model: one observation per distinct behavioral dimension, not one per clause |
| 4.1.9 | **Price-related observation incorrectly classified as solution-level insight** | Violates the Four-Level Evidence Framework | Extraction prompt must enforce: extract the behavior (price uncertainty), not the implied solution (show discount) |
| 4.1.10 | **Observation segment assigned without evidence** (LLM infers demographic) | Violates the constraint: "do not infer unsupported demographic characteristics" | Segment prompt must require a supporting quote for any segment assignment; demographics (age, gender, city) must never be inferred |

---

### 4.2 Schema Integrity & Field Validation

| # | Scenario | Risk | Required Handling |
|---|---|---|---|
| 4.2.1 | **`ai_confidence` returned as string** (`"0.87"`) rather than float | Type mismatch; DB insert fails | Pydantic coerces to float; if coercion fails, default to `0.0` |
| 4.2.2 | **`secondary_barriers` returned as a string** instead of an array (`"quality, price"`) | DB stores malformed JSON; aggregation breaks | Pydantic schema enforces `List[str]`; if LLM returns a string, split on comma and convert |
| 4.2.3 | **`observation_id` collision** (non-UUID generation) | DB primary key violation; record not stored | Use `uuid.uuid4()` for all observation IDs; never derive from content hash |
| 4.2.4 | **`source_record_id` FK missing from DB** (raw record not yet committed when observation is inserted) | FK constraint violation | Ensure `raw_records` write is committed before `observations` insert; use DB transactions |
| 4.2.5 | **`evidence_quote` is null or empty** | Observation has no traceable evidence; violates evidence-first principle | Discard any observation where `evidence_quote` is null or empty; this is a hard constraint |

---

### 4.3 LLM Failure & Degradation

| # | Scenario | Risk | Required Handling |
|---|---|---|---|
| 4.3.1 | **LLM API rate limit hit during bulk extraction** | Extraction stops mid-run; many records unprocessed | Implement per-record retry with exponential backoff; use `tenacity` library; track retry counts |
| 4.3.2 | **Extraction model unavailable** (API outage) | Entire extraction phase fails | Log API error; mark `pipeline_runs.status = "failed"`; allow re-run of extraction step only using `--step extraction` flag |
| 4.3.3 | **`min_extraction_success_rate` threshold breached** (too many records fail) | Low-quality run; results are unreliable | Abort remaining pipeline steps; surface alert; require manual investigation before promotion |
| 4.3.4 | **LLM returns correct JSON but with hallucinated content not present in source text** | Fabricated behavioral signals stored as real evidence | Systematic quote validation (4.1.3); low `ai_confidence` flagging; human audit sampling process |
| 4.3.5 | **Model version changes between pipeline runs** | Observations from different runs are not comparable | Store `extraction_model` and `prompt_version` on every observation; surface model version in dataset stats |

---

## 5. Theme Grouping & Pattern Discovery Layer

| # | Scenario | Risk | Required Handling |
|---|---|---|---|
| 5.1 | **Clustering produces a single mega-cluster** containing all observations | All observations assigned to one theme; no differentiation | Validate cluster count; if only 1 cluster is found for >100 observations, re-tune min_cluster_size, min_samples, or distance configuration |
| 5.2 | **Clustering produces too many micro-clusters** (HDBSCAN min_cluster_size too small) | Themes too granular to be useful; dashboard overwhelming | Re-tune HDBSCAN min_cluster_size and min_samples. Preserve low-support clusters for inspection; do not automatically merge into "Other" or promote to strong opportunity claims. |
| 5.3 | **New observation does not match any predefined theme** | Observation unclassified; potential emergent pattern missed | Route to `emergent_theme_candidates` collection; review when candidate count reaches configurable threshold |
| 5.4 | **All observations map to a single predefined theme** | Dataset appears dominated by one issue; possible classifier overfitting | Validate theme distribution against source distribution; if one theme has >80% of observations, investigate classifier |
| 5.5 | **Theme percentages do not sum to ~100%** (observations assigned to multiple themes) | Dashboard displays misleading totals | Document that themes are not mutually exclusive; show percentages as "% of relevant observations mentioning this theme", not as a pie chart |
| 5.6 | **Emergent theme emerges that contradicts a predefined theme** | Two contradictory themes in the dashboard confuse Product Managers | Emergent themes are reviewed before surfacing; mark them `is_predefined: false` and `requires_review: true` |
| 5.7 | **Theme synthesis LLM call fails** | Theme has no generated root cause summary | Persist the observation cluster; mark `root_cause_synthesis_status: "failed"`; surface theme in dashboard without root cause text; do not fabricate |

---

## 6. Root Cause & Opportunity Layer

| # | Scenario | Risk | Required Handling |
|---|---|---|---|
| 6.1 | **Root cause synthesis generates a solution, not a root cause** (e.g., "Users need a size recommender") | Violates the user-problem vs. solution distinction | System prompt must enforce: "Describe the user's problem and unresolved need. Do not describe a product feature or solution." Validate output against solution-language patterns |
| 6.2 | **Opportunity area automatically generated for a theme with insufficient evidence** (below `min_observations_for_opportunity`) | Weak opportunity surfaces in dashboard with no real support | Hard gate: do not generate opportunity unless `supporting_observation_count >= min_observations_for_opportunity` |
| 6.3 | **All decision outcomes in a theme are `"purchased"`** | No unresolved problem — user resolved barrier successfully | Opportunity criteria does NOT require specific decision_outcome (e.g., `unknown` is valid). However, if all outcomes are `purchased`, the problem is resolved and opportunity confidence should drop. Themes where all outcomes are `purchased` should not generate opportunities |
| 6.4 | **Opportunity description changes significantly between pipeline runs** (LLM non-determinism) | Product Managers see different opportunity framing on re-run | Store opportunity descriptions with `created_at` and `prompt_version`; never overwrite a published opportunity; create a new version instead |
| 6.5 | **A theme maps to multiple opportunity areas** | Overlapping opportunities confuse prioritization | Allowed — but mark `source_theme_ids` on each; surface overlap in dashboard with a note |
| 6.6 | **Zero opportunity areas generated** after a full run | Dashboard opportunity panel is empty | Distinguish "no opportunities met threshold" (expected for small datasets) from "opportunity generation failed"; log the distinction |

---

## 7. Evidence Store & Database

### 7.1 Relational Database

| # | Scenario | Risk | Required Handling |
|---|---|---|---|
| 7.1.1 | **Alembic migration fails on existing data** (e.g., column added as NOT NULL with no default) | Migration aborts; schema inconsistent | Always provide a default for new NOT NULL columns; test migrations against a populated development DB before production |
| 7.1.2 | **SQLite WAL file corruption** (interrupted write during large batch) | DB unreadable; all pipeline data lost | Use SQLite WAL mode with checksums; take JSONL file backups after each pipeline step (files are the source of truth) |
| 7.1.3 | **`raw_text` column storing very large text** (>50,000 chars) | DB query performance degrades | Store truncated version in DB (50,000 chars); full text always in JSONL; `raw_text` DB column is for querying, not archiving |
| 7.1.4 | **PostgreSQL migration path from SQLite not tested** | Schema drift; production deployment fails | Include an explicit migration test from SQLite → PostgreSQL in the deployment checklist |
| 7.1.5 | **Concurrent pipeline runs write to the same DB** | Race conditions on `pipeline_runs` and `observations` tables | Use optimistic locking or a run-mutex; for V1, enforce single-run-at-a-time via a `lock_file` or DB advisory lock |
| 7.1.6 | **Junction table `theme_observations` grows without bound** | Query latency increases over many runs | Index `theme_id` and `observation_id`; consider archiving old run data beyond a configurable retention period |

---

### 7.2 Vector Store

| # | Scenario | Risk | Required Handling |
|---|---|---|---|
| 7.2.1 | **Embedding API returns a null vector** | ChromaDB insert fails; observation not retrievable via semantic search | Validate embedding shape before insert; if null, retry once; on second failure, store with `embedding_status: "failed"` and exclude from semantic retrieval |
| 7.2.2 | **ChromaDB collection grows stale across pipeline runs** (old embeddings for deleted observations remain) | Semantic search returns observations from old runs that no longer exist in the DB | Implement an incremental sync/reconcile step to reuse valid existing embeddings. Embed only new, changed, failed, or invalidated artifacts. |
| 7.2.3 | **Embedding model changes between runs** | Vectors from different models are not comparable; semantic search returns garbage | Store `embedding_model` per observation; if model changes, invalidate and regenerate all embeddings |
| 7.2.4 | **ChromaDB not available** (startup failure) | Semantic retrieval fails; Query Interface returns no results | Degrade gracefully: fall back to structured filter-only retrieval; log that semantic search is unavailable |

---

## 8. Grounded Query Interface

| # | Scenario | Risk | Required Handling |
|---|---|---|---|
| 8.1 | **LLM answers from general training knowledge instead of retrieved evidence** | Response is not grounded; fabricated insights presented as real findings | System prompt must begin: "Answer ONLY from the provided observations. If the provided observations do not contain enough information to answer, say so explicitly. Do not use external knowledge." |
| 8.2 | **Zero observations retrieved for a query** (no matching structured filters or semantic results) | LLM receives empty context and either fabricates or says nothing | Detect empty retrieval set before calling synthesis LLM; return: "No matching observations found in the analyzed dataset for this query." |
| 8.3 | **Query produces a response that contradicts a displayed opportunity area** | Product Manager receives conflicting signals | This is a valid state — opportunities are AI-generated syntheses; individual query responses are evidence-grounded; surface the distinction explicitly in the UI |
| 8.4 | **User asks a query that implies a solution** ("What feature should we build?") | LLM generates product feature suggestions; violates system scope | Detect solution-seeking query intent; redirect: "This system discovers user problems. Here is what the evidence shows about the underlying user behaviors..." |
| 8.5 | **Query returns >50 supporting observations** | Response becomes unwieldy; key evidence buried | Surface top-K observations (configurable, e.g., 10); show count of total supporting observations; allow "Load more evidence" |
| 8.6 | **Exploratory query with no direct structured filter match** | Intent parser cannot map query to structured filters; retrieval falls to semantic search only | Log `filter_match: false`; proceed with semantic-only retrieval; synthesize with explicit caveat: "This answer is based on semantic similarity matching, not structured filter criteria" |
| 8.7 | **Query response cites an evidence quote that contains PII** (masking failure slipped through) | PII exposed to user | Final layer check: before returning the query response, validate that no `evidence_quote` in the response contains known PII patterns; log and redact if found |
| 8.8 | **Query response mixes Myntra-specific and category-level evidence without distinguishing them** | Product Manager draws Myntra-specific conclusions from general fashion data | Label every evidence quote in query response with its `evidence_type`; synthesis text must state when findings mix both types |
| 8.9 | **Streamed response is interrupted mid-generation** (network error) | User sees partial response; may misread truncated finding | On stream failure, display an error state; allow retry; do not store partial responses in query history |
| 8.10 | **Same query submitted multiple times** | Redundant LLM calls; inconsistent responses due to LLM non-determinism | Implement query caching keyed by `pipeline_run_id + normalized_query + active_filters`. Cache response with caveat that dataset may have been updated |

---

## 9. Discovery Pulse Dashboard & Evidence Explorer

| # | Scenario | Risk | Required Handling |
|---|---|---|---|
| 9.1 | **No pipeline run has completed** (fresh installation) | Dashboard displays empty or broken charts | Display an explicit "No data yet" state with instructions to run the pipeline; do not show zeroed-out charts as if they represent real data |
| 9.2 | **`pct_of_relevant` shown as `NaN`** when `relevant_record_count = 0` | Division-by-zero produces `NaN` in the UI | Guard every percentage calculation: `if total == 0: return 0.0` |
| 9.3 | **Theme percentages are shown as a pie chart that sums to >100%** (multi-theme observations) | Pie chart visually misleads Product Manager | Do not use a pie chart for theme distribution; use a bar chart; label as "% of relevant observations" |
| 9.4 | **Evidence quote in dashboard is truncated mid-sentence** | Behavioral context is lost; Product Manager misreads the finding | Truncate at sentence boundary, not at a character limit; always show a "Read full quote" expansion |
| 9.5 | **Source URL in Evidence Explorer leads to a deleted or private page** | Broken link; traceability fails | Validate source URLs at display time or periodically; show a "Source may no longer be available" label rather than a broken link icon |
| 9.6 | **Filter combination produces zero results** | Evidence Explorer shows empty table with no explanation | Display a clear "No observations match the selected filters" message with a "Reset filters" option |
| 9.7 | **`ai_confidence` displayed for every observation, including high-confidence ones** | Overemphasizes AI uncertainty for users who trust the data | Display confidence indicator only for observations below a threshold (e.g., < 0.70); above threshold, show a confidence badge implicitly |
| 9.8 | **Dashboard counts disagree with Evidence Explorer counts** (API response caching lag) | Product Manager loses trust in data consistency | Dashboard API and Evidence Explorer API must query the same underlying `dataset_stats` table, not independently aggregate |
| 9.9 | **CSV export of observations includes `raw_text`** | PII exported outside the system | CSV export must source data from `cleaned_records.cleaned_text` (masked) via `observations.evidence_quote` only; never export `raw_records.raw_text` |
| 9.10 | **Dashboard shows opportunity areas generated from a different (older) run** (if run metadata is updated but opportunity cache is not) | Stale opportunity shown alongside fresh theme counts | Always tag opportunity areas with `pipeline_run_id`; dashboard must show opportunities from the latest completed run, not the latest created |

---

## 10. Privacy & Compliance

| # | Scenario | Risk | Required Handling |
|---|---|---|---|
| 10.1 | **`raw_records.raw_text` accidentally exposed via an API endpoint** | Unmasked PII leaks to the frontend | API layer must never return `raw_text` from `raw_records`; expose only `evidence_quote` from `observations` (post-masking) |
| 10.2 | **Synthetic test data mixed with real pipeline data** | Fabricated evidence presented in dashboard as real user findings | Synthetic records must always have `is_synthetic: true`; all queries and dashboard aggregations must filter `WHERE is_synthetic = false` |
| 10.3 | **PII masking disabled in `config.yaml`** (`pii_masking_enabled: false`) | Raw PII stored and potentially surfaced | Treat `pii_masking_enabled: false` as a dev-only override; add a startup log warning; refuse to write to non-`tests/fixtures/` locations without masking |
| 10.4 | **Source URL in `observations` points to a private Reddit post** (post was public at ingest, now private) | Clicking the link gives a 403 to the end user | Source URLs are informational; validate at display time; show "Source may no longer be publicly accessible" |
| 10.5 | **Ingestion of a source not in the approved V1 source scope** | Unapproved data introduced without review | Validate `source` field on every record against the allowed list at normalization; reject with a pipeline error if an unknown source is detected |
| 10.6 | **Reddit comment `body` contains another user's full name** (e.g., "I agree with Ramesh Sharma") | Name persists into cleaned text | PII NER must catch `PERSON` entities in comment bodies, not just in metadata fields |

---

## 11. Pipeline Orchestration & Re-Runability

| # | Scenario | Risk | Required Handling |
|---|---|---|---|
| 11.1 | **Re-running a pipeline step with the same `run_id` on different data** | Step outputs are overwritten; prior results lost | Each run must have a unique `run_id`; re-running with the same `run_id` overwrites only that run's data — not other runs' data |
| 11.2 | **Step 4 (extraction) is re-run after Step 5 (theme grouping) has already completed** | Theme grouping uses stale observations; new observations not included in themes | Re-running extraction must invalidate downstream steps (themes, opportunities, vectors) for that run; prompt user or log a warning |
| 11.3 | **Pipeline run fails at Step 6 (root cause)** after successful extraction | Observations are stored but no themes or opportunities are generated | Allow partial runs to be resumed from a specific step; do not re-extract if observations are already present for the run |
| 11.4 | **Two pipeline runs overlap in time** (manual trigger while scheduled run is in progress) | Shared DB writes conflict; counts are inconsistent | Enforce a single-active-run lock; second trigger is queued or rejected with a clear error message |
| 11.5 | **`min_extraction_success_rate` is set to 1.0** | Any single extraction failure aborts the entire pipeline | This is a valid config but must produce an explicit warning at startup; recommend a threshold of 0.85 |
| 11.6 | **Pipeline run metadata (`pipeline_runs`) is deleted manually** | Dashboard has no run metadata to display; orphaned observations have no provenance | Provenance is stored in created_in_pipeline_run_id. Deleting a run row must preserve reusable canonical observations. |
| 11.7 | **Weekly scheduler run starts while manual run is in progress** | Shared DB writes conflict; counts are inconsistent | Enforce a single-active-run lock; second trigger is queued or rejected with a clear error message |
| 11.8 | **Weekly scheduler fails silently** | Pipeline stops refreshing; data becomes stale | Implement alerting in the scheduler action (e.g., GitHub Actions email alerts/Slack) to notify maintainers if the cron job fails |

---

## 12. Configuration & Taxonomy Edge Cases

| # | Scenario | Risk | Required Handling |
|---|---|---|---|
| 12.1 | **`config.yaml` is malformed YAML** (syntax error) | Pipeline crashes at startup with an unhelpful parse error | Validate `config.yaml` at startup with a dedicated schema validator; provide a clear human-readable error message indicating the line and key |
| 12.2 | **`app_store_window_weeks` set to 0 or negative** | All App Store reviews excluded (or infinite window) | Validate that window values are positive integers; raise a `ConfigurationError` with a clear message |
| 12.3 | **A taxonomy value is removed from `taxonomies.yaml`** but observations already stored with the old value | Existing observations reference a value no longer in the taxonomy; dashboard filter breaks | Never delete taxonomy values; mark as `deprecated: true` in YAML; filter UI should hide deprecated values unless `show_deprecated: true` |
| 12.4 | **A new taxonomy value is added to `taxonomies.yaml`** but not surfaced in the extraction prompt | LLM never assigns the new value; new category always empty | Extraction prompts must be regenerated when taxonomies change; version the prompts alongside the taxonomy |
| 12.5 | **Reddit thread URL malformed** in `config.yaml` (e.g., missing `/` at end) | PRAW cannot parse the submission ID | Validate all thread URLs at startup: must match `https://www.reddit.com/r/[subreddit]/comments/[id]/` pattern |
| 12.6 | **`sources_enabled` is empty** in `config.yaml` | Pipeline runs with zero sources; produces empty results silently | Validate that at least one source is enabled at startup; raise `ConfigurationError` if list is empty |
| 12.7 | **AI model name in `config.yaml` is invalid or deprecated** | LLM API returns a model-not-found error | Validate model names at startup against a known list or via a lightweight API ping; fail fast before processing data |

---

## 13. Cross-Cutting Concerns

| # | Scenario | Risk | Required Handling |
|---|---|---|---|
| 13.1 | **Observation counts shown in dashboard are not reproducible** between two API calls within the same session | Caching inconsistency; Product Manager distrusts the data | Dataset stats must be computed once per pipeline run and stored in `dataset_stats`; dashboard reads from the stored snapshot, not live aggregation |
| 13.2 | **`is_myntra_specific` filter applied to category-level findings** produces misleading narrowing | Product Manager draws Myntra-only conclusions from filtered data that excludes relevant category signals | Always show "N results for Myntra-specific filter; M additional results in category-level evidence" when filters are applied |
| 13.3 | **AI model produces different results on identical inputs across runs** (LLM non-determinism) | Themes and opportunity areas shift across re-runs; Product Managers question stability | Use deterministic temperature settings (temperature=0 or low temperature) for extraction and classification; document expected variance in caveat text |
| 13.4 | **A high-profile Reddit thread is added manually to `config.yaml` without review** | Unapproved data source changes the evidence corpus silently | Any change to `reddit_threads` in config must be documented in a changelog; V1 scope is fixed to the 8 approved threads |
| 13.5 | **Dashboard displayed in a timezone different from pipeline run timezone** | "Most recent 12 weeks" cutoff date appears incorrect to the user | Store all timestamps in UTC; display in user's local timezone with a UTC label; show window start/end dates explicitly |
| 13.6 | **Very small dataset** (< 50 total relevant observations) | Theme percentages are statistically meaningless; opportunity thresholds not reached | Surface a dataset size warning in the dashboard: "Dataset is small — findings should be treated as preliminary signals, not statistically representative patterns" |
| 13.7 | **Dashboard is accessed by a non-PM user** who treats AI-generated opportunity areas as product decisions | Organizational misuse of preliminary research findings | Every dashboard view must display a persistent caveat: "This system discovers and surfaces user behavioral evidence. Findings are research signals, not product decisions. All insights require human validation." |
| 13.8 | **Evidence quote in dashboard or query response is mistaken for a real Myntra user review by a downstream stakeholder** | Decontextualized quote misrepresents original source | Always label evidence quotes with their source type (`Play Store review`, `Reddit comment`, `YouTube comment`) and date |
| 13.9 | **Structured output mode unavailable for the selected LLM** | LLM returns free-text instead of JSON; extraction fails | Implement a JSON extraction fallback: parse the first valid JSON object or array found in the response using regex before failing |
| 13.10 | **API keys rotate or expire mid-pipeline** | Authentication fails partway through a run | Detect auth errors separately from rate limit errors; on auth failure, immediately abort the affected step and surface a clear key rotation alert |

---

*This document should be reviewed and updated whenever new data sources, AI models, or pipeline steps are introduced.*  
*All edge cases should have corresponding test coverage in `tests/unit/` or `tests/integration/` before their parent phase is considered complete.*
