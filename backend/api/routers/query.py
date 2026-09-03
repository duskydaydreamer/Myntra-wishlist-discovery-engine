from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import re

from backend.api.dependencies import get_db_session
from backend.api.resolvers import get_latest_successful_run
from backend.store.database import RunRecord, Observation, PredefinedTheme, ThemeAssignment
from backend.research_rules import DATASET_SCOPE_CAVEAT
from backend.query.intent_parser import parse_intent
from backend.query.filter_builder import build_sqlalchemy_filters, normalize_implied_filters
from backend.query.retriever import retrieve_semantic_evidence
from backend.query.synthesizer import synthesize_answer

router = APIRouter()

TOP_BARRIER_LABELS = {
    "delivery": "Delivery problems",
    "trust": "Trust concerns",
    "quality": "Product-quality concerns",
    "price": "Pricing concerns",
    "fit": "Fit and sizing concerns",
}

RANKING_TERMS = ("top", "most common", "main", "leading", "biggest", "frequent", "frequently")

READABLE_VALUE_LABELS = {
    "bought": "Purchase completed",
    "abandoned": "Purchase abandoned",
    "delayed": "Decision delayed",
    "switched": "Switched to another option",
    "discovery": "Discovery",
    "evaluation": "Evaluation",
    "purchase": "Purchase",
    "post_purchase": "After purchase",
}

RANKED_DIMENSIONS = {
    "decision_outcome": {
        "terms": ("outcome", "outcomes", "decision result", "decision results"),
        "column": Observation.decision_outcome,
        "title": "The most frequently identified shopping outcomes are:",
        "labels": {
            "bought": "Purchase completed",
            "abandoned": "Purchase abandoned",
            "delayed": "Decision delayed",
            "switched": "Switched to another option",
        },
    },
    "wishlist_intent": {
        "terms": ("wishlist intent", "wishlist intents", "wishlist motivation", "wishlist motivations"),
        "column": Observation.wishlist_intent,
        "title": "The most frequently identified wishlist motivations are:",
        "labels": {
            "genuine_purchase": "Saving with genuine purchase intent",
            "comparison_shortlist": "Comparison or shortlist",
            "inspiration": "Inspiration",
            "price_tracking": "Tracking price",
            "bookmarking": "Bookmarking",
            "aspirational_saving": "Aspirational saving",
            "occasion_planning": "Planning for an occasion",
        },
    },
    "purchase_intent": {
        "terms": ("purchase intent", "purchase intents", "buying intent", "buying intents"),
        "column": Observation.purchase_intent,
        "title": "The most frequently identified purchase-intent levels are:",
        "labels": {"high": "High intent", "low": "Low intent", "none": "No purchase intent"},
    },
    "journey_stage": {
        "terms": ("journey stage", "journey stages", "shopping stage", "shopping stages"),
        "column": Observation.journey_stage,
        "title": "The most frequently identified shopping stages are:",
        "labels": {
            "discovery": "Discovery",
            "evaluation": "Evaluation",
            "purchase": "Purchase",
            "post_purchase": "After purchase",
        },
    },
    "source": {
        "terms": ("source", "sources", "channel", "channels"),
        "column": Observation.source,
        "title": "The analyzed evidence is distributed across these public channels:",
        "labels": {
            "play_store": "Play Store",
            "youtube": "YouTube",
            "app_store": "App Store",
            "reddit": "Reddit",
        },
    },
}


def _is_ranked_barrier_query(question: str) -> bool:
    normalized = " ".join(question.lower().split())
    ranking_terms = ("top", "most common", "main", "leading", "biggest", "frequent")
    issue_terms = ("issue", "issues", "problem", "problems", "barrier", "barriers")
    return any(term in normalized for term in ranking_terms) and any(term in normalized for term in issue_terms)


def _detect_ranked_dimension(question: str) -> Optional[str]:
    normalized = " ".join(question.lower().split())
    if not any(term in normalized for term in RANKING_TERMS):
        return None
    for dimension, config in RANKED_DIMENSIONS.items():
        if any(term in normalized for term in config["terms"]):
            return dimension
    if any(term in normalized for term in ("theme", "themes", "topic", "topics")):
        return "predefined_theme"
    return None


async def _current_observation_count(
    db: AsyncSession,
    run_id: str,
    extra_filters: Optional[List[Any]] = None,
) -> int:
    statement = (
        select(func.count(func.distinct(Observation.observation_id)))
        .select_from(Observation)
        .join(RunRecord, RunRecord.raw_record_id == Observation.source_record_id)
        .where(RunRecord.pipeline_run_id == run_id)
    )
    if extra_filters:
        statement = statement.where(*extra_filters)
    return (await db.execute(statement)).scalar() or 0


def _good_quote_filters() -> List[Any]:
    return [
        func.length(Observation.evidence_quote).between(60, 360),
        Observation.evidence_quote.not_like("%[NAME]%"),
        Observation.evidence_quote.not_like("%REGION_RESTRICTED%"),
    ]


async def _representative_records(
    db: AsyncSession,
    run_id: str,
    filters: List[Any],
    limit: int = 3,
) -> List["EvidenceRecord"]:
    result = await db.execute(
        select(Observation)
        .join(RunRecord, RunRecord.raw_record_id == Observation.source_record_id)
        .where(RunRecord.pipeline_run_id == run_id, *filters, *_good_quote_filters())
        .order_by(
            desc(func.coalesce(Observation.ai_confidence, 0)),
            desc(func.length(Observation.evidence_quote)),
        )
        .limit(limit)
    )
    return [
        EvidenceRecord(
            observation_id=item.observation_id,
            evidence_quote=item.evidence_quote,
            source=item.source,
            source_url=item.source_url,
            primary_barrier=item.primary_barrier,
            workaround=item.workaround,
            source_record_id=item.source_record_id,
        )
        for item in result.scalars().all()
    ]


def _quote_lines(records: List["EvidenceRecord"]) -> List[str]:
    return [
        f'> “{record.evidence_quote.strip()}” — {(record.source or "public feedback").replace("_", " ").title()}'
        for record in records
    ]


def _normalize_information_need(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    if not normalized or normalized in {"unknown", "none", "null", "n a"}:
        return None
    categories = (
        ("Product link or where to buy", ("link", "where to buy", "where to purchase")),
        ("Size and fit details", ("size", "sizing", "fit", "height", "measurement", "inseam", "length", "waist", "chest")),
        ("Price and availability", ("price", "cost", "discount", "sale", "availability", "available", "stock", "budget")),
        ("Order, refund or delivery updates", ("refund", "return status", "exchange status", "delivery status", "order status")),
        ("Styling or product recommendations", ("style", "outfit", "look", "occasion", "recommendation", "how to wear", "pairing")),
        ("Material and product details", ("material", "fabric", "colour", "color", "stitch", "pocket", "specification", "product detail")),
        ("Brand, seller or authenticity details", ("brand", "seller", "authentic", "original")),
        ("Quality and review information", ("quality", "review", "rating")),
    )
    for label, terms in categories:
        if any(term in normalized for term in terms):
            return label
    return None


def _lexical_fallback_ids(question: str, observations: List[Observation], limit: int = 20) -> List[str]:
    stop_words = {
        "what", "which", "where", "when", "why", "how", "are", "the", "and", "for",
        "from", "with", "this", "that", "users", "user", "shoppers", "myntra", "report",
        "evidence", "show", "does", "do", "before", "after", "about",
    }
    tokens = {
        token for token in re.findall(r"[a-z0-9]+", question.lower())
        if len(token) > 2 and token not in stop_words
    }
    if not tokens:
        return [item.observation_id for item in observations[:limit]]

    scored = []
    for item in observations:
        searchable = " ".join(str(value or "") for value in (
            item.evidence_quote, item.primary_barrier, item.uncertainty,
            item.information_needed, item.root_cause, item.workaround, item.topic,
        )).lower()
        score = sum(1 for token in tokens if token in searchable)
        if score:
            scored.append((score, len(item.evidence_quote or ""), item.observation_id))
    scored.sort(reverse=True)
    return [observation_id for _, _, observation_id in scored[:limit]]


async def _ranked_dimension_response(question: str, dimension: str, db: AsyncSession):
    run = await get_latest_successful_run(db)
    config = RANKED_DIMENSIONS[dimension]
    column = config["column"]
    count_result = await db.execute(
        select(column, func.count(Observation.observation_id))
        .select_from(Observation)
        .group_by(column)
        .order_by(desc(func.count(Observation.observation_id)))
    )
    all_counts = [(value, count) for value, count in count_result.all()]
    ranked = [(value, count) for value, count in all_counts if value and value != "unknown"]
    unknown_count = sum(count for value, count in all_counts if not value or value == "unknown")
    denominator = await _current_observation_count(db, run.run_id)

    labels = config["labels"]
    lines = [
        f"- **{labels.get(value, value.replace('_', ' ').title())}** — **{count:,} observations**"
        for value, count in ranked[:8]
    ]
    answer_parts = [config["title"], "\n".join(lines)]
    if unknown_count:
        answer_parts.append(
            f"Another **{unknown_count:,} observations** did not contain enough information for this classification."
        )
    answer_parts.append(
        "Counts describe extracted evidence observations, not unique customers or population prevalence."
    )

    ranked_values = [value for value, _ in ranked]
    unique_records_result = await db.execute(
        select(func.count(func.distinct(Observation.source_record_id))).select_from(Observation).join(RunRecord, RunRecord.raw_record_id == Observation.source_record_id).where(RunRecord.pipeline_run_id == run.run_id, column.in_(ranked_values))
    )
    return QueryResponse(
        query=question,
        query_type=f"ranked_{dimension}",
        retrieval_mode="deterministic",
        applied_filters={},
        evidence_count=sum(count for _, count in ranked),
        unique_source_count=unique_records_result.scalar() or 0,
        dataset_scope_caveat=DATASET_SCOPE_CAVEAT,
        answer="\n\n".join(answer_parts),
        evidence=[],
        denominator=denominator,
        denominator_definition="Total extracted evidence observations",
        denominator_scope="global",
    )


async def _ranked_theme_response(question: str, db: AsyncSession):
    run = await get_latest_successful_run(db)
    result = await db.execute(
        select(
            PredefinedTheme.canonical_name,
            func.count(func.distinct(ThemeAssignment.observation_id)),
        )
        .outerjoin(ThemeAssignment, ThemeAssignment.predefined_theme_id == PredefinedTheme.theme_id).outerjoin(Observation, Observation.observation_id == ThemeAssignment.observation_id).outerjoin(RunRecord, RunRecord.raw_record_id == Observation.source_record_id).where(True)
        .group_by(PredefinedTheme.theme_id, PredefinedTheme.canonical_name)
        .order_by(desc(func.count(func.distinct(ThemeAssignment.observation_id))))
    )
    ranked = [(name or "Unnamed research topic", count) for name, count in result.all()]
    denominator = await _current_observation_count(db, run.run_id)
    lines = [f"- **{name}** — **{count:,} matching observations**" for name, count in ranked[:8]]
    answer = "\n\n".join([
        "The research topics with the most semantic matches are:",
        "\n".join(lines),
        (
            "An observation may match more than one topic. These are semantic topic assignments, "
            "not problem counts or unique customers."
        ),
    ])
    return QueryResponse(
        query=question,
        query_type="ranked_predefined_themes",
        retrieval_mode="deterministic",
        applied_filters={},
        evidence_count=sum(count for _, count in ranked),
        unique_source_count=denominator,
        dataset_scope_caveat=DATASET_SCOPE_CAVEAT,
        answer=answer,
        evidence=[],
        denominator=denominator,
        denominator_definition="Total extracted evidence observations",
        denominator_scope="global",
    )


async def _ranked_barrier_response(
    question: str,
    db: AsyncSession,
    extra_filters: Optional[List[Any]] = None,
    title: Optional[str] = None,
    applied_filters: Optional[Dict[str, List[str]]] = None,
):
    run = await get_latest_successful_run(db)
    extra_filters = extra_filters or []
    count_query = (
        select(Observation.primary_barrier, func.count(Observation.observation_id))
        .select_from(Observation)
        .join(RunRecord, RunRecord.raw_record_id == Observation.source_record_id)
        .where(
            RunRecord.pipeline_run_id == run.run_id,
            Observation.primary_barrier.is_not(None),
            *extra_filters,
        )
        .group_by(Observation.primary_barrier)
        .order_by(desc(func.count(Observation.observation_id)))
    )
    count_result = await db.execute(count_query)
    barrier_counts = {
        barrier: count for barrier, count in count_result.all()
        if barrier and barrier not in {"unknown", "none"}
    }
    ranked_barriers = sorted(
        ((barrier, barrier_counts.get(barrier, 0)) for barrier in TOP_BARRIER_LABELS),
        key=lambda item: item[1],
        reverse=True,
    )
    top_nonzero = [(barrier, count) for barrier, count in ranked_barriers if count > 0]

    denominator = await _current_observation_count(db, run.run_id, extra_filters)
    classified_count = sum(barrier_counts.values())
    unclassified_count = max(denominator - classified_count, 0)
    top_five_count = sum(count for _, count in ranked_barriers)
    top_five_pct = round(top_five_count / denominator * 100, 1) if denominator else 0.0

    evidence_records: List[EvidenceRecord] = []
    for barrier, _ in top_nonzero[:3]:
        evidence_records.extend(
            await _representative_records(
                db,
                run.run_id,
                [Observation.primary_barrier == barrier, *extra_filters],
                limit=1,
            )
        )

    ranking_lines = [
        f"- **{TOP_BARRIER_LABELS[barrier]}** — **{count:,} feedback observations**"
        for barrier, count in top_nonzero
    ]
    quote_lines = _quote_lines(evidence_records)
    summary = ""
    if top_nonzero:
        summary = (
            f"**{TOP_BARRIER_LABELS[top_nonzero[0][0]]}** appears most often in this scope"
            + (
                f", followed by **{TOP_BARRIER_LABELS[top_nonzero[1][0]]}**."
                if len(top_nonzero) > 1 else "."
            )
        )
    answer_parts = [
        title or "The most frequently identified purchase barriers in the analyzed feedback are:",
        "\n".join(ranking_lines) if ranking_lines else "No primary barrier was identified in the current analysis.",
        summary,
        f"Together, these barriers appear in **{top_five_count:,} of {denominator:,} feedback observations ({top_five_pct}%)**.",
        (
            f"Counts represent extracted feedback observations, not unique customers. Another **{unclassified_count:,} observations** "
            "did not contain enough information to identify a primary barrier."
        ),
    ]
    if quote_lines:
        answer_parts.extend(["### Representative customer comments", "\n".join(quote_lines)])

    source_count_result = await db.execute(
        select(func.count(func.distinct(Observation.source_record_id))).select_from(Observation).join(RunRecord, RunRecord.raw_record_id == Observation.source_record_id).where(RunRecord.pipeline_run_id == run.run_id,
            Observation.primary_barrier.in_([barrier for barrier, _ in ranked_barriers]),
            *extra_filters,
        )
    )

    return QueryResponse(
        query=question,
        query_type="ranked_barriers",
        retrieval_mode="deterministic",
        applied_filters=applied_filters or {},
        evidence_count=top_five_count,
        unique_source_count=source_count_result.scalar() or 0,
        dataset_scope_caveat=DATASET_SCOPE_CAVEAT,
        answer="\n\n".join(answer_parts),
        evidence=evidence_records,
    )


async def _barrier_focus_response(
    question: str,
    db: AsyncSession,
    barriers: List[str],
    title: str,
):
    run = await get_latest_successful_run(db)
    scope_filters = [Observation.primary_barrier.in_(barriers)]
    total = await _current_observation_count(db, run.run_id)
    matching = await _current_observation_count(db, run.run_id, scope_filters)

    barrier_result = await db.execute(
        select(Observation.primary_barrier, func.count(Observation.observation_id))
        .join(RunRecord, RunRecord.raw_record_id == Observation.source_record_id)
        .where(RunRecord.pipeline_run_id == run.run_id, *scope_filters)
        .group_by(Observation.primary_barrier)
        .order_by(desc(func.count(Observation.observation_id)))
    )
    barrier_counts = [(value, count) for value, count in barrier_result.all() if value]

    outcome_result = await db.execute(
        select(Observation.decision_outcome, func.count(Observation.observation_id))
        .join(RunRecord, RunRecord.raw_record_id == Observation.source_record_id)
        .where(
            RunRecord.pipeline_run_id == run.run_id,
            *scope_filters,
            Observation.decision_outcome.is_not(None),
            Observation.decision_outcome.notin_(["unknown", "none"]),
        )
        .group_by(Observation.decision_outcome)
        .order_by(desc(func.count(Observation.observation_id)))
    )
    outcomes = outcome_result.all()
    evidence_records = await _representative_records(db, run.run_id, scope_filters, limit=3)

    barrier_lines = [
        f"- **{TOP_BARRIER_LABELS.get(value, value.replace('_', ' ').title())}** — **{count:,} observations**"
        for value, count in barrier_counts
    ]
    outcome_lines = [
        f"- **{READABLE_VALUE_LABELS.get(value, value.replace('_', ' ').title())}** — **{count:,} observations**"
        for value, count in outcomes
    ]
    share = round(matching / total * 100, 1) if total else 0.0
    answer_parts = [
        title,
        "### What the data shows",
        "\n".join(barrier_lines),
        f"This signal appears in **{matching:,} of {total:,} analyzed observations ({share}%)**.",
    ]
    if outcome_lines:
        answer_parts.extend([
            "### What shoppers did next",
            "\n".join(outcome_lines),
            "These are associated outcomes in the same records; they do not prove that this issue alone caused the decision.",
        ])
    if evidence_records:
        answer_parts.extend(["### Representative customer comments", "\n".join(_quote_lines(evidence_records))])

    source_count_result = await db.execute(
        select(func.count(func.distinct(Observation.source_record_id)))
        .select_from(Observation)
        .join(RunRecord, RunRecord.raw_record_id == Observation.source_record_id)
        .where(RunRecord.pipeline_run_id == run.run_id, *scope_filters)
    )
    return QueryResponse(
        query=question,
        query_type="focused_evidence",
        retrieval_mode="deterministic",
        applied_filters={"primary_barrier": barriers},
        evidence_count=matching,
        unique_source_count=source_count_result.scalar() or 0,
        dataset_scope_caveat=DATASET_SCOPE_CAVEAT,
        answer="\n\n".join(part for part in answer_parts if part),
        evidence=evidence_records,
    )


async def _information_needs_response(question: str, db: AsyncSession):
    run = await get_latest_successful_run(db)
    result = await db.execute(
        select(Observation.information_needed, func.count(Observation.observation_id))
        .join(RunRecord, RunRecord.raw_record_id == Observation.source_record_id)
        .where(
            RunRecord.pipeline_run_id == run.run_id,
            Observation.information_needed.is_not(None),
            func.trim(Observation.information_needed) != "",
        )
        .group_by(Observation.information_needed)
    )
    aggregated: Dict[str, int] = {}
    for value, count in result.all():
        label = _normalize_information_need(value)
        if label:
            aggregated[label] = aggregated.get(label, 0) + count
    ranked = sorted(aggregated.items(), key=lambda item: (-item[1], item[0]))[:8]
    classified = sum(aggregated.values())
    total = await _current_observation_count(db, run.run_id)
    lines = [f"- **{label}** — **{count:,} observations**" for label, count in ranked]
    answer_parts = [
        "The clearest information needs stated in the analyzed feedback are:",
        "\n".join(lines) if lines else "No clearly stated information needs were found in the current analysis.",
        (
            f"These categories cover **{classified:,} of {total:,} observations**. "
            "Many comments describe an experience without explicitly stating what information was needed."
        ),
        "Counts represent feedback observations, not unique customers. Similar free-text requests were grouped into the labels above.",
    ]
    evidence_records = await _representative_records(
        db,
        run.run_id,
        [Observation.information_needed.is_not(None), func.trim(Observation.information_needed) != ""],
        limit=3,
    )
    if evidence_records:
        answer_parts.extend(["### Representative customer comments", "\n".join(_quote_lines(evidence_records))])
    source_count_result = await db.execute(
        select(func.count(func.distinct(Observation.source_record_id)))
        .select_from(Observation)
        .join(RunRecord, RunRecord.raw_record_id == Observation.source_record_id)
        .where(
            RunRecord.pipeline_run_id == run.run_id,
            Observation.information_needed.is_not(None),
            func.trim(Observation.information_needed) != "",
        )
    )
    return QueryResponse(
        query=question,
        query_type="ranked_information_needs",
        retrieval_mode="deterministic",
        applied_filters={},
        evidence_count=classified,
        unique_source_count=source_count_result.scalar() or 0,
        dataset_scope_caveat=DATASET_SCOPE_CAVEAT,
        answer="\n\n".join(answer_parts),
        evidence=evidence_records,
    )

class QueryRequest(BaseModel):
    query: str
    
class EvidenceRecord(BaseModel):
    observation_id: str
    evidence_quote: str
    source: Optional[str]
    source_url: Optional[str]
    primary_barrier: Optional[str]
    workaround: Optional[str]
    # Required by contract:
    source_record_id: Optional[str] = None
    theme_context: Optional[str] = None
    cluster_context: Optional[str] = None

class QueryResponse(BaseModel):
    query: str
    query_type: str
    retrieval_mode: str
    applied_filters: Dict[str, List[str]]
    evidence_count: int
    unique_source_count: int
    dataset_scope_caveat: str
    answer: str
    evidence: List[EvidenceRecord]
    
    # Optional deterministic fields
    numerator: Optional[int] = None
    denominator: Optional[int] = None
    denominator_definition: Optional[str] = None
    denominator_scope: Optional[str] = None

@router.post("", response_model=QueryResponse)
async def execute_query(req: QueryRequest, db: AsyncSession = Depends(get_db_session)):
    question = req.query.strip()
    normalized_question = " ".join(question.lower().replace("-", " ").split())

    if len(question) < 5:
        raise HTTPException(status_code=422, detail="Enter a question with at least five characters.")

    asks_high_intent_barriers = (
        ("high intent" in normalized_question or "ready to buy" in normalized_question)
        and any(term in normalized_question for term in ("barrier", "prevent", "stop", "not purchasing", "not buying"))
    )
    if asks_high_intent_barriers:
        return await _ranked_barrier_response(
            question,
            db,
            extra_filters=[Observation.purchase_intent == "high"],
            title="Among feedback with high purchase intent, the most frequently identified barriers are:",
            applied_filters={"purchase_intent": ["high"]},
        )

    if _is_ranked_barrier_query(question):
        return await _ranked_barrier_response(question, db)

    ranked_dimension = _detect_ranked_dimension(question)
    if ranked_dimension == "predefined_theme":
        return await _ranked_theme_response(question, db)
    if ranked_dimension:
        return await _ranked_dimension_response(question, ranked_dimension, db)

    asks_information_needs = (
        any(term in normalized_question for term in ("what information", "information do", "details do", "need to know", "look for before"))
        and any(term in normalized_question for term in ("buy", "buying", "purchase", "shopping", "product"))
    )
    if asks_information_needs:
        return await _information_needs_response(question, db)

    asks_fit = any(term in normalized_question for term in ("fit", "sizing", "size uncertainty", "which size"))
    if asks_fit:
        return await _barrier_focus_response(
            question,
            db,
            ["fit"],
            "Shoppers describe uncertainty about choosing the right size, understanding measurements, and knowing whether the delivered fit will match expectations.",
        )

    asks_delivery = any(term in normalized_question for term in ("delivery", "shipping", "return", "refund", "exchange"))
    if asks_delivery:
        return await _barrier_focus_response(
            question,
            db,
            ["delivery"],
            "Delivery-related friction includes late or cancelled orders, difficult returns or exchanges, delayed refunds, and weak support resolution.",
        )

    asks_price_or_trust = any(
        term in normalized_question
        for term in ("price", "pricing", "discount", "fee", "trust", "seller", "authentic", "fake")
    )
    if asks_price_or_trust:
        selected = []
        if any(term in normalized_question for term in ("price", "pricing", "discount", "fee")):
            selected.append("price")
        if any(term in normalized_question for term in ("trust", "seller", "authentic", "fake")):
            selected.append("trust")
        return await _barrier_focus_response(
            question,
            db,
            selected or ["price", "trust"],
            "The evidence connects purchase confidence with price clarity, offer consistency, seller reliability, and confidence that products are genuine.",
        )

    asks_wishlist_reason = (
        any(term in normalized_question for term in ("wishlist", "wishlisted", "save products", "saved products"))
        and any(term in normalized_question for term in ("why", "reason", "motivation", "purpose"))
    )
    if asks_wishlist_reason:
        return await _ranked_dimension_response(question, "wishlist_intent", db)
    
    # 1. Parse intent
    intent_result = await parse_intent(question)
    query_type = intent_result.get("query_type", "evidence_explanatory")
    implied_filters = normalize_implied_filters(intent_result.get("implied_filters", {}))
    
    # 2. Build DB filters
    db_filters = build_sqlalchemy_filters(implied_filters)
    
    # 3. Retrieve eligible IDs
    run = await get_latest_successful_run(db)
    stmt = select(Observation)
    if db_filters:
        stmt = stmt.where(*db_filters)
        
    result = await db.execute(stmt)
    eligible_obs = result.scalars().all()
    eligible_ids = {obs.observation_id for obs in eligible_obs}
    
    dataset_scope_caveat = (
        DATASET_SCOPE_CAVEAT
        + " This explanatory answer uses a maximum of 20 semantically retrieved observations, not a full-dataset ranking."
    )
    retrieval_mode = "semantic_only" if not implied_filters else "filtered_semantic"
    
    # 4. Handle query types
    if query_type == "count_filter":
        count = len(eligible_ids)
        
        # Calculate denominator (total canonical observations)
        denominator = await _current_observation_count(db, run.run_id)
        
        answer = f"Found {count} observation(s) matching the criteria out of {denominator} total."
        
        return QueryResponse(
            query=question,
            query_type=query_type,
            retrieval_mode="deterministic",
            applied_filters=implied_filters,
            evidence_count=count,
            unique_source_count=(
                await db.execute(
                    select(func.count(func.distinct(Observation.source_record_id))).select_from(Observation).join(RunRecord, RunRecord.raw_record_id == Observation.source_record_id).where(RunRecord.pipeline_run_id == run.run_id,
                        Observation.observation_id.in_(eligible_ids)
                    )
                )
            ).scalar() or 0,
            dataset_scope_caveat=dataset_scope_caveat,
            answer=answer,
            evidence=[],
            numerator=count,
            denominator=denominator,
            denominator_definition="Total canonical observations",
            denominator_scope="global"
        )
    else:
        # 5. Meaning-based retrieval, with a local lexical fallback for hosted
        # environments where the embedding model or vector store is unavailable.
        try:
            top_k_ids = retrieve_semantic_evidence(question, eligible_ids, top_k=20)
        except Exception:
            top_k_ids = _lexical_fallback_ids(question, eligible_obs, limit=20)
            retrieval_mode = "filtered_keyword" if implied_filters else "keyword_only"
        if not top_k_ids:
            top_k_ids = _lexical_fallback_ids(question, eligible_obs, limit=20)
            retrieval_mode = "filtered_keyword" if implied_filters else "keyword_only"
        
        # 6. Fetch actual records
        if not top_k_ids:
            return QueryResponse(
                query=question,
                query_type=query_type,
                retrieval_mode=retrieval_mode,
                applied_filters=implied_filters,
                evidence_count=0,
                unique_source_count=0,
                dataset_scope_caveat=dataset_scope_caveat,
                answer="No supporting evidence was found for the current filters.",
                evidence=[]
            )
            
        run = await get_latest_successful_run(db)
        obs_stmt = select(Observation).join(RunRecord, RunRecord.raw_record_id == Observation.source_record_id).where(RunRecord.pipeline_run_id == run.run_id, Observation.observation_id.in_(top_k_ids))
        obs_result = await db.execute(obs_stmt)
        observations = obs_result.scalars().all()
        
        # Maintain order from chroma
        obs_dict = {o.observation_id: o for o in observations}
        ordered_observations = [obs_dict[oid] for oid in top_k_ids if oid in obs_dict]
        
        evidence_dicts = []
        evidence_records_models = []
        for obs in ordered_observations:
            evidence_dicts.append({
                "evidence_quote": obs.evidence_quote,
                "primary_barrier": obs.primary_barrier,
                "workaround": obs.workaround,
                "source": obs.source
            })
            evidence_records_models.append(EvidenceRecord(
                observation_id=obs.observation_id,
                evidence_quote=obs.evidence_quote,
                source=obs.source,
                source_url=obs.source_url,
                primary_barrier=obs.primary_barrier,
                workaround=obs.workaround,
                source_record_id=obs.source_record_id
            ))
            
        # 7. Grounded Synthesis
        answer = await synthesize_answer(question, evidence_dicts)
        
        return QueryResponse(
            query=question,
            query_type=query_type,
            retrieval_mode=retrieval_mode,
            applied_filters=implied_filters,
            evidence_count=len(evidence_records_models),
            unique_source_count=len(set(o.source for o in ordered_observations if o.source)),
            dataset_scope_caveat=dataset_scope_caveat,
            answer=answer,
            evidence=evidence_records_models
        )
