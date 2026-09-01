# Problem Statement: Myntra Wishlist Discovery Pulse

---

## Overview

The objective of this project is to build an **AI-powered discovery engine** that helps Product Managers understand why users add fashion products to their Myntra wishlist but do not eventually purchase them.

A wishlist represents an important behavioral signal — the user has expressed interest in a product but has stopped short of purchasing it.

The broader business context is to improve:

> **Wishlist → Purchase Conversion within 30 days**

However, the underlying user problem is not known.

The purpose of this system is to analyze public user conversations at scale and discover:

- Why users add fashion products to their wishlist
- What prevents wishlisted products from being purchased
- What uncertainties remain before purchase
- What causes users to postpone purchase decisions
- How users compare shortlisted products
- What information users seek before purchasing
- What users do outside Myntra before deciding
- What workarounds users currently use
- How these behaviors differ across user segments
- Which recurring unmet needs emerge from user conversations
- Which potential opportunity areas have the strongest supporting evidence

The system should go beyond sentiment analysis and generic review summarization. It should convert unstructured public user conversations into **structured, evidence-backed product insights** explored through:

1. A **Discovery Pulse Dashboard**
2. An **Evidence Explorer**
3. A **Grounded Query Interface**

---

## Product Context

| Field | Value |
|---|---|
| **Product** | Myntra |
| **Project Name** | Myntra Wishlist Discovery Pulse |
| **Primary Users** | Product Managers, Growth Teams, User Researchers, Designers |

The relevant business metric is:

> **Percentage of users who purchase at least one wishlisted item within 30 days of adding it.**

The AI Discovery Engine does not directly improve this metric. Its purpose is to discover the user behaviors, barriers, uncertainties, and unmet needs that may influence it.

---

## Objective

Design and implement an AI-powered system that can:

1. Collect or import public conversations related to Myntra and online fashion shopping
2. Import Myntra App Store and Play Store reviews from the **most recent 12 weeks** via a rolling analysis window
3. Clean, normalize, deduplicate, and privacy-filter collected data
4. Identify conversations that contain useful shopping-decision evidence
5. Extract structured behavioral observations using AI
6. Identify recurring wishlist motivations, purchase barriers, uncertainties, workarounds, and decision behaviors
7. Discover patterns across different behavioral user segments
8. Use structured classification and emergent pattern discovery to group observations into recurring themes
9. Identify root causes and possible unmet needs within those themes
10. Convert recurring unresolved problems into potential opportunity areas
11. Quantify recurring patterns where the available evidence allows it
12. Preserve supporting evidence for every important insight
13. Attribute every downstream artifact to a specific pipeline run, preserving historical runs
14. Present findings through a Discovery Pulse Dashboard (defaulting to the latest successfully completed pipeline run)
15. Allow Product Managers to inspect the underlying evidence
16. Allow Product Managers to investigate the evidence through a Grounded Query Interface
17. Support exploratory queries that surface implicit user needs even when users do not explicitly request features
18. Support a weekly refresh scheduler triggering the same pipeline

---

## Target Users

| User | Need |
|---|---|
| **Product Managers** | Discover and investigate user problems from large volumes of public feedback |
| **Growth Teams** | Understand barriers that may prevent wishlist interest from converting into purchase |
| **User Researchers** | Identify hypotheses and behavioral segments that require deeper research |
| **Designers** | Understand user uncertainties, decision processes, and workarounds |
| **Product Leadership** | Review evidence-backed opportunity areas without reading thousands of conversations |

---

## Core Research Questions

The system should help answer questions such as:

- Why do users add fashion products to their wishlist?
- When does a wishlist represent genuine purchase intent?
- When is a wishlist being used as a bookmark, inspiration board, comparison list, or price tracker?
- What prevents wishlisted products from eventually being purchased?
- What uncertainties remain after users have identified a product they like?
- What causes users to postpone a purchase?
- How do users compare multiple shortlisted products?
- What information do users look for before deciding to purchase?
- What information do users seek outside Myntra?
- What role do fit and size play in purchase hesitation?
- What role does product quality play?
- What role do reviews and ratings play?
- What role does styling uncertainty play?
- What role does occasion suitability play?
- What role does price or purchase timing play?
- What role does social validation play?
- What role do delivery, returns, exchanges, and trust play?
- What workarounds do users currently use?
- How do these behaviors differ across user types?
- What implicit unmet needs appear repeatedly?
- Which opportunity areas have the strongest supporting evidence?

---

## End-to-End System Flow

```text
Public User Conversations
        ↓
Data Ingestion
        ↓
Cleaning + Normalization
        ↓
Deduplication + Privacy Filtering
        ↓
Relevance Classification
        ↓
Structured AI Research Extraction
        ↓
Theme Grouping
        ↓
Root-Cause + Unmet-Need Discovery
        ↓
Opportunity Quantification
        ↓
Evidence Store
        ↓
┌─────────────────────────────┐
│ Discovery Pulse Dashboard   │
└─────────────────────────────┘

┌─────────────────────────────┐
│ Evidence Explorer           │
└─────────────────────────────┘

┌─────────────────────────────┐
│ Grounded Query Interface    │
└─────────────────────────────┘
```

---

## What the System Must Build

### 1. Discovery Pulse Dashboard

Helps a Product Manager quickly scan what patterns are emerging across the analyzed conversations. The dashboard should default to showing data from the **latest successfully completed pipeline run**.

**The dashboard should include:**

- Total raw, cleaned, and relevant conversations for the run
- Total structured observations
- Source distribution and review analysis window
- Earliest and latest review date
- Myntra-specific vs broader online fashion-shopping evidence
- Top wishlist motivations
- Top recurring themes and purchase barriers
- Top user uncertainties and information needs
- Top workarounds and external research behaviors
- Recurring behavioral segments
- Emerging opportunity areas
- Representative supporting user quotes

**Useful filters may include:**

- Source, wishlist intent, purchase intent, purchase barrier
- Theme, behavioral segment, product category
- Journey stage, Myntra-specific vs category-level evidence

---

### 2. Evidence Explorer

Allows Product Managers to inspect the evidence behind important findings.

Each evidence item should display, where available:

| Field | Description |
|---|---|
| Evidence Quote | Anonymized supporting quote |
| Source | Source name and type |
| Source URL | Link to original public source |
| Published Date | When the review/post was published |
| Wishlist Intent | Why the product was wishlisted |
| Purchase Intent | High / Medium / Low / Unknown |
| Theme | Recurring pattern classification |
| Purchase Barrier | Primary barrier identified |
| Root Cause | Underlying reason if observable |
| Uncertainty | What the user is unsure about |
| Information Needed | Information the user is seeking |
| Workaround | Current user workaround |
| Behavioral Segment | Segment signal if observable |
| AI Confidence | Model confidence score |

> Every major insight shown by the system should be traceable back to supporting evidence.

---

### 3. Grounded Query Interface

Allows Product Managers to investigate the analyzed dataset using natural-language questions.

**Example queries:**

- Why do users add products to wishlists?
- What prevents high-intent users from purchasing?
- Why do users postpone fashion purchases?
- What are the common causes of fit uncertainty?
- How do users compare shortlisted products?
- What information do users seek outside Myntra?
- What workarounds do users use when reviews are not enough?
- Which segments show the strongest fit-related uncertainty?
- What unmet needs appear repeatedly?
- Which opportunity areas have the strongest supporting evidence?

**Each answer should include, where appropriate:**

- Direct answer
- Supporting evidence and anonymized user quotes
- Source references and relevant counts
- Important caveats
- Distinction between observed evidence and AI interpretation

> The Query Interface must answer using the analyzed evidence corpus. It should not answer research questions purely from the LLM's general knowledge.

---

## Exploratory Query Capability

Users do not always explicitly request features. Instead they describe behaviors:

> *"I had saved a dress earlier but completely forgot about it."*
> *"I had too many things saved and couldn't remember which ones I actually wanted."*

The Query Interface should support **exploratory product-discovery questions** that surface behaviors, frustrations, or repeated situations indicating an underlying unmet need.

**Example exploratory queries:**

- Find conversations where users mention forgetting about products they previously liked, saved, or intended to buy
- Find evidence that users lose track of products after saving many items
- Find conversations where users repeatedly revisit a product but still do not purchase
- Find users who struggle to choose between several shortlisted products
- Find users who leave the shopping platform because they still need more information
- Find behaviors that suggest strong purchase intent even when users do not explicitly state that intent
- What problems are users describing without directly asking for a feature?
- What implicit unmet needs appear repeatedly across high-intent conversations?

### Four-Level Evidence Framework

The system must distinguish between:

| Level | Description |
|---|---|
| **User Evidence** | What the user actually said |
| **Observed Behavior** | A behavior that can be reasonably inferred from the evidence |
| **Possible Unmet Need** | A hypothesis derived from repeated evidence |
| **Potential Solution** | A feature or intervention that could address the unmet need |

> The system must not automatically treat a potential solution as the discovered user problem.

**Example:**

```text
User Evidence:
"I had so many things saved that I forgot which ones I actually wanted."

Observed Behavior:
The user accumulated many saved products and lost track of their original purchase consideration.

Possible Unmet Need:
The user may need help maintaining context or prioritizing previously saved products.

Incorrect Conclusion:
"Users need wishlist reminders."

A reminder is only one possible solution and should not be treated as the discovered problem.
```

---

## Data Sources

The following four source groups form the verified V1 source scope for the Myntra Wishlist Discovery Pulse.

No additional data sources should be added at this stage.

Before implementing ingestion for any source, verify that the selected access method is publicly permitted and does not require bypassing authentication, access restrictions, or platform protections.

---

### Source 1 — Google Play Store (Myntra)

**Official listing:** https://play.google.com/store/apps/details?id=com.myntra.android&hl=en_IN

**Package ID:** `com.myntra.android`

Requirements:

- Import Myntra reviews from the most recent 12 weeks
- Preserve review text, rating, and publication date where available
- Do not retain reviewer names or other personal identifiers
- Store source as `play_store`
- Preserve the source URL or reference
- Filter imported data to the configured 12-week analysis window before downstream analysis

---

### Source 2 — Apple App Store (Myntra)

**Official listing:** https://apps.apple.com/in/app/myntra-fashion-shopping-app/id907394059

**App Store ID:** `907394059`

**India storefront:** `in`

Requirements:

- Import Myntra reviews from the most recent 12 weeks
- Preserve review title, review text, rating, and publication date where available
- Do not retain reviewer names or other personal identifiers
- Store source as `app_store`
- Preserve the source URL or reference
- Filter imported data to the configured 12-week analysis window before downstream analysis

---

### Source 3 — Reddit (Curated Myntra Threads)

The initial Reddit dataset uses the following curated public threads. These threads should be treated as qualitative user evidence, not as statistically representative of Myntra's entire user base.

For every thread:

- Ingest the original post
- Ingest relevant comments
- Preserve the thread URL
- Preserve post and comment relationships where possible
- Do not retain Reddit usernames or personal identifiers
- Store source as `reddit`
- Do not invent or paraphrase user quotes when storing evidence

**Thread A — Wishlist behavior and purchase consideration**

https://www.reddit.com/r/IndianFashionAddicts/comments/14r29cl/show_me_ur_myntra_wishlist/

*Why relevant:* The discussion explicitly involves Myntra wishlists and products users are considering buying.

*Research dimensions:* wishlist behavior · purchase intent · product shortlisting · comparison

**Thread B — Fashion discovery outside Myntra**

https://www.reddit.com/r/IndianFashionAddicts/comments/14k5wqe/do_you_guys_buy_from_myntra_how_do_you_discover/

*Why relevant:* The discussion is about difficulty discovering desirable products on Myntra and users moving to platforms such as Pinterest and Instagram for fashion discovery.

*Research dimensions:* external research behavior · product discovery · styling/inspiration · unmet information or discovery needs

**Thread C — Reviews missing from wishlisted products**

https://www.reddit.com/r/IndianFashionAddicts/comments/1osrk03/myntra_is_deleting_reviews_from_the_listed/

*Why relevant:* The discussion includes users reporting that reviews were missing for products already present in their Myntra wishlist.

*Research dimensions:* wishlist behavior · review trust · information uncertainty · decision confidence

**Thread D — Myntra size-guide confusion**

https://www.reddit.com/r/IndianFashionAddicts/comments/16ccycw/i_was_checking_myntra_for_a_shirt_and_came_across/

*Why relevant:* The discussion concerns confusing sizing information while evaluating a Myntra product.

*Research dimensions:* sizing uncertainty · fit confidence · external verification · information needed before purchase

**Thread E — Myntra vs AJIO size comparison**

https://www.reddit.com/r/IndianFashionAddicts/comments/159bh63/size_difference_help/

*Why relevant:* The discussion compares sizing information between Myntra and AJIO.

*Research dimensions:* cross-platform comparison · size uncertainty · product evaluation · purchase confidence

**Thread F — Quality uncertainty while shopping on Myntra**

https://www.reddit.com/r/IndianFashionAddicts/comments/15x8thm/recommend_me_brands_from_myntra/

*Why relevant:* The user is searching for Myntra products but expresses uncertainty about the quality of available options and seeks other people's recommendations.

*Research dimensions:* quality uncertainty · social validation · brand trust · information seeking · purchase consideration

**Thread G — Myntra price changes during product consideration**

https://www.reddit.com/r/IndianFashionAddicts/comments/132mwar/myntra_hikes_prices_after_product_is_added_to_the/

*Why relevant:* The discussion concerns perceived price changes after a product has already entered the user's consideration process.

*Research dimensions:* price/timing uncertainty · purchase postponement · trust · product consideration

> Note: Price-related behavior should be analyzed as a potential barrier, even though monetary incentives are outside the eventual solution scope.

**Thread H — Wishlist items with price, quality, and delivery hesitation**

https://www.reddit.com/r/IndianFashionAddicts/comments/14cbt53/whats_going_on_with_myntra/

*Why relevant:* The discussion contains users referring to products in their wishlist while expressing hesitation around factors such as price, quality, and delivery.

*Research dimensions:* wishlist hesitation · price uncertainty · quality uncertainty · delivery concerns · purchase postponement

---

### Source 4 — YouTube (Myntra Shopping Discussions)

YouTube videos and comments should be discovered programmatically using the YouTube Data API, not selected manually from an arbitrary list.

**API references:**

- Search videos: https://developers.google.com/youtube/v3/docs/search/list
- Retrieve comment threads: https://developers.google.com/youtube/v3/docs/commentThreads/list

Use the following initial search queries to discover relevant videos:

- Myntra haul
- Myntra try on haul
- Myntra clothing haul
- Myntra sizing review
- Myntra size review
- Myntra quality review
- Myntra honest review
- Myntra dress haul
- Myntra jeans review
- Myntra wedding outfits
- Myntra vs AJIO

Only select videos that are directly relevant to at least one of:

- Myntra shopping
- Actual Myntra purchases
- Product try-ons
- Fit or sizing
- Quality
- Styling
- Occasion shopping
- Product comparison
- Purchase decisions

Prefer videos with meaningful public comment discussions.

For each selected video and its comments, preserve where available:

- `video_id`
- `video_title`
- `video_url`
- `video_published_at`
- `search_query` (that discovered it)
- `selection_reason`
- `comment_text`
- `comment_published_at`
- `number_of_comments_collected`
- `comment_sampling_rule` (if sampling occurs)
- `source = youtube`

Avoid selecting comments only by popularity/likeCount. If a comment section is extremely large, use a documented mixed strategy or a deterministic configurable cap. Run relevance classification after ingestion.

Do not retain commenter names or personal identifiers (channel identifiers).

User comments, rather than creator marketing claims, should be treated as the primary qualitative user-evidence source.

---

## Evidence Type

Every collected record should also be classified as one of the following:

### Myntra-Specific Evidence

Conversations that directly mention or relate to Myntra.

Examples:

- Myntra App Store reviews
- Myntra Play Store reviews
- Reddit discussions mentioning Myntra
- Comments on Myntra haul or review videos
- Public conversations about shopping on Myntra

### Category-Level Evidence

Conversations about online fashion-shopping behavior where Myntra may not be explicitly mentioned.

Examples:

- Difficulty selecting the right clothing size online
- Comparing several shortlisted fashion products
- Searching YouTube for try-on or haul videos
- Checking Reddit or communities before purchasing
- Asking for opinions or social validation
- Uncertainty about quality or material
- Shopping for a specific occasion
- Losing track of previously saved products
- Using wishlists for bookmarking, inspiration, comparison, or price tracking
- Researching products across multiple shopping platforms

Both evidence types are valuable.

Myntra-specific evidence helps identify problems occurring within the Myntra shopping experience, while category-level evidence can reveal broader fashion-shopping behaviors and unmet needs that users may not explicitly describe in Myntra reviews.

The system must preserve this distinction throughout analysis so Product Managers can filter and compare Myntra-specific findings against broader category-level patterns.

---

## Review Time Window

Time windows differ by source:

| Source | Window | Rule |
|---|---|---|
| Google Play Store reviews | Most recent 12 weeks | Strict — exclude reviews outside the configured window |
| Apple App Store reviews | Most recent 12 weeks | Strict — exclude reviews outside the configured window |
| Reddit | Thread-based | Ingest the 8 curated threads in full; no time-window filter applied |
| YouTube | Availability-based | Discover via API search queries; select videos with meaningful comment evidence |

For Apple App Store and Google Play Store reviews, the ingestion pipeline should:

- Fetch or import reviews from the latest 12-week period
- Preserve the original review publication date
- Exclude reviews outside the configured analysis window
- Record the start and end date of the analyzed period
- Show the analyzed date range in the Discovery Pulse Dashboard

> The 12-week review window should be configurable so it can be changed later if required.

For Reddit, the curated thread list defines the scope — not a time window. All posts and comments from the listed threads should be ingested.

For YouTube, videos are discovered through the specified API search queries. Comments are retrieved from selected relevant videos. No strict time window is enforced, but publication dates should be preserved wherever available so findings can be filtered by time period.

---

## Raw Data Requirements

The dataset versioning must distinguish between canonical source evidence and evidence included in a particular pipeline run. A source record may belong to multiple pipeline runs without being duplicated as canonical evidence.

- `raw_records` = unique canonical source records
- `pipeline_runs` = individual analysis runs
- `run_records` = relationship between a pipeline run and the raw records included in that run. Current-run membership comes from this table.

Each canonical collected conversation should be stored with the following schema:

```json
{
  "raw_record_id": "unique_id",
  "source": "play_store | app_store | reddit | youtube",
  "source_type": "review | post | comment | video_comment",
  "source_url": "public_url_if_available",
  "published_at": "date_if_available",
  "collected_at": "collection_timestamp",
  "title": "title_if_available",
  "raw_text": "original_text",
  "rating": "rating_if_available",
  "product_context": "myntra | online_fashion_general | competitor | unknown",
  "evidence_type": "myntra_specific | category_level | unknown",
  "parent_post_id": "reddit_thread_or_youtube_video_id_if_comment",
  "video_id": "youtube_video_id_if_applicable",
  "video_title": "youtube_video_title_if_applicable",
  "search_query": "query_if_applicable",
  "selection_reason": "reason_if_applicable",
  "comment_sampling_rule": "rule_if_applicable"
}
```

> Original text should be preserved internally (locally, excluded from Git, not exposed via API/UI) so AI-generated observations can be audited.

---

## Data Cleaning

Before AI analysis, collected data should pass through a cleaning layer:

- Remove exact duplicates and identify near-duplicate content
- Remove empty records and extremely low-information content
- Remove spam, advertisements, and promotional content
- Normalize whitespace and text formatting
- Process Language: English and Hinglish/mixed processed normally. Very short text should not be discarded solely due to language uncertainty. Pure non-English preserved, tagged, and marked `extraction_status = unsupported_language` to exclude from AI extraction.
- **Privacy Filtering**: SOURCE ACCOUNT IDENTIFIERS (reviewer names, Reddit usernames, YouTube commenter names/channels) must be removed immediately during ingestion. TEXT-LEVEL PII must be masked before text is sent to LLMs, embeddings, API, or UI.
- Do NOT automatically remove useful contextual city/region mentions (e.g., "Bangalore").
- Preserve cleaned and original versions separately where necessary (original versions remain restricted/local).

> Cleaning rules should not remove useful behavioral evidence simply because a review is short, negative, informal, or grammatically incorrect.

---

## Relevance Classification

Each conversation should be classified as:

```text
highly_relevant
somewhat_relevant
not_relevant
```

**Relevant conversations may contain evidence about:**

- Wishlist behavior, product shortlisting, purchase hesitation
- Product comparison, fit or sizing, product quality
- Styling, occasion suitability, review usage
- Trust, social validation, price or timing, availability
- Delivery concerns, returns or exchanges affecting a decision
- External research, decision postponement, purchase abandonment

**Examples of likely irrelevant records:**

- App crashes with no shopping-decision context
- Login problems
- Generic customer-service complaints
- Generic positive reviews
- Payment failures unrelated to product decision-making

> Relevance should be determined by usefulness for the research objective, not by sentiment.

---

## Unit of Analysis

The primary unit of analysis is:

> **An evidence-backed behavioral observation extracted from a public user conversation.**

A single conversation may produce multiple useful observations.

**Example:**

```text
"I saved three dresses but still haven't ordered because I'm unsure
about sizing. I searched YouTube for haul videos to see how they look
on real people."
```

**Possible observations extracted:**

```text
Wishlist behavior     → Comparison shortlist
Purchase barrier      → Fit/size uncertainty
Information need      → Real-life fit information
Workaround            → YouTube haul videos
External behavior     → Research outside the shopping platform
Decision outcome      → Purchase postponed
```

---

## Structured Research Observation Schema

Each observation should include:

```json
{
  "observation_id": "unique_id",
  "source_record_id": "raw_record_id",
  "source": "play_store | app_store | reddit | youtube | product_review | community | other",
  "source_url": "public_source_url_if_available",
  "is_myntra_specific": true,
  "journey_stage": "browse | wishlist_add | wishlist_revisit | comparison | cart | checkout | post_purchase | unknown",
  "wishlist_intent": "genuine_purchase | price_tracking | comparison | inspiration | bookmarking | aspirational | occasion_planning | unknown",
  "purchase_intent": "high | medium | low | unknown",
  "product_category": "category_if_observable",
  "theme": "recurring_theme_if_observable",
  "primary_barrier": "barrier_category",
  "secondary_barriers": [],
  "root_cause": "underlying_reason_if_observable",
  "uncertainty": "what_the_user_is_unsure_about",
  "information_needed": "information_the_user_is_seeking",
  "workaround": "current_user_workaround",
  "external_platform_used": "youtube | instagram | google | reddit | friends_family | offline_store | competitor | none | unknown",
  "alternative_considered": "true | false | unknown",
  "occasion": "occasion_if_observable",
  "decision_outcome": "purchased | postponed | abandoned | still_considering | returned | unknown",
  "segment_signal": "segment_if_observable",
  "evidence_quote": "verbatim_supporting_text",
  "ai_confidence": 0.0,
  "model_id": "classification_or_extraction_model_id",
  "prompt_version": "v1",
  "created_in_pipeline_run_id": "run_id"
}
```

> Note: `created_in_pipeline_run_id` denotes creation provenance. Current-run membership is determined via `run_records`. Current thresholds (e.g., relevance confidence) are INITIAL CONFIGURABLE DEFAULTS, which should be calibrated against golden sets and manual review.

---

## Research Taxonomies

### Wishlist Intent Taxonomy

| Intent | Description |
|---|---|
| Genuine Purchase Intent | User intends to buy soon |
| Price Tracking | Waiting for a price drop |
| Comparison Shortlist | Comparing with other options |
| Inspiration | Saving for style ideas |
| Bookmarking | Saving to revisit later |
| Aspirational Saving | Saving without current intent to buy |
| Occasion Planning | Saving for a future event |
| Unknown | Intent not observable |

### Purchase Barrier Taxonomy

| Barrier | Description |
|---|---|
| Fit / Size Uncertainty | Unsure about correct size |
| Quality Uncertainty | Unsure about product quality |
| Price / Timing Uncertainty | Waiting for better price or timing |
| Comparison Difficulty | Struggling to choose between options |
| Styling Uncertainty | Unsure how to style the product |
| Occasion Suitability | Unsure if appropriate for the occasion |
| Review Trust Gap | Insufficient or untrustworthy reviews |
| Social Validation | Seeking external validation |
| Availability | Product out of stock |
| Delivery Concern | Concerns about shipping |
| Return / Exchange Concern | Concerns about returns or exchanges |
| Product / Platform Trust | Trust in product or platform |
| Other / Unknown | Not categorized |

### Behavioral Segment Signals

| Segment | Description |
|---|---|
| High-Intent Deliberator | Strong intent but careful decision-maker |
| Fit-Anxious Shopper | Primarily hesitates due to sizing concerns |
| Comparison Shopper | Evaluates multiple alternatives |
| Occasion Shopper | Shopping for specific events |
| Price Watcher | Waiting for price drops or sales |
| Research-Heavy Shopper | Conducts extensive pre-purchase research |
| Casual Bookmarker | Saves products without strong purchase intent |
| Quality-Conscious Shopper | Prioritizes product quality |
| Unknown | Segment not observable |

> Segments should only be assigned when supported by evidence. The system should not infer unsupported demographic characteristics.

---

## Theme Grouping & Emergent Discovery

Relevant behavioral observations should be grouped into recurring themes using **TWO complementary mechanisms**:

1. **Structured Theme Classification**: Classify observations using the initial taxonomy where supported.
2. **Emergent Pattern Discovery**: Run clustering/pattern discovery over the broader observation corpus to surface unexpected behaviors, even if an observation belongs to an existing theme.

An observation may belong to an existing theme, contribute to an emergent pattern, or both. Predefined taxonomies are organizational frameworks, not conclusions. All emergent patterns must remain traceable to evidence.

**Possible themes include:**

- Fit and sizing uncertainty
- Product quality uncertainty
- Comparison difficulty
- Price or purchase-timing hesitation
- Styling uncertainty
- Occasion suitability
- Review trust gap
- Social validation
- Availability concerns
- Delivery, return, or exchange concerns

> Themes should be derived from the analyzed data and should evolve when new patterns emerge. Thresholds (like minimum observations per theme) are initial configurable defaults.

For each theme, the Discovery Pulse Dashboard should show:

- Number of supporting observations and percentage of relevant observations
- Common root causes and associated wishlist intents
- Associated purchase intent and affected behavioral segments
- Recurring uncertainties, information needs, and workarounds
- External research behaviors and representative user quotes
- Source distribution and AI confidence / evidence quality

---

## Themes vs Opportunity Areas

| Concept | Definition |
|---|---|
| **Theme** | A recurring pattern found across user conversations |
| **Opportunity Area** | A recurring unresolved user problem or unmet need worth investigating |

> Themes should not automatically be treated as opportunity areas.

**Example:**

```text
Theme:
Fit and sizing

Observed Pattern:
Users repeatedly hesitate because they are uncertain which size will fit.

Root Cause:
Available sizing information does not provide enough confidence for the user's specific situation.

Possible Opportunity Area:
Users with purchase intent need greater confidence about how a shortlisted product is likely to fit
before deciding whether to purchase it.
```

---

## Opportunity Areas

The Discovery Engine should convert recurring unresolved problems into potential opportunity areas.

An opportunity area may qualify when evidence shows:
1. Recurring evidence (minimum observations threshold is an initial configurable default)
2. Meaningful shopping/purchase intent
3. Recurring unresolved friction (e.g., uncertainty, hesitation, comparison difficulty, fit confidence gap, external research behavior, workaround behavior)
4. Sufficient supporting evidence.

Known outcomes such as `postponed`, `abandoned`, or `still_considering` increase opportunity confidence but are NOT mandatory. `decision_outcome = unknown` is valid, as public conversations frequently do not reveal the final purchase outcome. If evidence overwhelmingly shows successful resolution/purchase with no remaining problem, opportunity confidence should decrease.

An opportunity area must represent a **USER PROBLEM OR UNMET NEED**, not a product solution (e.g. do not suggest "reminder system" or "discount").

```text
Incorrect:
Build an AI size recommendation feature.

Correct:
Users with purchase intent remain uncertain about which size will fit because available sizing
information does not provide enough confidence.
```

> The engine should avoid prematurely recommending features.

---

## Opportunity Quantification

For each opportunity area, calculate:

- Supporting observation count and percentage of relevant observations
- Source distribution (Myntra-specific vs category-level)
- Associated wishlist intent, purchase intent, and behavioral segments
- Recurring root causes, uncertainties, information needs, and workarounds
- External research behavior and evidence confidence

> Quantification must refer **only** to the analyzed dataset.

```text
Correct:   "23% of relevant observations in the analyzed dataset mention fit uncertainty."
Incorrect: "23% of Myntra users experience fit uncertainty."
```

The public dataset is a discovery sample and should not be represented as statistically representative of Myntra's entire user population.

---

## Grounded Retrieval Flow

The Query Interface should use the analyzed evidence corpus rather than relying only on semantic search across raw reviews.

```text
User Question
      ↓
Understand Research Intent
      ↓
Apply Structured Filters When Relevant
      ↓
Retrieve Relevant Observations
      ↓
Retrieve Supporting Source Evidence
      ↓
Generate Grounded Synthesis
      ↓
Answer + Evidence + Caveats
```

**Possible structured filters:**

- Wishlist intent, purchase intent, purchase barrier
- Theme, behavioral segment, source, product category
- Journey stage, Myntra-specific vs category-level evidence

---

## External Research Behavior

The engine should identify where users go when the shopping platform does not provide enough information:

- YouTube reviews and haul videos
- Google search
- Reddit and fashion communities
- Instagram and influencers / creators
- Friends and family
- Offline stores
- Competitor shopping platforms
- Brand websites

> The purpose is to understand what information users still need after discovering a product they like.

---

## Privacy Requirements

The system must follow a consistent raw data policy for privacy:

**SOURCE ACCOUNT IDENTIFIERS:**
Remove immediately during ingestion:
- reviewer names, Reddit usernames, YouTube commenter names, channel identifiers, and similar account-level identity metadata.

**TEXT-LEVEL PII:**
Mask before text is sent to LLM classification, extraction, embeddings, vector store, UI, or exports:
- email, phone, order ID, usernames/social handles, precise addresses, direct personal identifiers.

**Do NOT automatically remove useful contextual city/region mentions.** (e.g., "I wore this to a wedding in Bangalore" should retain Bangalore unless it forms part of a precise/private address).

If untouched source text is temporarily retained for engineering/debugging:
- keep it local/restricted
- exclude it from Git
- do not expose it through API/UI/export
- do not send it to AI models
- make it deletable

> The research/evidence dataset used downstream should always use masked text.

---

## Data Constraints

Use only legally accessible public conversations or permitted public exports.

**Do not use:**

- Private Myntra data or login-protected user data
- Private communities
- Data obtained by bypassing access controls
- Scraping methods that violate source restrictions
- Fabricated reviews or synthetic quotes presented as real evidence

> Synthetic data may be used for engineering tests but must never be mixed with real research findings.

---

## AI Reliability Requirements

The AI system must:

- Preserve source evidence
- Use structured outputs where appropriate
- Allow uncertain values
- Avoid inventing motivations, outcomes, quotes, counts, or percentages
- Distinguish evidence from interpretation
- Store confidence information
- Allow inspection of extracted observations

If information cannot be inferred reliably, use values such as:

```text
unknown
not_observable
insufficient_evidence
```

> It is preferable to leave information unknown rather than fabricate an interpretation.

---

## Non-Goals

The system is **not** intended to:

- Build the final wishlist product solution
- Automatically modify Myntra
- Perform only sentiment analysis or produce only a generic review summary
- Optimize App Store or Play Store ratings
- Treat every wishlist addition as genuine purchase intent
- Infer unsupported demographic characteristics
- Make claims about all Myntra users from a public conversation sample
- Generate fake user evidence or statistics
- Treat feature requests as equivalent to user problems
- Replace primary user research

> Price-related hesitation may still be analyzed as a user behavior, but the engine should focus on discovering the underlying problem rather than automatically recommending discounts or monetary incentives.

---

## Expected Deliverables

### 1. Discovery Pulse Dashboard

A usable dashboard that allows a Product Manager to:

- Understand the analyzed dataset
- Inspect recurring themes, wishlist motivations, and recurring purchase barriers
- Understand user uncertainties, information needs, and workarounds
- Compare behavioral segments
- Explore potential opportunity areas
- Inspect supporting evidence

### 2. Grounded Query Interface

A natural-language interface allowing Product Managers to investigate the analyzed evidence, with responses grounded in retrieved observations and supporting source evidence.

### 3. Evidence Explorer

Allows inspection of evidence supporting important findings, displaying:

- Source, supporting quote, wishlist intent, purchase barrier
- Theme, root cause, uncertainty, information needed
- Workaround, behavioral segment, source link where available

### 4. Structured Research Outputs

The pipeline should generate reviewable outputs containing:

- Raw conversations, cleaned conversations, relevance classification
- Extracted observations, themes, barriers, wishlist intents
- Uncertainties, information needs, workarounds, behavioral segments
- Evidence references, AI confidence

> Intermediate outputs should be stored in reviewable files where useful so the data and AI transformations can be manually inspected.

---

## Success Criteria

The system will be considered successful if it can:

- Analyze meaningful volumes of public user conversations
- Import the most recent 12 weeks of Myntra App Store and Play Store reviews
- Filter irrelevant feedback
- Group relevant observations into useful recurring themes
- Identify different wishlist motivations
- Distinguish stronger purchase intent from casual saving where evidence permits
- Identify recurring purchase barriers, unresolved uncertainties, and current user workarounds
- Identify external research behavior
- Compare patterns across behavioral segments
- Discover implicit unmet needs
- Identify problems users describe even when they do not request a feature
- Distinguish themes from potential opportunity areas
- Quantify recurring patterns within the analyzed dataset where possible
- Preserve traceable supporting evidence
- Surface useful insights through the Discovery Pulse
- Answer evidence-backed research questions through the Query Interface
- Avoid fabricated evidence and unsupported claims

---

## Definition of Done

The system is complete when:

1. Public user conversations can be collected or imported
2. Myntra App Store and Play Store reviews from the most recent 12 weeks are available for analysis
3. Raw data is stored in a consistent format
4. Data is cleaned and normalized
5. Duplicate and privacy-risk records are handled
6. Relevant conversations are identified
7. Structured behavioral observations are extracted
8. Initial research taxonomies can be reviewed and refined
9. Recurring themes can be identified and grouped
10. Root causes and unmet needs can be explored
11. Implicit unmet needs can be investigated through natural-language queries
12. Themes can be distinguished from opportunity areas
13. Opportunity areas can be generated from recurring unresolved needs
14. Patterns can be quantified within the analyzed dataset
15. Supporting evidence can be inspected
16. A Discovery Pulse Dashboard presents the main findings
17. An Evidence Explorer provides traceability to user evidence
18. A Grounded Query Interface answers evidence-backed research questions
19. Intermediate and final outputs can be manually reviewed
20. The system clearly communicates uncertainty, evidence quality, and dataset limitations

---

## Summary

The goal is to build an **AI-powered product discovery system** that converts public Myntra and online fashion-shopping conversations into structured, evidence-backed research insights.

The final product combines:

> **Discovery Pulse Dashboard + Evidence Explorer + Grounded Query Interface**

The system should help move from:

```text
Thousands of Unstructured User Conversations
                ↓
Relevant Behavioral Evidence
                ↓
Recurring Themes
                ↓
Wishlist Motivations
                ↓
Purchase Barriers
                ↓
Unresolved Uncertainties
                ↓
Information Needs
                ↓
Current Workarounds
                ↓
Behavioral Patterns
                ↓
Implicit Unmet Needs
                ↓
Potential Opportunity Areas
```

The value of the system is not simply summarizing what users say.

Its value is helping Product Managers understand:

> **What users are doing, why they are hesitating, what information they are missing, how they currently solve the problem themselves, and which recurring unmet needs deserve deeper investigation.**
