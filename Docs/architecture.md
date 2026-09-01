# Architecture: Myntra Wishlist Discovery Pulse

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architectural Principles](#2-architectural-principles)
3. [High-Level Architecture](#3-high-level-architecture)
4. [Layer-by-Layer Breakdown](#4-layer-by-layer-breakdown)
   - [4.1 Data Ingestion Layer](#41-data-ingestion-layer)
   - [4.2 Data Cleaning & Normalization Layer](#42-data-cleaning--normalization-layer)
   - [4.3 Relevance Classification Layer](#43-relevance-classification-layer)
   - [4.4 AI Research Extraction Layer](#44-ai-research-extraction-layer)
   - [4.5 Theme Grouping & Pattern Discovery Layer](#45-theme-grouping--pattern-discovery-layer)
   - [4.6 Root Cause & Opportunity Layer](#46-root-cause--opportunity-layer)
   - [4.7 Evidence Store](#47-evidence-store)
   - [4.8 Query & Retrieval Layer](#48-query--retrieval-layer)
   - [4.9 Presentation Layer](#49-presentation-layer)
5. [Data Models & Schemas](#5-data-models--schemas)
6. [AI & LLM Integration](#6-ai--llm-integration)
7. [Technology Stack](#7-technology-stack)
8. [Directory Structure](#8-directory-structure)
9. [Pipeline Orchestration](#9-pipeline-orchestration)
10. [Privacy & Compliance Architecture](#10-privacy--compliance-architecture)
11. [Reliability & Observability](#11-reliability--observability)
12. [Configuration & Environment](#12-configuration--environment)
13. [Deployment Architecture](#13-deployment-architecture)
14. [Open Design Decisions](#14-open-design-decisions)

---

## 1. System Overview

The **Myntra Wishlist Discovery Pulse** is an AI-powered product discovery system that converts large volumes of unstructured public user conversations into structured, evidence-backed research insights.

The system targets a single business problem:

> **Why do users add fashion products to the Myntra wishlist but not purchase them within 30 days?**

It does **not** build a product solution. It builds the research infrastructure that helps Product Managers, Growth Teams, User Researchers, and Designers understand the problem space.

### Core Outputs

| Output | Purpose |
|---|---|
| **Discovery Pulse Dashboard** | Surface recurring themes, wishlist motivations, barriers, and opportunity areas |
| **Evidence Explorer** | Inspect structured observations traceable to individual source records |
| **Grounded Query Interface** | Answer natural-language research questions grounded in the analyzed evidence corpus |

---

## 2. Architectural Principles

| Principle | Rationale |
|---|---|
| **Evidence-first** | Every insight must be traceable to a source record and verbatim quote. Nothing fabricated. |
| **Separation of evidence and interpretation** | Raw quotes, inferred behaviors, and AI hypotheses must be stored and displayed distinctly. |
| **Unknown is valid** | If a field cannot be reliably inferred, it must default to `unknown` / `not_observable`. Never hallucinate. |
| **Taxonomy is a starting point** | Wishlist intents, barriers, and segments are initial research scaffolding — the system must also discover emergent patterns. |
| **Quantification is dataset-scoped** | All percentages and counts refer only to the analyzed dataset, never projected to all Myntra users. |
| **Privacy by default** | PII must be detected and masked before text is sent to LLMs, embeddings, APIs, or UI. |
| **Pipeline is auditable** | Every transformation — raw → cleaned → classified → observed — must be inspectable as intermediate files or database records. |
| **Grounded retrieval over pure generation** | The Query Interface retrieves structured observations first, then synthesizes — not the reverse. |
| **Configurability** | The 12-week review window and taxonomies must be configurable without code changes. |

---

## 3. High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          DATA SOURCES                                        │
│              Play Store · App Store · Reddit · YouTube                       │
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │    INGESTION LAYER         │
                    │  Connectors / Importers    │
                    │  Raw Record Normalization  │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │    CLEANING LAYER          │
                    │  Dedup · PII Mask · Filter │
                    │  Normalize · Spam Remove   │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │  RELEVANCE CLASSIFIER      │
                    │  highly_relevant           │
                    │  somewhat_relevant         │
                    │  not_relevant              │
                    └─────────────┬─────────────┘
                                  │ (relevant only)
                    ┌─────────────▼─────────────┐
                    │  AI EXTRACTION ENGINE      │
                    │  Behavioral Observations   │
                    │  Structured JSON Output    │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │  THEME & PATTERN ENGINE    │
                    │  Theme Grouping            │
                    │  Segment Discovery         │
                    │  Root Cause Analysis       │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │  OPPORTUNITY ENGINE        │
                    │  Unmet Need Synthesis      │
                    │  Opportunity Quantification│
                    └─────────────┬─────────────┘
                                  │
             ┌────────────────────▼──────────────────────┐
             │               EVIDENCE STORE               │
             │  Raw Records · Cleaned Records             │
             │  Observations · Themes · Opportunities     │
             │  Vector Embeddings · Source Metadata       │
             └──────┬─────────────────┬──────────────────┘
                    │                 │
       ┌────────────▼──┐    ┌─────────▼──────────────────┐
       │  REST API /   │    │   GROUNDED QUERY ENGINE     │
       │  Backend BFF  │    │   Retrieval + Synthesis     │
       └────────┬──────┘    └─────────┬──────────────────┘
                │                     │
    ┌───────────▼─────────────────────▼──────────────┐
    │                  FRONTEND                       │
    │  Discovery Pulse · Evidence Explorer · Query Interface │
    └─────────────────────────────────────────────────┘
```

---

## 4. Layer-by-Layer Breakdown

### 4.1 Data Ingestion Layer

**Purpose:** Fetch or import raw public conversations from the verified V1 source scope and persist them in a consistent raw record format.

The V1 source scope is fixed to the following four source groups. No additional sources should be added at this stage. Before implementing ingestion for any source, verify that the selected access method is publicly permitted and does not require bypassing authentication, access restrictions, or platform protections.

---

#### 4.1.1 V1 Source Scope

| Source Group | Adapter | Scope | Time Window |
|---|---|---|---|
| Google Play Store — Myntra | `PlayStoreAdapter` | Package `com.myntra.android` | Most recent 12 weeks (configurable) |
| Apple App Store — Myntra | `AppStoreAdapter` | App ID `907394059`, storefront `in` | Most recent 12 weeks (configurable) |
| Reddit — Curated threads | `RedditThreadIngester` | 8 specified public threads | Thread-based (no time filter) |
| YouTube — API-discovered | `YouTubeAPIIngester` | Videos discovered via specified search queries | Availability-based |

---

#### 4.1.2 Adapter Specifications

##### PlayStoreAdapter — Google Play Store

- **App:** Myntra
- **Package ID:** `com.myntra.android`
- **Official listing:** `https://play.google.com/store/apps/details?id=com.myntra.android&hl=en_IN`
- **Library:** `google-play-scraper` (Python) or equivalent public method
- **Time window:** Most recent 12 weeks, configurable via `play_store_window_weeks`
- **Filter:** Exclude reviews with `published_at` older than the configured window **before** any downstream processing
- **Preserve:** review text, star rating, publication date, source URL reference
- **Strip:** reviewer names and source account identifiers before storage. Text-level PII may remain in raw_text.
- **`source` value:** `play_store`

##### AppStoreAdapter — Apple App Store

- **App:** Myntra — Fashion Shopping App
- **App Store ID:** `907394059`
- **Storefront:** `in` (India)
- **Official listing:** `https://apps.apple.com/in/app/myntra-fashion-shopping-app/id907394059`
- **Library:** `app-store-scraper` (Python) or equivalent public method
- **Time window:** Most recent 12 weeks, configurable via `app_store_window_weeks`
- **Filter:** Exclude reviews with `published_at` older than the configured window **before** any downstream processing
- **Preserve:** review title, review text, star rating, publication date, source URL reference
- **Strip:** reviewer names and source account identifiers before storage. Text-level PII may remain in raw_text.
- **`source` value:** `app_store`

##### RedditThreadIngester — Curated Myntra Threads

- **Library:** PRAW (Python Reddit API Wrapper) — public read-only access
- **Scope:** The 8 curated threads listed below. No additional threads should be added without explicit approval.
- **Per thread:** ingest the original post + all top-level comments + nested replies
- **Preserve:** thread URL, post ID, comment ID, parent–child relationship (`parent_post_id`), publication date
- **Strip:** Reddit usernames and source account identifiers before storage. Text-level PII may remain in raw_text.
- **`source` value:** `reddit`
- **`source_type`:** `post` for the original post, `comment` for all replies
- **Do not** invent, paraphrase, or summarize user quotes — store verbatim text only

**Curated thread list:**

| Thread | URL | Primary Research Dimensions |
|---|---|---|
| A — Wishlist behavior and purchase consideration | https://www.reddit.com/r/IndianFashionAddicts/comments/14r29cl/show_me_ur_myntra_wishlist/ | wishlist behavior, purchase intent, shortlisting, comparison |
| B — Fashion discovery outside Myntra | https://www.reddit.com/r/IndianFashionAddicts/comments/14k5wqe/do_you_guys_buy_from_myntra_how_do_you_discover/ | external research, product discovery, styling/inspiration, unmet discovery needs |
| C — Reviews missing from wishlisted products | https://www.reddit.com/r/IndianFashionAddicts/comments/1osrk03/myntra_is_deleting_reviews_from_the_listed/ | wishlist behavior, review trust, information uncertainty, decision confidence |
| D — Myntra size-guide confusion | https://www.reddit.com/r/IndianFashionAddicts/comments/16ccycw/i_was_checking_myntra_for_a_shirt_and_came_across/ | sizing uncertainty, fit confidence, external verification, pre-purchase information needs |
| E — Myntra vs AJIO size comparison | https://www.reddit.com/r/IndianFashionAddicts/comments/159bh63/size_difference_help/ | cross-platform comparison, size uncertainty, purchase confidence |
| F — Quality uncertainty while shopping on Myntra | https://www.reddit.com/r/IndianFashionAddicts/comments/15x8thm/recommend_me_brands_from_myntra/ | quality uncertainty, social validation, brand trust, information seeking |
| G — Myntra price changes during product consideration | https://www.reddit.com/r/IndianFashionAddicts/comments/132mwar/myntra_hikes_prices_after_product_is_added_to_the/ | price/timing uncertainty, purchase postponement, trust |
| H — Wishlist hesitation around price, quality, delivery | https://www.reddit.com/r/IndianFashionAddicts/comments/14cbt53/whats_going_on_with_myntra/ | wishlist hesitation, price/quality/delivery uncertainty, purchase postponement |

> Thread G involves price-related behavior. This should be analyzed as a potential purchase barrier. Monetary solutions (discounts, cashback) are outside the eventual solution scope.

##### YouTubeAPIIngester — API-Discovered Videos

- **API:** YouTube Data API v3 (public, key-authenticated)
- **Search endpoint:** `GET https://www.googleapis.com/youtube/v3/search`
- **Comment threads endpoint:** `GET https://www.googleapis.com/youtube/v3/commentThreads`
- **Replies endpoint:** `GET https://www.googleapis.com/youtube/v3/comments` (when thread replies need separate retrieval)
- **Do not** begin with manually selected videos; discovery must be API-driven

**Initial search queries:**

```
Myntra haul
Myntra try on haul
Myntra clothing haul
Myntra sizing review
Myntra size review
Myntra quality review
Myntra honest review
Myntra dress haul
Myntra jeans review
Myntra wedding outfits
Myntra vs AJIO
```

**Video selection criteria** — only select videos relevant to at least one of:
- Myntra shopping or actual Myntra purchases
- Product try-ons, fit, or sizing
- Quality, styling, or occasion shopping
- Product comparison or purchase decisions

Prefer videos that have generated meaningful public comment discussions.

**Preserve per video and comment:**

| Field | Description |
|---|---|
| `video_id` | YouTube video ID |
| `video_title` | Title of the video |
| `video_url` | Full public URL |
| `video_published_at` | Video publication date |
| `comment_text` | Verbatim comment text |
| `comment_published_at` | Comment publication date |
| `parent_post_id` | `video_id` for top-level comments; parent comment ID for replies |

- Strip commenter names and source account identifiers before storage. Text-level PII may remain in raw_text.
- `source` value: `youtube`
- `source_type`: `video_comment`
- User comments are the primary qualitative evidence source — not creator marketing claims

---

#### 4.1.3 Time Windows

| Source | Time Window | Rule Applied |
|---|---|---|
| Google Play Store | Most recent 12 weeks (configurable) | Reviews older than window are excluded before downstream processing |
| Apple App Store | Most recent 12 weeks (configurable) | Reviews older than window are excluded before downstream processing |
| Reddit | Thread-based — no time filter | All posts and comments from the 8 curated threads are ingested in full |
| YouTube | Availability-based — no strict filter | Videos discovered via API queries; publication dates preserved for later filtering |

Configuration:

```yaml
ingestion:
  app_store_window_weeks: 12     # configurable
  play_store_window_weeks: 12    # configurable
  record_window_start: true      # record start date in pipeline run metadata
  record_window_end: true        # record end date in pipeline run metadata
```

- The window start and end dates are recorded in pipeline run metadata and surfaced in the Discovery Pulse Dashboard.
- Publication dates are preserved on every record regardless of source, to support time-based filtering in the UI.

---

#### 4.1.4 Evidence Type Classification

Every collected record is classified as one of two evidence types at ingestion. This classification is preserved throughout the full pipeline so findings can be filtered and compared by evidence type.

##### Myntra-Specific Evidence

Conversations that **directly mention or relate to Myntra**.

Examples from V1 sources:
- All Play Store and App Store reviews (Myntra app)
- Reddit threads where users explicitly reference Myntra products, the Myntra app, or Myntra shopping
- YouTube comments on Myntra haul or Myntra shopping videos

##### Category-Level Evidence

Conversations about **online fashion-shopping behavior where Myntra may not be explicitly mentioned**.

Examples from V1 sources:
- Reddit comments about sizing difficulty when shopping online (any platform)
- YouTube comments about fit uncertainty or quality concerns on fashion purchases generally
- Cross-platform comparisons (e.g., Myntra vs AJIO) where the behavior observed applies beyond Myntra

> Both evidence types are valuable. The system must preserve this distinction throughout analysis.

Evidence type is recorded on every raw record and propagated to every downstream observation:

```
evidence_type: "myntra_specific | category_level | unknown"
```

---

#### 4.1.5 Raw Record Schema

Every raw record, regardless of source, is normalized into this schema before storage:

```json
{
  "raw_record_id": "uuid-v4",
  "source": "play_store | app_store | reddit | youtube",
  "source_type": "review | post | comment | video_comment",
  "source_url": "public_url_or_null",
  "published_at": "ISO-8601-date-or-null",
  "collected_at": "ISO-8601-timestamp",
  "title": "review_title_or_video_title_or_null",
  "raw_text": "original_unmodified_text",
  "rating": "numeric_or_null",
  "product_context": "myntra | online_fashion_general | competitor | unknown",
  "evidence_type": "myntra_specific | category_level | unknown",
  "parent_post_id": "reddit_thread_id_or_youtube_video_id_if_comment_else_null",
  "video_id": "youtube_video_id_or_null",
  "video_title": "youtube_video_title_or_null",
  "ingestion_run_id": "pipeline_run_uuid"
}
```

> `raw_text` is never modified after ingestion. All downstream layers operate on a copy.

---

### 4.2 Data Cleaning & Normalization Layer

**Purpose:** Prepare raw records for AI analysis without discarding genuine behavioral evidence.

#### 4.2.1 Cleaning Steps (in order)

```
Raw Text
   │
   ├── [1] Exact Duplicate Detection  → flag & skip duplicates (same raw_text hash)
   ├── [2] Near-Duplicate Detection   → cosine similarity on TF-IDF or embedding vectors
   ├── [3] Empty / Whitespace Check   → discard empty records
   ├── [4] Spam / Ad Classifier       → LLM or heuristic-based binary classifier
   ├── [5] PII Masking                → NER-based detection → replace with [REDACTED]
   ├── [6] Text Normalization         → unicode normalize, strip excess whitespace
   ├── [7] Language Detection         → tag language; optionally translate non-English
   └── Cleaned Record
```

#### 4.2.2 Cleaned Record Schema

```json
{
  "cleaned_record_id": "uuid-v4",
  "raw_record_id": "foreign_key → raw_records",
  "cleaned_text": "normalized_pii_masked_text",
  "is_duplicate": false,
  "duplicate_of": "raw_record_id_or_null",
  "is_spam": false,
  "cleaning_flags": ["near_duplicate", "low_information"],
  "language": "en",
  "cleaned_at": "ISO-8601-timestamp"
}
```

#### 4.2.5 Cleaning Rules

- A short review is **not** automatically low-information. A five-word review like *"sizing is completely off, returned it"* contains a clear behavioral signal.
- Negative sentiment is **not** a disqualifier.
- Informal grammar and typos are **not** disqualifiers.
- Only discard records that are entirely empty, entirely spam/ads, or exact/near-exact duplicates with no additional information.

---

### 4.3 Phase 3: Relevance Classification

**Purpose:** Filter out noise (e.g., "Great app") and keep only records containing shopping-decision signals.

**Process:**

1. Sends `cleaned_text` to the configured classification model.
2. The LLM classifies the record into: `highly_relevant`, `somewhat_relevant`, or `not_relevant`.
3. It also extracts a binary array of `signals_detected` (e.g., `["pricing", "sizing"]`).
4. **Invalid AI Output Handling:** Validate the output schema. If invalid, retry once. If it fails again, mark `classification_status = failed` and skip the record (do not send to extraction).
5. Only records scoring above a configurable threshold (e.g., `relevance_confidence_min`) proceed to the extraction phase.

#### 4.3.4 Classified Record Schema

```json
{
  "classified_record_id": "uuid-v4",
  "cleaned_record_id": "foreign_key",
  "raw_record_id": "foreign_key",
  "relevance_label": "highly_relevant | somewhat_relevant | not_relevant",
  "relevance_confidence": 0.92,
  "signals_detected": ["fit_uncertainty", "external_research"],
  "classified_at": "ISO-8601-timestamp",
  "classifier_model": "configured_model_id"
}
```

---

### 4.4 AI Research Extraction Layer

**Purpose:** Transform relevant conversations into structured, multi-dimensional behavioral observations.

#### 4.4.1 Unit of Analysis

One source record may produce **multiple** independent observations. The extraction prompt must instruct the model to emit an array of observations — not a single topic per record.

Example extraction from a single review:
```
"I saved three dresses but still haven't ordered because I'm unsure
about sizing. I searched YouTube for haul videos to see how they look
on real people."

→ Observation 1: Wishlist behavior = comparison_shortlist
→ Observation 2: Primary barrier = fit_size_uncertainty
→ Observation 3: Information need = real-life fit evidence
→ Observation 4: Workaround = YouTube haul videos
→ Observation 5: External platform = youtube
→ Observation 6: Decision outcome = postponed
```

#### 4.4.2 Extraction Prompt Design

The extraction prompt must:

- Instruct the model to extract **only** what is observable from the text
- Require the model to quote verbatim evidence for every claim
- Default uncertain fields to `"unknown"` or `"not_observable"`
- **Not** fabricate motivations, outcomes, or quotes
- Allow multiple observations per record
- Use structured JSON output mode

```
System Prompt:
You are a behavioral research analyst. Extract structured observations from the following public user conversation about online fashion shopping.

Rules:
1. Extract only what is directly observable or reasonably inferable from the text.
2. For every observation, include the verbatim evidence_quote from the text.
3. Use "unknown" for any field you cannot reliably infer.
4. Do not invent quotes, motivations, outcomes, or statistics.
5. A single text may produce multiple independent observations — emit all of them.
6. Use the output schema provided exactly.

Output: JSON array of observations matching the schema.
```

#### 4.4.3 Observation Schema

```json
{
  "observation_id": "uuid-v4",
  "source_record_id": "raw_record_id",
  "cleaned_record_id": "foreign_key",

  "source": "play_store | app_store | reddit | youtube | product_review | community | social_media | other",
  "source_url": "url_or_null",
  "is_myntra_specific": true,
  "evidence_type": "myntra_specific | category_level | unknown",

  "journey_stage": "browse | wishlist_add | wishlist_revisit | comparison | cart | checkout | post_purchase | unknown",

  "wishlist_intent": "genuine_purchase | price_tracking | comparison | inspiration | bookmarking | aspirational | occasion_planning | unknown",

  "purchase_intent": "high | medium | low | unknown",

  "product_category": "string_or_unknown",

  "theme": "string_or_unknown",

  "primary_barrier": "fit_size_uncertainty | quality_uncertainty | price_timing | comparison_difficulty | styling_uncertainty | occasion_suitability | review_trust_gap | social_validation | availability | delivery_concern | return_exchange_concern | platform_trust | other | unknown",

  "secondary_barriers": ["string"],

  "root_cause": "string_or_unknown",

  "uncertainty": "string_or_unknown",

  "information_needed": "string_or_unknown",

  "workaround": "string_or_unknown",

  "external_platform_used": "youtube | instagram | google | reddit | friends_family | offline_store | competitor | none | unknown",

  "alternative_considered": "true | false | unknown",

  "occasion": "string_or_unknown",

  "decision_outcome": "purchased | postponed | abandoned | still_considering | returned | unknown",

  "segment_signal": "high_intent_deliberator | fit_anxious | comparison_shopper | occasion_shopper | price_watcher | research_heavy | casual_bookmarker | quality_conscious | unknown",

  "evidence_quote": "verbatim_text_from_source",

  "ai_confidence": 0.87,

  "extracted_at": "ISO-8601-timestamp",

  "extraction_model": "model_name_and_version",
  "created_in_pipeline_run_id": "run_id"
}
```

#### 4.4.4 Taxonomy Extensibility

The initial taxonomies (wishlist intent, purchase barrier, segment signal) are a **starting framework**, not a closed set. The extraction prompt should include an `other_theme` field to capture patterns that do not fit existing taxonomy values. These are reviewed periodically and promoted to first-class taxonomy values when sufficient evidence accumulates.

---

### 4.5 Theme Grouping & Pattern Discovery Layer

**Purpose:** Group related observations into recurring themes to surface macro-level patterns across the dataset.

#### 4.5.1 Approaches

**Step 1 — Embedding-based clustering**

Generate vector embeddings for each observation's `evidence_quote` + `primary_barrier` + `uncertainty` + `information_needed`. Apply clustering (e.g., HDBSCAN or k-means with elbow selection) to surface emergent groupings.

**Step 2 — Classification into predefined themes**

Classify each observation into one or more of the initial research themes using an LLM classifier or embedding similarity to theme seed descriptions.

**Step 3 — Emergent theme detection**

HDBSCAN clustering is run across the broader relevant observation corpus (including already mapped observations) to surface emergent themes. If a cluster reaches a minimum observation count threshold (configurable), it is surfaced as a candidate new theme.

#### 4.5.2 Theme Record Schema

```json
{
  "theme_id": "uuid-v4",
  "theme_name": "fit_and_sizing_uncertainty",
  "theme_label": "Fit and Sizing Uncertainty",
  "is_predefined": true,
  "description": "Users hesitate to purchase because they are uncertain how a product will fit.",
  "observation_count": 142,
  "pct_of_relevant": 23.4,
  "common_root_causes": ["string"],
  "associated_wishlist_intents": ["genuine_purchase", "comparison"],
  "associated_purchase_intents": ["high", "medium"],
  "affected_segments": ["fit_anxious", "high_intent_deliberator"],
  "recurring_uncertainties": ["string"],
  "recurring_info_needs": ["string"],
  "common_workarounds": ["string"],
  "external_research_behaviors": ["youtube", "google"],
  "representative_quotes": ["string"],
  "source_distribution": { "play_store": 42, "reddit": 58, "youtube": 31 },
  "myntra_specific_count": 71,
  "category_level_count": 71,
  "avg_ai_confidence": 0.84,
  "created_at": "ISO-8601-timestamp"
}
```

#### 4.5.3 Segment Analysis

Each behavioral segment is analyzed cross-theme to show:

- Which themes most affect each segment
- Wishlist intent distribution within a segment
- Purchase intent distribution within a segment
- Common barriers and workarounds per segment
- External research behaviors per segment

---

### 4.6 Root Cause & Opportunity Layer

**Purpose:** Move from recurring patterns (themes) to actionable opportunity areas defined as user problems or unmet needs.

#### 4.6.1 Root Cause Extraction per Theme

For each theme, the system runs a synthesis step:

```
Theme observations
      ↓
What happened? (observation summary)
      ↓
What prevented progress? (primary barriers)
      ↓
Why did that barrier exist? (root cause)
      ↓
What information was missing? (information_needed)
      ↓
What did the user do instead? (workarounds)
```

This synthesis is LLM-driven, grounded in the actual observation records for the theme. The model is given the observations, not free-form prompting.

#### 4.6.2 Opportunity Area Generation

An opportunity area is created when a theme meets all of the following:

The `opportunity_generator.py` module evaluates themes against these criteria:

1. `observation_count` >= `min_observations_for_opportunity` (initial configurable default).
2. Contains high or medium `purchase_intent`.
3. Contains recurring unresolved friction (uncertainty, hesitation, external research).
4. **Decision Outcome:** `postponed`, `abandoned`, or `still_considering` increase confidence, but are NOT mandatory. `unknown` is valid.
5. Must be framed strictly as a **USER PROBLEM**, not a product solution.

Opportunity areas describe the **user problem**, not a solution:

```
Correct:
"Users with purchase intent remain uncertain about how a product will fit because
available sizing information does not give them enough confidence for their specific body type."

Incorrect:
"Build an AI size recommendation feature."
```

#### 4.6.3 Opportunity Area Schema

```json
{
  "opportunity_id": "uuid-v4",
  "opportunity_title": "string",
  "opportunity_description": "user_problem_statement",
  "source_theme_ids": ["theme_id"],
  "supporting_observation_count": 98,
  "pct_of_relevant_observations": 16.1,
  "source_distribution": {},
  "myntra_specific_count": 52,
  "category_level_count": 46,
  "associated_wishlist_intents": ["genuine_purchase"],
  "associated_purchase_intents": ["high", "medium"],
  "associated_segments": ["fit_anxious", "high_intent_deliberator"],
  "recurring_root_causes": ["string"],
  "recurring_uncertainties": ["string"],
  "recurring_info_needs": ["string"],
  "recurring_workarounds": ["string"],
  "external_research_behaviors": ["youtube"],
  "avg_evidence_confidence": 0.81,
  "representative_quotes": ["string"],
  "created_at": "ISO-8601-timestamp"
}
```

> All quantification refers to the analyzed dataset only. Not projected to all Myntra users.

---

### 4.7 Evidence Store

**Purpose:** Persist all pipeline artifacts in a queryable, inspectable, and auditable store.

#### 4.7.1 Storage Architecture

```
Evidence Store
├── Relational DB (SQLite → PostgreSQL)
│   ├── raw_records
│   ├── cleaned_records
│   ├── classified_records
│   ├── observations
│   ├── themes
│   ├── opportunity_areas
│   ├── pipeline_runs
│   └── dataset_stats
│
├── Vector Store (ChromaDB)
│   ├── observation_embeddings (for semantic retrieval)
│   └── evidence_quote_embeddings
│
└── File Store (local filesystem or S3)
    ├── raw_ingestion_dumps/       ← JSONL per run
    ├── cleaned_records/           ← JSONL per run
    ├── classified_records/        ← JSONL per run
    ├── extracted_observations/    ← JSONL per run
    ├── theme_reports/             ← JSON summaries
    └── opportunity_reports/       ← JSON summaries
```

#### 4.7.2 Pipeline Run Metadata

Each pipeline execution is tracked:

```json
{
  "run_id": "uuid-v4",
  "started_at": "ISO-8601-timestamp",
  "completed_at": "ISO-8601-timestamp",
  "status": "running | completed | partial | failed | interrupted",
  "review_window_start": "date",
  "review_window_end": "date",
  "sources_ingested": ["play_store", "reddit"],
  "raw_record_count": 4120,
  "cleaned_record_count": 3891,
  "relevant_record_count": 1743,
  "observation_count": 4218,
  "theme_count": 11,
  "opportunity_count": 6,
  "errors": []
}
```

---

#### 4.8 Query & Retrieval Layer

**Purpose:** Power the Grounded Query Interface with evidence-backed, structured retrieval followed by LLM synthesis.

**Flow:**

1. **Intent Parsing:** LLM parses the query into a structured `{research_intent, implied_filters}` JSON.
2. **Filter Application:** Translates `implied_filters` to SQL `WHERE` clauses on the `observations` table (scoped to the current run via `run_records`).
3. **Retrieval:**
   - Retrieves matching records via structured SQL.
   - If the query implies semantic matching (e.g., "describe behaviors when..."), performs a vector search on the filtered subset.
4. **Caching:** Results are cached, keyed by `pipeline_run_id + normalized_query + active_filters`.
5. **Synthesis:** Passes the top-K retrieved observations to the LLM to generate an answer *strictly grounded in the provided evidence*.

#### 4.8.2 Query Response Schema

```json
{
  "query": "original_user_question",
  "research_intent": "extracted_intent",
  "filters_applied": {},
  "answer": "synthesized_answer_text",
  "evidence_count": 23,
  "supporting_observations": [
    {
      "observation_id": "uuid",
      "evidence_quote": "verbatim_quote",
      "source": "play_store",
      "source_url": "url_or_null",
      "published_at": "date",
      "theme": "fit_and_sizing",
      "primary_barrier": "fit_size_uncertainty",
      "wishlist_intent": "genuine_purchase",
      "purchase_intent": "high",
      "ai_confidence": 0.88
    }
  ],
  "caveats": [
    "This analysis is based on 1,743 relevant observations from a public dataset.",
    "Findings should not be generalized to all Myntra users."
  ],
  "evidence_vs_interpretation_note": "string",
  "generated_at": "ISO-8601-timestamp"
}
```

#### 4.8.3 Exploratory Query Support

For exploratory queries (e.g., *"Find behaviors that suggest users lost decision context after wishlisting"*), the system:

1. Identifies that no structured filter directly maps to the question
2. Falls back to semantic search across all observation embeddings
3. Retrieves observations matching the behavioral pattern semantically
4. Synthesizes findings with an explicit note that this is inference, not direct observation

The Four-Level Evidence Framework is preserved in all responses:

| Level | Displayed Label |
|---|---|
| User Evidence | 📌 What users said |
| Observed Behavior | 🔍 Inferred behavior |
| Possible Unmet Need | 💡 Possible unmet need |
| Potential Solution | ⚙️ One possible solution (not the discovered problem) |

---

### 4.9 Presentation Layer

**Purpose:** Provide the three user-facing interfaces — Discovery Pulse Dashboard, Evidence Explorer, and Grounded Query Interface.

#### 4.9.1 Discovery Pulse Dashboard

**Components:**

| Component | Data Source |
|---|---|
| Dataset Stats Card | `pipeline_runs` + `dataset_stats` |
| Source Distribution Chart | `raw_records.source` aggregation |
| Review Date Range | `pipeline_runs.review_window_*` |
| Wishlist Motivation Chart | `observations.wishlist_intent` aggregation |
| Top Themes Panel | `themes` table with `observation_count` |
| Purchase Barriers Chart | `observations.primary_barrier` aggregation |
| User Uncertainties List | `observations.uncertainty` aggregation |
| Information Needs List | `observations.information_needed` aggregation |
| Workarounds Panel | `observations.workaround` aggregation |
| Behavioral Segments Panel | `observations.segment_signal` aggregation |
| Opportunity Areas Panel | `opportunity_areas` table |
| Representative Quotes Carousel | Representative sample based on theme relevance and diversity from `observations.evidence_quote` |

**Filters:**
- Source
- Wishlist intent
- Purchase intent
- Purchase barrier
- Theme
- Behavioral segment
- Product category
- Journey stage
- Myntra-specific vs category-level

#### 4.9.2 Evidence Explorer

A paginated, filterable table of all observations.

**Columns displayed:**

- Evidence quote (truncated, expandable)
- Source + source type
- Published date
- Wishlist intent
- Purchase intent
- Primary barrier
- Theme
- Root cause
- Uncertainty
- Information needed
- Workaround
- Behavioral segment
- AI confidence
- Source URL (external link)

**Features:**

- Full-text search within evidence quotes
- All structured filters from the Dashboard
- Click-to-expand full observation detail
- Export to CSV / JSON for offline analysis

#### 4.9.3 Grounded Query Interface

A chat-style interface with:

- Natural-language question input
- Structured answer with evidence panel
- Collapsible evidence cards (quote, source, filters applied)
- Query history
- Explicit caveat display
- Evidence vs interpretation labels

---

## 5. Data Models & Schemas

### Entity Relationship Overview

```
pipeline_runs
    │
    ├── run_records (pipeline_run_id FK, raw_record_id FK)
    │
    ├── raw_records (raw_record_id PK) 
    │       │
    │       └── cleaned_records (raw_record_id FK)
    │               │
    │               └── classified_records (cleaned_record_id FK)
    │                       │
    │                       └── observations (source_record_id FK)
    │                               │
    │                               ├── theme_observations (observation_id FK, theme_id FK)
    │                               └── opportunity_observations (observation_id FK, opportunity_id FK)
    │
    ├── themes (theme_id PK)
    │       └── theme_observations (theme_id FK)
    │
    └── opportunity_areas (opportunity_id PK)
            └── opportunity_observations (opportunity_id FK)
```

### Key Tables

#### `raw_records`
```sql
raw_record_id       TEXT PRIMARY KEY,
source              TEXT NOT NULL,
source_type         TEXT,
source_url          TEXT,
published_at        DATE,
collected_at        TIMESTAMP NOT NULL,
title               TEXT,
raw_text            TEXT NOT NULL,
rating              REAL,
product_context     TEXT,
language            TEXT
```

#### `run_records`
```sql
run_record_id       TEXT PRIMARY KEY,
pipeline_run_id     TEXT REFERENCES pipeline_runs(run_id),
raw_record_id       TEXT REFERENCES raw_records(raw_record_id)
```

#### `observations`
```sql
observation_id          TEXT PRIMARY KEY,
source_record_id        TEXT REFERENCES raw_records(raw_record_id),
cleaned_record_id       TEXT REFERENCES cleaned_records(cleaned_record_id),
source                  TEXT,
source_url              TEXT,
is_myntra_specific      BOOLEAN,
journey_stage           TEXT,
wishlist_intent         TEXT,
purchase_intent         TEXT,
product_category        TEXT,
theme                   TEXT,
primary_barrier         TEXT,
secondary_barriers      JSON,
root_cause              TEXT,
uncertainty             TEXT,
information_needed      TEXT,
workaround              TEXT,
external_platform_used  TEXT,
alternative_considered  TEXT,
occasion                TEXT,
decision_outcome        TEXT,
segment_signal          TEXT,
evidence_quote          TEXT NOT NULL,
ai_confidence           REAL,
extracted_at            TIMESTAMP,
model_id                TEXT,
prompt_version          TEXT,
created_in_pipeline_run_id TEXT REFERENCES pipeline_runs(run_id)
```

---

## 6. AI & LLM Integration

### 6.1 LLM Usage Points

| Pipeline Step | LLM Role | Output Type |
|---|---|---|
| Relevance Classification | Classify record relevance | Structured JSON label + signals |
| Behavioral Observation Extraction | Extract multi-dimensional observations | Structured JSON array |
| Theme Synthesis | Summarize root causes per theme | Structured text + JSON |
| Opportunity Area Generation | Synthesize unmet needs from themes | Structured text |
| Query Intent Understanding | Parse research intent + implied filters | Structured JSON |
| Grounded Answer Synthesis | Generate answer from retrieved evidence | Text with citations |
| Spam / Ad Detection | Classify non-content records | Binary label |

### 6.2 LLM Reliability Guardrails

| Risk | Mitigation |
|---|---|
| Fabricated quotes | System prompt: "Only use verbatim text from the input. Never paraphrase as a quote." |
| Hallucinated motivations | Require `evidence_quote` for every extracted field |
| Overconfident inference | Force `unknown` for unobservable fields; return `ai_confidence < 0.5` for borderline cases |
| Spurious counts | All counts come from the database — LLM never generates numbers |
| Mixing training knowledge with retrieval | Grounded query system prompt: "Answer ONLY from the provided observations. Do not use external knowledge." |
| Non-JSON output | Use LLM structured output / JSON mode where available |

### 6.3 Model Selection

The system should support swappable model backends:

```yaml
ai:
  classification:
    provider: groq
    model: llama-3.3-70b-versatile
  extraction:
    provider: groq
    model: llama-3.3-70b-versatile
  synthesis:
    provider: gemini
    model: gemini-2.5-flash
  embedding:
    provider: configurable
    model: configurable
```

### 6.4 Prompt & Model Versioning

Each prompt and model config is versioned and stored. Every extracted observation and synthesis records:

- `model_id` (Do not hardcode model IDs in application code; fetch from configuration)
- `prompt_version`
- `pipeline_run_id`
- `extracted_at`

This allows re-extraction if prompts are improved without losing the history of earlier runs.

---

## 7. Technology Stack

### 7.1 Backend

| Component | Technology | Rationale |
|---|---|---|
| Language | Python 3.11+ | LLM/ML ecosystem |
| API Framework | FastAPI | Async, typed, auto-docs |
| Pipeline Orchestration | Prefect / simple script runner | DAG-based pipeline with retries |
| Task Queue | Celery + Redis (optional) | For async extraction at scale |
| ORM | SQLAlchemy + Alembic | Typed models + migrations |
| Primary Database | SQLite (dev) → PostgreSQL (prod) | Structured observation storage |
| Vector Store | ChromaDB | Embedding-based retrieval |
| Embedding Generation | Configurable embedding model | Consistent with Gemini stack |
| LLM Integration | `google-generativeai` / `groq` SDK | Primary; abstracted behind adapter |
| Data Validation | Pydantic v2 | Schema enforcement |

### 7.2 Data Collection

| Component | Technology |
|---|---|
| Play Store scraping | `google-play-scraper` (Python) |
| App Store scraping | `app-store-scraper` (Python) |
| Reddit | PRAW (Python Reddit API Wrapper) |
| YouTube | `google-api-python-client` (YouTube Data API v3) |
| Near-duplicate detection | `sentence-transformers` + cosine similarity |
| PII detection | `presidio-analyzer` (Microsoft) or spaCy NER |

### 7.3 Frontend

| Component | Technology |
|---|---|
| Framework | Next.js 14 (App Router) |
| Styling | Tailwind CSS |
| Charts | Recharts or Nivo |
| State Management | Zustand or React Query |
| Query Interface | Custom chat UI with streaming |

### 7.4 Infrastructure

| Component | Technology |
|---|---|
| Containerization | Docker + Docker Compose |
| Environment Config | `.env` + `config.yaml` |
| Secrets Management | Environment variables (dev); Secret Manager (prod) |
| File Storage | Local filesystem (dev); S3-compatible (prod) |
| Logging | `structlog` (structured JSON logs) |
| Monitoring | Prometheus + Grafana (optional) |

---

## 8. Directory Structure

```
myntra-discovery-pulse/
│
├── docs/
│   ├── problemStatement.md
│   └── architecture.md
│
├── config/
│   ├── config.yaml              ← ingestion window, model selection, thresholds
│   └── taxonomies.yaml          ← wishlist intents, barriers, segments (editable)
│
├── data/
│   ├── raw/                     ← JSONL dumps per ingestion run
│   ├── cleaned/                 ← cleaned records per run
│   ├── classified/              ← classified records per run
│   ├── observations/            ← extracted observations per run
│   ├── themes/                  ← theme reports per run
│   └── opportunities/           ← opportunity reports per run
│
├── backend/
│   ├── ingestion/
│   │   ├── connectors/
│   │   │   ├── play_store.py
│   │   │   ├── app_store.py
│   │   │   ├── reddit.py
│   │   │   ├── youtube.py
│   │   │   └── manual_importer.py
│   │   ├── normalizer.py        ← raw record schema enforcement
│   │   └── ingestion_runner.py
│   │
│   ├── cleaning/
│   │   ├── deduplicator.py
│   │   ├── pii_masker.py
│   │   ├── spam_filter.py
│   │   └── normalizer.py
│   │
│   ├── classification/
│   │   ├── relevance_classifier.py
│   │   └── prompts/
│   │       └── relevance_v1.txt
│   │
│   ├── extraction/
│   │   ├── observation_extractor.py
│   │   └── prompts/
│   │       └── extraction_v1.txt
│   │
│   ├── analysis/
│   │   ├── theme_grouper.py
│   │   ├── segment_analyzer.py
│   │   ├── root_cause_synthesizer.py
│   │   └── opportunity_generator.py
│   │
│   ├── store/
│   │   ├── database.py          ← SQLAlchemy models + session
│   │   ├── vector_store.py      ← ChromaDB integration
│   │   └── migrations/          ← Alembic migrations
│   │
│   ├── query/
│   │   ├── intent_parser.py
│   │   ├── filter_builder.py
│   │   ├── retriever.py
│   │   └── synthesizer.py
│   │
│   ├── api/
│   │   ├── main.py              ← FastAPI app
│   │   ├── routers/
│   │   │   ├── dashboard.py
│   │   │   ├── evidence.py
│   │   │   ├── query.py
│   │   │   └── pipeline.py
│   │   └── schemas/             ← Pydantic API schemas
│   │
│   ├── pipeline/
│   │   └── runner.py            ← Orchestrates full pipeline end-to-end
│   │
│   └── ai/
│       ├── llm_client.py        ← Abstracted LLM adapter
│       └── embedder.py          ← Embedding generation
│
├── frontend/
│   ├── app/
│   │   ├── dashboard/
│   │   ├── evidence/
│   │   └── query/
│   ├── components/
│   └── lib/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/                ← Synthetic test data (never mixed with real data)
│
├── scripts/
│   ├── run_pipeline.sh
│   ├── seed_taxonomies.py
│   └── export_observations.py
│
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## 9. Pipeline Orchestration

### 9.1 Full Pipeline Sequence

```
run_pipeline(sources, config)
      │
      ├── Step 1: Ingest raw records → data/raw/run_{id}.jsonl
      ├── Step 2: Clean records      → data/cleaned/run_{id}.jsonl
      ├── Step 3: Classify relevance → data/classified/run_{id}.jsonl
      ├── Step 4: Extract observations → data/observations/run_{id}.jsonl
      ├── Step 5: Group themes       → data/themes/run_{id}.json
      ├── Step 6: Synthesize root causes
      ├── Step 7: Generate opportunities → data/opportunities/run_{id}.json
      ├── Step 8: Update vector store (embeddings)
      └── Step 9: Update pipeline_runs metadata
```

### 9.2 Re-Runability

- Each step is idempotent. Re-running a step with the same `run_id` overwrites its outputs.
- Steps can be run individually for debugging (e.g., `python -m backend.pipeline.runner --step extraction --run-id <id>`).
- The cleaning and classification steps write intermediate JSONL files that can be manually inspected before running AI extraction.

### 9.3 Error Handling

- LLM extraction failures on individual records are logged and skipped (not pipeline-fatal).
- Records that fail extraction are flagged with `extraction_status: "failed"` in the database.
- Pipeline run metadata records total success and failure counts.
- A minimum extraction success rate threshold (configurable) can abort the run if too many records fail.

---

## 10. Privacy & Compliance Architecture

### 10.1 PII Masking

PII masking runs **before** any data is stored in the cleaned records table and before any AI processing.

**Detected and masked entity types:**

| Entity Type | Replacement |
|---|---|
| Full names | `[NAME]` |
| Usernames / handles | `[USERNAME]` |
| Email addresses | `[EMAIL]` |
| Phone numbers | `[PHONE]` |
| Physical addresses | `[ADDRESS]` |
| Order IDs | `[ORDER_ID]` |
| Payment info | `[PAYMENT_INFO]` |
| Device identifiers | `[DEVICE_ID]` |

### 10.2 Data Access Control

- `raw_text` in `raw_records` is preserved internally for audit purposes only.
- The API never exposes `raw_text` directly — it exposes `evidence_quote` from observations, which has already been masked.
- Source URLs are included only for publicly accessible pages.

### 10.3 Data Collection Constraints

| Allowed | Not Allowed |
|---|---|
| Public Play Store reviews | Private Myntra internal data |
| Public App Store reviews | Login-protected communities |
| Public Reddit posts and comments | Data obtained via access control bypass |
| Public YouTube comments | Purchased or scraped private datasets |
| Public community discussions | Synthetic data mixed with real findings |

Synthetic data may only be used in `tests/fixtures/` and must be clearly tagged `is_synthetic: true`.

---

## 11. Reliability & Observability

### 11.1 Logging

Every pipeline step logs:

- `run_id`
- `step_name`
- `record_id` (where applicable)
- `status`: `started | succeeded | failed | skipped`
- `duration_ms`
- Structured error details on failure

### 11.2 AI Confidence Tracking

- Every observation stores `ai_confidence` (0.0–1.0).
- Dashboard and Evidence Explorer display confidence where relevant.
- Low-confidence observations (below configurable threshold) are flagged with a visual indicator.
- Aggregate confidence metrics are tracked per pipeline run.

### 11.3 Dataset Integrity Checks

After each pipeline run, the system computes and stores:

```json
{
  "run_id": "...",
  "raw_record_count": 4120,
  "cleaned_record_count": 3891,
  "pct_cleaned": 94.4,
  "relevant_count": 1743,
  "pct_relevant": 44.8,
  "observation_count": 4218,
  "avg_observations_per_record": 2.42,
  "avg_ai_confidence": 0.83,
  "low_confidence_observation_count": 112,
  "extraction_failure_count": 14
}
```

### 11.4 Evidence Auditability

For every insight surfaced in the dashboard or query interface:

- The observation ID is preserved
- The source record ID is preserved
- The verbatim evidence quote is preserved
- The AI model version and extraction timestamp are preserved

This allows any displayed finding to be traced back to the original public source.

---

## 12. Configuration & Environment

### 12.1 `config.yaml`

```yaml
ingestion:
  # App Store and Play Store: strict 12-week window (configurable)
  app_store_window_weeks: 12
  play_store_window_weeks: 12
  record_window_start: true       # record start date in pipeline run metadata
  record_window_end: true         # record end date in pipeline run metadata

  # Other sources: availability-based (no strict window enforced)
  other_sources_window: "availability_based"

  sources_enabled:
    - play_store          # PlayStoreAdapter — com.myntra.android, 12-week window
    - app_store           # AppStoreAdapter  — ID 907394059, storefront 'in', 12-week window
    - reddit              # RedditThreadIngester — 8 curated threads (thread-based, no time filter)
    - youtube             # YouTubeAPIIngester — API-discovered via search queries

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
    provider: groq
    model: llama-3.3-70b-versatile
  extraction:
    provider: groq
    model: llama-3.3-70b-versatile
  synthesis:
    provider: gemini
    model: gemini-2.5-flash
  embedding:
    provider: configurable
    model: configurable
  prompt_version: "v1"

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

### 12.2 `taxonomies.yaml`

Taxonomies are externalized so they can be updated without code changes:

```yaml
wishlist_intents:
  - genuine_purchase
  - price_tracking
  - comparison
  - inspiration
  - bookmarking
  - aspirational
  - occasion_planning
  - unknown

purchase_barriers:
  - fit_size_uncertainty
  - quality_uncertainty
  - price_timing
  - comparison_difficulty
  - styling_uncertainty
  - occasion_suitability
  - review_trust_gap
  - social_validation
  - availability
  - delivery_concern
  - return_exchange_concern
  - platform_trust
  - other
  - unknown

segment_signals:
  - high_intent_deliberator
  - fit_anxious
  - comparison_shopper
  - occasion_shopper
  - price_watcher
  - research_heavy
  - casual_bookmarker
  - quality_conscious
  - unknown

predefined_themes:
  - fit_and_sizing_uncertainty
  - product_quality_uncertainty
  - comparison_difficulty
  - price_timing_hesitation
  - styling_uncertainty
  - occasion_suitability
  - review_trust_gap
  - social_validation
  - availability_concerns
  - delivery_return_exchange_concerns
```

---

## 13. Deployment Architecture

### 13.1 Development (Local)

```
docker-compose up
  ├── backend   (FastAPI on :8000)
  ├── frontend  (Next.js on :3000)
  ├── db        (PostgreSQL on :5432)
  └── chromadb  (ChromaDB on :8001)
```

### 13.2 Production (Single-Server)

```
┌─────────────────────────────────────────┐
│              VPS / Cloud VM             │
│                                         │
│  ┌──────────────┐  ┌──────────────┐    │
│  │   Nginx       │  │  Next.js     │    │
│  │ (reverse proxy│→ │  Frontend    │    │
│  └──────────────┘  └──────────────┘    │
│           │                            │
│           ▼                            │
│  ┌──────────────────────────────────┐  │
│  │       FastAPI Backend            │  │
│  │  (uvicorn + gunicorn workers)    │  │
│  └──────────────────────────────────┘  │
│           │                            │
│  ┌────────▼─────────┐                  │
│  │   PostgreSQL      │                  │
│  └──────────────────┘                  │
│                                        │
│  ┌──────────────────┐                  │
│  │   File Storage    │                  │
│  │ (local or S3)    │                  │
│  └──────────────────┘                  │
└─────────────────────────────────────────┘
```

Pipeline runs are triggered via:
- Manual CLI command: `python -m backend.pipeline.runner`
- Scheduled cron job / weekly scheduler: Implement a weekly trigger (e.g., via GitHub Actions or similar cron scheduler) that hits the same pipeline runner and computes a rolling 12-week window automatically.
- API endpoint (protected): `POST /api/pipeline/run`

---

## 14. Open Design Decisions

| Decision | Options | Recommendation | Status |
|---|---|---|---|
| Primary LLM | Configurable | Groq / Gemini | Decided |
| Vector store (prod) | ChromaDB | ChromaDB | Decided |
| Near-duplicate threshold | 0.90–0.95 cosine similarity | 0.92 (configurable) | Open |
| Frontend framework | Next.js vs Vite + React | Next.js 14 (SSR + API routes) | Open |
| Taxonomy update mechanism | YAML file reload vs DB admin UI | YAML for now, DB admin later | Open |
| Multi-language support | English-only vs translate-and-analyze | English-only in v1 | Open |
| Embedding model | Configurable | Configurable | Decided |
| Synthetic data separation | Separate DB vs flag column | Separate fixtures directory + `is_synthetic` flag | Decided |
| Opportunity creation trigger | Manual review vs auto-generate above threshold | Auto-generate above threshold, human review before surfacing | Open |
| Re-ingestion frequency | Weekly / on-demand | Weekly scheduled and on-demand for v1 | Decided |

---

*This architecture document is derived directly from the [Myntra Wishlist Discovery Pulse Problem Statement](./problemStatement.md).*
*All design decisions reference the problem constraints and non-goals defined therein.*
