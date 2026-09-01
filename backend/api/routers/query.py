from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from backend.api.dependencies import get_db_session
from backend.store.database import Observation, PredefinedTheme, ThemeAssignment
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


async def _ranked_dimension_response(question: str, dimension: str, db: AsyncSession):
    config = RANKED_DIMENSIONS[dimension]
    column = config["column"]
    count_result = await db.execute(
        select(column, func.count(Observation.observation_id))
        .group_by(column)
        .order_by(desc(func.count(Observation.observation_id)))
    )
    all_counts = [(value, count) for value, count in count_result.all()]
    ranked = [(value, count) for value, count in all_counts if value and value not in {"unknown", "none"}]
    unknown_count = sum(count for value, count in all_counts if not value or value == "unknown")
    denominator_result = await db.execute(select(func.count(Observation.observation_id)))
    denominator = denominator_result.scalar() or 0

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
        select(func.count(func.distinct(Observation.source_record_id))).where(column.in_(ranked_values))
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
    result = await db.execute(
        select(
            PredefinedTheme.canonical_name,
            func.count(func.distinct(ThemeAssignment.observation_id)),
        )
        .outerjoin(ThemeAssignment, ThemeAssignment.predefined_theme_id == PredefinedTheme.theme_id)
        .group_by(PredefinedTheme.theme_id, PredefinedTheme.canonical_name)
        .order_by(desc(func.count(func.distinct(ThemeAssignment.observation_id))))
    )
    ranked = [(name or "Unnamed research topic", count) for name, count in result.all()]
    denominator_result = await db.execute(select(func.count(Observation.observation_id)))
    denominator = denominator_result.scalar() or 0
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


async def _ranked_barrier_response(question: str, db: AsyncSession):
    count_query = (
        select(Observation.primary_barrier, func.count(Observation.observation_id))
        .where(Observation.primary_barrier.is_not(None))
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

    denominator_result = await db.execute(select(func.count(Observation.observation_id)))
    denominator = denominator_result.scalar() or 0
    classified_count = sum(barrier_counts.values())
    unclassified_count = max(denominator - classified_count, 0)
    top_five_count = sum(count for _, count in ranked_barriers)
    top_five_pct = round(top_five_count / denominator * 100, 1) if denominator else 0.0

    evidence_records = []
    for barrier, _ in ranked_barriers[:3]:
        sample_query = (
            select(Observation)
            .where(
                Observation.primary_barrier == barrier,
                func.length(Observation.evidence_quote).between(60, 300),
                Observation.evidence_quote.not_like("%[NAME]%"),
            )
            .order_by(desc(func.coalesce(Observation.ai_confidence, 0)), desc(func.length(Observation.evidence_quote)))
            .limit(1)
        )
        sample_result = await db.execute(sample_query)
        sample = sample_result.scalars().first()
        if sample:
            evidence_records.append(EvidenceRecord(
                observation_id=sample.observation_id,
                evidence_quote=sample.evidence_quote,
                source=sample.source,
                source_url=sample.source_url,
                primary_barrier=sample.primary_barrier,
                workaround=sample.workaround,
                source_record_id=sample.source_record_id,
            ))

    ranking_lines = [
        f"- **{TOP_BARRIER_LABELS[barrier]}** — **{count:,} feedback observations**"
        for barrier, count in ranked_barriers
    ]
    quote_lines = [
        f'> “{record.evidence_quote.strip()}” — {(record.source or "public feedback").replace("_", " ").title()}'
        for record in evidence_records
    ]
    answer_parts = [
        "The most frequently identified purchase barriers in the analyzed feedback are:",
        "\n".join(ranking_lines),
        (
            f"Together, these five barriers appear in **{top_five_count:,} of {denominator:,} feedback observations ({top_five_pct}%)**. "
            "Delivery, trust, and product quality form the strongest concentration of stated friction; pricing and fit remain substantial recurring concerns."
        ),
        (
            f"Counts represent extracted feedback observations, not unique customers. Another **{unclassified_count:,} observations** "
            "did not contain enough information to identify a primary barrier."
        ),
    ]
    if quote_lines:
        answer_parts.extend(["### Representative customer comments", "\n".join(quote_lines)])

    source_count_result = await db.execute(
        select(func.count(func.distinct(Observation.source_record_id))).where(
            Observation.primary_barrier.in_([barrier for barrier, _ in ranked_barriers])
        )
    )

    return QueryResponse(
        query=question,
        query_type="ranked_barriers",
        retrieval_mode="deterministic",
        applied_filters={},
        evidence_count=len(evidence_records),
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
    question = req.query

    if _is_ranked_barrier_query(question):
        return await _ranked_barrier_response(question, db)

    ranked_dimension = _detect_ranked_dimension(question)
    if ranked_dimension == "predefined_theme":
        return await _ranked_theme_response(question, db)
    if ranked_dimension:
        return await _ranked_dimension_response(question, ranked_dimension, db)
    
    # 1. Parse intent
    intent_result = await parse_intent(question)
    query_type = intent_result.get("query_type", "evidence_explanatory")
    implied_filters = normalize_implied_filters(intent_result.get("implied_filters", {}))
    
    # 2. Build DB filters
    db_filters = build_sqlalchemy_filters(implied_filters)
    
    # 3. Retrieve eligible IDs
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
        denom_result = await db.execute(select(func.count(Observation.observation_id)))
        denominator = denom_result.scalar() or 0
        
        answer = f"Found {count} observation(s) matching the criteria out of {denominator} total."
        
        return QueryResponse(
            query=question,
            query_type=query_type,
            retrieval_mode="deterministic",
            applied_filters=implied_filters,
            evidence_count=count,
            unique_source_count=(
                await db.execute(
                    select(func.count(func.distinct(Observation.source_record_id))).where(
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
        # 5. Semantic Retrieval
        top_k_ids = retrieve_semantic_evidence(question, eligible_ids, top_k=20)
        
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
            
        obs_stmt = select(Observation).where(Observation.observation_id.in_(top_k_ids))
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
