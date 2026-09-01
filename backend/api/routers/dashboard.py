from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, text
from typing import List, Optional, Dict, Any
import json
import re

from backend.api.dependencies import get_db_session
from backend.api.schemas.dashboard import (
    DatasetStatsResponse, ThemeStat, ClusterStat, OpportunityStat,
    DistributionResponse, DistributionStat
)
from backend.store.database import (
    DatasetStats, PipelineRun, Theme, SemanticCluster, Phase4OpportunityArea, CleanedRecord,
    Observation, OpportunityObservation, OpportunityEvidence, RawRecord, ClassifiedRecord,
    ClusterMembership,
)
from backend.research_rules import OPPORTUNITY_RULES, PATTERN_EVIDENCE_ROLES

router = APIRouter()


def _representative_quote_score(opportunity_id: str, quote: Optional[str], source: Optional[str]) -> Optional[float]:
    """Score verbatim quotes for clarity and direct relevance without rewriting them."""
    if not quote:
        return None

    text_value = " ".join(quote.split())
    if not 70 <= len(text_value) <= 450 or re.search(r"\[[A-Z_]+\]", text_value):
        return None

    lowered = text_value.lower()
    if any(term in lowered for term in ("send your number", "google pay your number", "order for me")):
        return None

    latin_words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text_value)
    letters = [character for character in text_value if character.isalpha()]
    latin_letters = [character for character in text_value if character.isascii() and character.isalpha()]
    if len(latin_words) < 10 or not letters or len(latin_letters) / len(letters) < 0.9:
        return None

    rule = OPPORTUNITY_RULES.get(opportunity_id, {})
    relevant_terms = rule.get("representative_terms", ())
    problem_terms = rule.get("representative_problem_terms", ())
    term_hits = sum(1 for term in relevant_terms if term in lowered)
    problem_hits = sum(1 for term in problem_terms if term in lowered)
    if term_hits == 0 or problem_hits == 0:
        return None

    # Prefer specific, complete comments over either very short fragments or
    # unusually long comments that combine several unrelated complaints.
    ideal_length_score = max(0.0, 24.0 - abs(len(text_value) - 170) / 8)
    sentence_score = 8.0 if text_value.rstrip().endswith((".", "!", "?")) else 0.0
    source_score = 6.0 if source in {"play_store", "app_store", "reddit"} else 3.0
    return min(term_hits, 2) * 16.0 + min(problem_hits, 2) * 18.0 + min(len(latin_words), 32) + ideal_length_score + sentence_score + source_score


def _normalize_information_need(value: Optional[str]) -> Optional[str]:
    """Group free-text information needs into stable, user-facing categories."""
    if not value:
        return None

    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    if not normalized or normalized in {"unknown", "none", "null", "n a"}:
        return None

    if "link" in normalized or "where to buy" in normalized:
        return "product_link"
    if any(term in normalized for term in (
        "size", "sizing", "fit", "height", "measurement", "inseam", "length", "waist", "chest"
    )):
        return "sizing_and_fit_details"
    if any(term in normalized for term in (
        "price", "cost", "discount", "sale", "availability", "available", "stock", "budget"
    )):
        return "price_and_availability"
    if any(term in normalized for term in (
        "refund", "return status", "exchange status", "delivery status", "delivery delay", "order status"
    )):
        return "order_refund_and_delivery_updates"
    if any(term in normalized for term in (
        "style", "outfit", "look", "occasion", "recommendation", "how to wear", "pairing"
    )):
        return "styling_and_product_recommendations"
    if any(term in normalized for term in (
        "material", "fabric", "colour", "color", "stitch", "pocket", "transparent", "specification", "product detail"
    )):
        return "product_details_and_specifications"
    if any(term in normalized for term in ("brand", "seller", "authentic", "original")):
        return "brand_and_seller_details"
    if any(term in normalized for term in ("quality", "review", "rating")):
        return "quality_and_review_information"
    return None


def _aggregate_information_needs(rows, limit: int = 10):
    aggregated: Dict[str, int] = {}
    for name, count in rows:
        label = _normalize_information_need(name)
        if label:
            aggregated[label] = aggregated.get(label, 0) + count
    return [
        {"name": name, "count": count}
        for name, count in sorted(aggregated.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def _normalize_uncertainty(value: Optional[str]) -> Optional[str]:
    """Group free-text uncertainties into stable decision questions."""
    if not value:
        return None
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    if not normalized:
        return None
    if any(term in normalized for term in (
        "size", "sizing", "fit", "measurement", "height", "inseam", "length", "waist", "chest", "comfort"
    )):
        return "size_and_fit_confidence"
    if any(term in normalized for term in (
        "refund", "return", "exchange", "pickup", "claim", "credited", "money back"
    )):
        return "returns_refunds_and_exchanges"
    if any(term in normalized for term in (
        "deliver", "arrival", "arrive", "fulfil", "fulfill", "shipping", "order status", "order reach"
    )):
        return "delivery_timing_and_reliability"
    if any(term in normalized for term in (
        "quality", "fabric", "material", "durability", "stitch", "see through", "texture", "feel"
    )):
        return "product_quality_and_material"
    if any(term in normalized for term in (
        "authentic", "original", "fake", "counterfeit", "genuine", "seller", "sealed", "brand"
    )):
        return "authenticity_and_seller_trust"
    if any(term in normalized for term in (
        "link", "where to buy", "where to purchase", "stock", "available", "availability", "sold out"
    )):
        return "product_availability_and_links"
    if any(term in normalized for term in (
        "price", "discount", "sale", "fee", "charge", "cost", "myncash", "amount"
    )):
        return "price_discounts_and_fees"
    if any(term in normalized for term in (
        "match", "photo", "picture", "description", "wrong item", "wrong color", "wrong colour", "variation"
    )):
        return "product_accuracy"
    return None


def _normalize_workaround(value: Optional[str]) -> Optional[str]:
    """Group free-text shopper responses into stable workaround categories."""
    if not value:
        return None
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    if not normalized:
        return None
    if any(term in normalized for term in ("comment", "creator", "influencer")):
        return "asking_creators_or_in_comments"
    if any(term in normalized for term in (
        "customer support", "customer care", "help centre", "help center", "helpline", "support team", "complaint"
    )):
        return "contacting_customer_support"
    if any(term in normalized for term in (
        "switch", "meesho", "amazon", "ajio", "flipkart", "alternative platform", "other platform", "shopping app"
    )):
        return "switching_shopping_platforms"
    if any(term in normalized for term in (
        "google", "youtube", "instagram", "pinterest", "review elsewhere", "search elsewhere", "physical store", "compare price"
    )):
        return "researching_or_comparing_elsewhere"
    if any(term in normalized for term in ("wait", "retry", "re order", "reorder", "try again", "later")):
        return "waiting_or_retrying"
    if any(term in normalized for term in ("cancel", "uninstall", "stop using", "abandon", "gave up")):
        return "cancelling_or_leaving"
    return None


def _aggregate_free_text(rows, normalizer, limit: int = 10):
    aggregated: Dict[str, int] = {}
    for name, count in rows:
        label = normalizer(name)
        if label:
            aggregated[label] = aggregated.get(label, 0) + count
    ordered = sorted(aggregated.items(), key=lambda item: (-item[1], item[0]))
    return [{"name": name, "count": count} for name, count in ordered[:limit]], sum(aggregated.values())

def _build_filters(
    source: Optional[str] = None,
    wishlist_intent: Optional[str] = None,
    purchase_intent: Optional[str] = None,
    primary_barrier: Optional[str] = None,
    journey_stage: Optional[str] = None,
    decision_outcome: Optional[str] = None,
):
    filters = []
    if source: filters.append(Observation.source.in_(source.split(",")))
    if wishlist_intent: filters.append(Observation.wishlist_intent.in_(wishlist_intent.split(",")))
    if purchase_intent: filters.append(Observation.purchase_intent.in_(purchase_intent.split(",")))
    if primary_barrier: filters.append(Observation.primary_barrier.in_(primary_barrier.split(",")))
    if journey_stage: filters.append(Observation.journey_stage.in_(journey_stage.split(",")))
    if decision_outcome: filters.append(Observation.decision_outcome.in_(decision_outcome.split(",")))
    return filters

def _get_active_filters_dict(
    source, wishlist_intent, purchase_intent, primary_barrier, journey_stage, decision_outcome
) -> Dict[str, Any]:
    active = {}
    if source: active["source"] = source
    if wishlist_intent: active["wishlist_intent"] = wishlist_intent
    if purchase_intent: active["purchase_intent"] = purchase_intent
    if primary_barrier: active["primary_barrier"] = primary_barrier
    if journey_stage: active["journey_stage"] = journey_stage
    if decision_outcome: active["decision_outcome"] = decision_outcome
    return active


@router.get("/stats", response_model=DatasetStatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db_session)):
    
    # Get latest successful pipeline run
    run_query = select(PipelineRun).where(PipelineRun.status == "completed").order_by(desc(PipelineRun.completed_at)).limit(1)
    run_result = await db.execute(run_query)
    run = run_result.scalars().first()
    
    if not run:
        raise HTTPException(status_code=404, detail="No completed pipeline run found")
        
    # Calculate every displayed count from the current database snapshot.
    source_dist_query = select(Observation.source, func.count(Observation.observation_id)).group_by(Observation.source)
    dist_result = await db.execute(source_dist_query)
    source_dist_analyzed = {row[0]: row[1] for row in dist_result.all() if row[0]}

    cleaned_count_query = select(func.count(CleanedRecord.cleaned_record_id)).where(
        CleanedRecord.is_duplicate == False,
        CleanedRecord.is_spam == False,
    )
    cleaned_count_result = await db.execute(cleaned_count_query)
    cleaned_count = cleaned_count_result.scalar() or 0

    raw_count_result = await db.execute(select(func.count(RawRecord.raw_record_id)))
    raw_count = raw_count_result.scalar() or 0
    raw_dist_result = await db.execute(
        select(RawRecord.source, func.count(RawRecord.raw_record_id)).group_by(RawRecord.source)
    )
    raw_dist = {row[0]: row[1] for row in raw_dist_result.all() if row[0]}

    relevant_count_result = await db.execute(
        select(func.count(ClassifiedRecord.classified_record_id)).where(
            ClassifiedRecord.relevance_label.in_(("highly_relevant", "somewhat_relevant"))
        )
    )
    relevant_count = relevant_count_result.scalar() or 0
    processed_count_result = await db.execute(select(func.count(func.distinct(Observation.source_record_id))))
    processed_count = processed_count_result.scalar() or 0
    observation_count_result = await db.execute(select(func.count(Observation.observation_id)))
    observation_count = observation_count_result.scalar() or 0

    date_result = await db.execute(select(func.min(RawRecord.published_at), func.max(RawRecord.published_at)))
    min_date, max_date = date_result.one()
    snapshot_result = await db.execute(select(func.max(Observation.extracted_at)))
    snapshot_at = snapshot_result.scalar()

    source_labels = {
        "play_store": "Play Store",
        "youtube": "YouTube",
        "app_store": "App Store",
        "reddit": "Reddit",
    }
    return {
        "total_raw_records": raw_count,
        "cleaned_records": cleaned_count,
        "relevant_records": relevant_count,
        "processed_source_records": processed_count,
        "canonical_observations": observation_count,
        "source_distribution_analyzed": source_dist_analyzed,
        "source_distribution_raw": {
            source_labels.get(source, source.replace("_", " ").title()): count
            for source, count in raw_dist.items()
        },
        "date_range": {
            "start": min_date.date().isoformat() if min_date else "unknown",
            "end": max_date.date().isoformat() if max_date else "unknown",
        },
        "analysis_run_metadata": {
            "run_id": "legacy-snapshot-unregistered",
            "timestamp": snapshot_at.isoformat() if snapshot_at else run.completed_at.isoformat(),
        }
    }

@router.get("/themes", response_model=List[ThemeStat])
async def get_themes(db: AsyncSession = Depends(get_db_session)):
    from backend.store.database import PredefinedTheme, ThemeAssignment
    
    # Query predefined_themes + count from theme_assignments
    query = (
        select(
            PredefinedTheme.theme_id,
            PredefinedTheme.canonical_name,
            func.count(ThemeAssignment.observation_id).label("obs_count"),
        )
        .outerjoin(ThemeAssignment, ThemeAssignment.predefined_theme_id == PredefinedTheme.theme_id)
        .group_by(PredefinedTheme.theme_id, PredefinedTheme.canonical_name)
        .order_by(desc(func.count(ThemeAssignment.observation_id)))
    )
    result = await db.execute(query)
    rows = result.all()
    
    # Total observations for mapping rate
    total_obs_q = select(func.count(Observation.observation_id))
    total_obs_res = await db.execute(total_obs_q)
    total_obs = total_obs_res.scalar() or 1
    
    return [{
        "theme_id": row[0],
        "canonical_name": row[1],
        "observation_count": row[2],
        "unique_source_count": row[2],
        "mapping_rate_pct": round(row[2] / total_obs * 100, 1) if total_obs > 0 else 0.0
    } for row in rows]
    
@router.get("/clusters", response_model=List[ClusterStat])
async def get_clusters(db: AsyncSession = Depends(get_db_session)):
    query = select(SemanticCluster).where(SemanticCluster.is_noise == False).order_by(desc(SemanticCluster.observation_count))
    result = await db.execute(query)
    clusters = result.scalars().all()
    
    return [{
        "cluster_id": c.cluster_id,
        "canonical_label": c.canonical_label,
        "observation_count": c.observation_count,
        "unique_source_count": c.unique_source_count,
        "evidence_role": PATTERN_EVIDENCE_ROLES.get(c.cluster_id, "unreviewed"),
        "review_status": "directionally_reviewed" if c.cluster_id in PATTERN_EVIDENCE_ROLES else "unreviewed",
    } for c in clusters]

@router.get("/opportunities", response_model=List[OpportunityStat])
async def get_opportunities(db: AsyncSession = Depends(get_db_session)):
    query = select(Phase4OpportunityArea).order_by(Phase4OpportunityArea.opportunity_id)
    result = await db.execute(query)
    opportunities = result.scalars().all()
    
    stats = []
    for opp in opportunities:
        rule = OPPORTUNITY_RULES.get(opp.opportunity_id)
        if not rule:
            continue
        cluster_ids = rule["cluster_ids"]

        count_q = (
            select(func.count(func.distinct(Observation.source_record_id)))
            .join(ClusterMembership, ClusterMembership.observation_id == Observation.observation_id)
            .where(ClusterMembership.cluster_id.in_(cluster_ids))
        )
        count_res = await db.execute(count_q)
        unique_source_count = count_res.scalar() or 0

        quotes_q = (
            select(
                RawRecord.raw_text,
                RawRecord.source,
                RawRecord.source_url,
                RawRecord.raw_record_id,
            )
            .select_from(Observation)
            .join(ClusterMembership, ClusterMembership.observation_id == Observation.observation_id)
            .join(RawRecord, RawRecord.raw_record_id == Observation.source_record_id)
            .where(
                ClusterMembership.cluster_id.in_(cluster_ids),
                func.length(RawRecord.raw_text).between(70, 450),
            )
            .limit(500)
        )
        quotes_res = await db.execute(quotes_q)
        scored_quotes = []
        seen_records = set()
        seen_quotes = set()
        for row in quotes_res.all():
            normalized_quote = " ".join((row[0] or "").split()).lower()
            if row[3] in seen_records or normalized_quote in seen_quotes:
                continue
            score = _representative_quote_score(opp.opportunity_id, row[0], row[1])
            if score is None:
                continue
            seen_records.add(row[3])
            seen_quotes.add(normalized_quote)
            scored_quotes.append((score, row))
        preferred_source_ids = tuple(rule.get("preferred_representative_source_ids", ()))
        preferred_source_rank = {
            source_record_id: rank
            for rank, source_record_id in enumerate(preferred_source_ids)
        }
        scored_quotes.sort(key=lambda item: (
            preferred_source_rank.get(item[1][3], len(preferred_source_rank)),
            -item[0],
            -len(item[1][0] or ""),
        ))
        selected_quotes = [row for _, row in scored_quotes[:3]]
        rep_quotes = [
            {"quote": row[0], "source": row[1], "source_url": row[2]}
            for row in selected_quotes if row[0]
        ]

        denominator_result = await db.execute(select(func.count(func.distinct(Observation.source_record_id))))
        denominator = denominator_result.scalar() or 0
            
        stats.append({
            "opportunity_id": opp.opportunity_id,
            "title": rule["title"],
            "description": rule["description"],
            "original_generated_label": opp.title,
            "metric_relevance": "directional",
            "unique_source_count": unique_source_count,
            "dataset_percentage": round(unique_source_count / denominator * 100, 1) if denominator else 0.0,
            "denominator": denominator,
            "denominator_definition": "Successfully processed public-feedback records",
            "supporting_unmet_needs": list(rule["supporting_needs"]),
            "representative_quotes": rep_quotes,
            "calculation_note": rule["calculation_note"],
            "validation_status": "directional_reviewed_clusters",
        })
    return stats

@router.get("/barriers", response_model=DistributionResponse)
async def get_barriers(
    source: Optional[str] = Query(None),
    wishlist_intent: Optional[str] = Query(None),
    purchase_intent: Optional[str] = Query(None),
    journey_stage: Optional[str] = Query(None),
    decision_outcome: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session)
):
    active_filters = _get_active_filters_dict(
        source, wishlist_intent, purchase_intent, None, journey_stage, decision_outcome
    )
    db_filters = _build_filters(
        source=source, wishlist_intent=wishlist_intent, purchase_intent=purchase_intent,
        primary_barrier=None, journey_stage=journey_stage, decision_outcome=decision_outcome
    )
    
    query = select(Observation.primary_barrier, func.count(Observation.observation_id))
    
    if db_filters:
        query = query.where(*db_filters)
        
    query = query.group_by(Observation.primary_barrier).order_by(desc(func.count(Observation.observation_id)))
    
    result = await db.execute(query)
    items = [{"name": row[0] or "unknown", "count": row[1]} for row in result.all()]
    
    # Calculate denominator
    if not active_filters:
        denominator = 9171
        denominator_definition = "Total canonical observations"
        denominator_scope = "global"
    else:
        denom_query = select(func.count(Observation.observation_id))
        if db_filters: denom_query = denom_query.where(*db_filters)
        denom_result = await db.execute(denom_query)
        denominator = denom_result.scalar() or 0
        denominator_definition = "Observations matching active filters"
        denominator_scope = "filtered"
    
    return {
        "items": items,
        "denominator": denominator,
        "denominator_definition": denominator_definition,
        "denominator_scope": denominator_scope,
        "active_filters": active_filters
    }

@router.get("/wishlist-motivations", response_model=DistributionResponse)
async def get_wishlist_motivations(
    source: Optional[str] = Query(None),
    purchase_intent: Optional[str] = Query(None),
    primary_barrier: Optional[str] = Query(None),
    journey_stage: Optional[str] = Query(None),
    decision_outcome: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session)
):
    active_filters = _get_active_filters_dict(
        source, None, purchase_intent, primary_barrier, journey_stage, decision_outcome
    )
    db_filters = _build_filters(
        source=source, wishlist_intent=None, purchase_intent=purchase_intent,
        primary_barrier=primary_barrier, journey_stage=journey_stage, decision_outcome=decision_outcome
    )
    
    query = select(Observation.wishlist_intent, func.count(Observation.observation_id))
    if db_filters: query = query.where(*db_filters)
    query = query.group_by(Observation.wishlist_intent).order_by(desc(func.count(Observation.observation_id)))
    
    result = await db.execute(query)
    items = [{"name": row[0] or "unknown", "count": row[1]} for row in result.all()]
    
    if not active_filters:
        denominator = 9171
        denominator_definition = "Total canonical observations"
        denominator_scope = "global"
    else:
        denom_query = select(func.count(Observation.observation_id))
        if db_filters: denom_query = denom_query.where(*db_filters)
        denom_result = await db.execute(denom_query)
        denominator = denom_result.scalar() or 0
        denominator_definition = "Observations matching active filters"
        denominator_scope = "filtered"
    
    return {
        "items": items,
        "denominator": denominator,
        "denominator_definition": denominator_definition,
        "denominator_scope": denominator_scope,
        "active_filters": active_filters
    }

@router.get("/purchase-intents", response_model=DistributionResponse)
async def get_purchase_intents(
    source: Optional[str] = Query(None),
    wishlist_intent: Optional[str] = Query(None),
    primary_barrier: Optional[str] = Query(None),
    journey_stage: Optional[str] = Query(None),
    decision_outcome: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session)
):
    active_filters = _get_active_filters_dict(
        source, wishlist_intent, None, primary_barrier, journey_stage, decision_outcome
    )
    db_filters = _build_filters(
        source=source, wishlist_intent=wishlist_intent, purchase_intent=None,
        primary_barrier=primary_barrier, journey_stage=journey_stage, decision_outcome=decision_outcome
    )
    
    query = select(Observation.purchase_intent, func.count(Observation.observation_id))
    if db_filters: query = query.where(*db_filters)
    query = query.group_by(Observation.purchase_intent).order_by(desc(func.count(Observation.observation_id)))
    
    result = await db.execute(query)
    items = [{"name": row[0] or "unknown", "count": row[1]} for row in result.all()]
    
    if not active_filters:
        denominator = 9171
        denominator_definition = "Total canonical observations"
        denominator_scope = "global"
    else:
        denom_query = select(func.count(Observation.observation_id))
        if db_filters: denom_query = denom_query.where(*db_filters)
        denom_result = await db.execute(denom_query)
        denominator = denom_result.scalar() or 0
        denominator_definition = "Observations matching active filters"
        denominator_scope = "filtered"
    
    return {
        "items": items,
        "denominator": denominator,
        "denominator_definition": denominator_definition,
        "denominator_scope": denominator_scope,
        "active_filters": active_filters
    }
    
@router.get("/journey-stages", response_model=DistributionResponse)
async def get_journey_stages(
    source: Optional[str] = Query(None),
    wishlist_intent: Optional[str] = Query(None),
    purchase_intent: Optional[str] = Query(None),
    primary_barrier: Optional[str] = Query(None),
    decision_outcome: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session)
):
    active_filters = _get_active_filters_dict(
        source, wishlist_intent, purchase_intent, primary_barrier, None, decision_outcome
    )
    db_filters = _build_filters(
        source=source, wishlist_intent=wishlist_intent, purchase_intent=purchase_intent,
        primary_barrier=primary_barrier, journey_stage=None, decision_outcome=decision_outcome
    )
    
    query = select(Observation.journey_stage, func.count(Observation.observation_id))
    if db_filters: query = query.where(*db_filters)
    query = query.group_by(Observation.journey_stage).order_by(desc(func.count(Observation.observation_id)))
    
    result = await db.execute(query)
    items = [{"name": row[0] or "unknown", "count": row[1]} for row in result.all()]
    
    if not active_filters:
        denominator = 9171
        denominator_definition = "Total canonical observations"
        denominator_scope = "global"
    else:
        denom_query = select(func.count(Observation.observation_id))
        if db_filters: denom_query = denom_query.where(*db_filters)
        denom_result = await db.execute(denom_query)
        denominator = denom_result.scalar() or 0
        denominator_definition = "Observations matching active filters"
        denominator_scope = "filtered"
    
    return {
        "items": items,
        "denominator": denominator,
        "denominator_definition": denominator_definition,
        "denominator_scope": denominator_scope,
        "active_filters": active_filters
    }

@router.get("/decision-outcomes", response_model=DistributionResponse)
async def get_decision_outcomes(
    source: Optional[str] = Query(None),
    wishlist_intent: Optional[str] = Query(None),
    purchase_intent: Optional[str] = Query(None),
    primary_barrier: Optional[str] = Query(None),
    journey_stage: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session)
):
    active_filters = _get_active_filters_dict(
        source, wishlist_intent, purchase_intent, primary_barrier, journey_stage, None
    )
    db_filters = _build_filters(
        source=source, wishlist_intent=wishlist_intent, purchase_intent=purchase_intent,
        primary_barrier=primary_barrier, journey_stage=journey_stage, decision_outcome=None
    )
    
    query = select(Observation.decision_outcome, func.count(Observation.observation_id))
    if db_filters: query = query.where(*db_filters)
    query = query.group_by(Observation.decision_outcome).order_by(desc(func.count(Observation.observation_id)))
    
    result = await db.execute(query)
    items = [{"name": row[0] or "unknown", "count": row[1]} for row in result.all()]
    
    if not active_filters:
        denominator = 9171
        denominator_definition = "Total canonical observations"
        denominator_scope = "global"
    else:
        denom_query = select(func.count(Observation.observation_id))
        if db_filters: denom_query = denom_query.where(*db_filters)
        denom_result = await db.execute(denom_query)
        denominator = denom_result.scalar() or 0
        denominator_definition = "Observations matching active filters"
        denominator_scope = "filtered"
    
    return {
        "items": items,
        "denominator": denominator,
        "denominator_definition": denominator_definition,
        "denominator_scope": denominator_scope,
        "active_filters": active_filters
    }

@router.get("/uncertainties", response_model=DistributionResponse)
async def get_uncertainties(
    source: Optional[str] = Query(None),
    wishlist_intent: Optional[str] = Query(None),
    purchase_intent: Optional[str] = Query(None),
    primary_barrier: Optional[str] = Query(None),
    journey_stage: Optional[str] = Query(None),
    decision_outcome: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session)
):
    active_filters = _get_active_filters_dict(
        source, wishlist_intent, purchase_intent, primary_barrier, journey_stage, decision_outcome
    )
    db_filters = _build_filters(
        source=source, wishlist_intent=wishlist_intent, purchase_intent=purchase_intent,
        primary_barrier=primary_barrier, journey_stage=journey_stage, decision_outcome=decision_outcome
    )
    
    valid_uncertainty = [
        Observation.uncertainty.is_not(None),
        func.trim(Observation.uncertainty) != "",
        func.lower(func.trim(Observation.uncertainty)).notin_([
            "unknown", "none", "null", "n/a", "not specified", "not enough information to classify"
        ]),
        func.lower(Observation.uncertainty).not_like("%region_restricted%"),
    ]
    query = select(Observation.uncertainty, func.count(Observation.observation_id))
    query = query.where(*valid_uncertainty)
    if db_filters: query = query.where(*db_filters)
    query = query.group_by(Observation.uncertainty)
    
    result = await db.execute(query)
    items, classified_count = _aggregate_free_text(result.all(), _normalize_uncertainty)
    
    total_query = select(func.count(Observation.observation_id))
    if db_filters:
        total_query = total_query.where(*db_filters)
    total_count = (await db.execute(total_query)).scalar() or 0
    
    return {
        "items": items,
        "denominator": classified_count,
        "denominator_definition": "Records with an identifiable uncertainty",
        "denominator_scope": "classified",
        "active_filters": active_filters,
        "classified_count": classified_count,
        "unclassified_count": max(total_count - classified_count, 0),
    }

@router.get("/information-needs", response_model=DistributionResponse)
async def get_information_needs(
    source: Optional[str] = Query(None),
    wishlist_intent: Optional[str] = Query(None),
    purchase_intent: Optional[str] = Query(None),
    primary_barrier: Optional[str] = Query(None),
    journey_stage: Optional[str] = Query(None),
    decision_outcome: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session)
):
    active_filters = _get_active_filters_dict(
        source, wishlist_intent, purchase_intent, primary_barrier, journey_stage, decision_outcome
    )
    db_filters = _build_filters(
        source=source, wishlist_intent=wishlist_intent, purchase_intent=purchase_intent,
        primary_barrier=primary_barrier, journey_stage=journey_stage, decision_outcome=decision_outcome
    )
    
    query = select(Observation.information_needed, func.count(Observation.observation_id))
    query = query.where(
        Observation.information_needed.is_not(None),
        func.lower(func.trim(Observation.information_needed)).notin_(["", "unknown", "none", "null"]),
    )
    if db_filters: query = query.where(*db_filters)
    query = query.group_by(Observation.information_needed)
    
    result = await db.execute(query)
    items = _aggregate_information_needs(result.all())
    
    denom_query = select(func.count(Observation.observation_id))
    if db_filters: denom_query = denom_query.where(*db_filters)
    denom_result = await db.execute(denom_query)
    denominator = denom_result.scalar() or 0
    
    return {
        "items": items,
        "denominator": denominator,
        "denominator_definition": "Observations matching active filters",
        "denominator_scope": "filtered" if active_filters else "global",
        "active_filters": active_filters
    }

@router.get("/workarounds", response_model=DistributionResponse)
async def get_workarounds(
    source: Optional[str] = Query(None),
    wishlist_intent: Optional[str] = Query(None),
    purchase_intent: Optional[str] = Query(None),
    primary_barrier: Optional[str] = Query(None),
    journey_stage: Optional[str] = Query(None),
    decision_outcome: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session)
):
    active_filters = _get_active_filters_dict(
        source, wishlist_intent, purchase_intent, primary_barrier, journey_stage, decision_outcome
    )
    db_filters = _build_filters(
        source=source, wishlist_intent=wishlist_intent, purchase_intent=purchase_intent,
        primary_barrier=primary_barrier, journey_stage=journey_stage, decision_outcome=decision_outcome
    )
    
    valid_workaround = [
        Observation.workaround.is_not(None),
        func.trim(Observation.workaround) != "",
        func.lower(func.trim(Observation.workaround)).notin_([
            "unknown", "none", "null", "n/a", "not specified", "not enough information to classify", "?", "??"
        ]),
        func.lower(Observation.workaround).not_like("%region_restricted%"),
    ]
    query = select(Observation.workaround, func.count(Observation.observation_id))
    query = query.where(*valid_workaround)
    if db_filters: query = query.where(*db_filters)
    query = query.group_by(Observation.workaround)
    
    result = await db.execute(query)
    items, classified_count = _aggregate_free_text(result.all(), _normalize_workaround)
    
    total_query = select(func.count(Observation.observation_id))
    if db_filters:
        total_query = total_query.where(*db_filters)
    total_count = (await db.execute(total_query)).scalar() or 0
    
    return {
        "items": items,
        "denominator": classified_count,
        "denominator_definition": "Records with an identifiable workaround",
        "denominator_scope": "classified",
        "active_filters": active_filters,
        "classified_count": classified_count,
        "unclassified_count": max(total_count - classified_count, 0),
    }

@router.get("/segments", response_model=DistributionResponse)
async def get_segments(
    source: Optional[str] = Query(None),
    wishlist_intent: Optional[str] = Query(None),
    purchase_intent: Optional[str] = Query(None),
    primary_barrier: Optional[str] = Query(None),
    journey_stage: Optional[str] = Query(None),
    decision_outcome: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session)
):
    active_filters = _get_active_filters_dict(
        source, wishlist_intent, purchase_intent, primary_barrier, journey_stage, decision_outcome
    )
    db_filters = _build_filters(
        source=source, wishlist_intent=wishlist_intent, purchase_intent=purchase_intent,
        primary_barrier=primary_barrier, journey_stage=journey_stage, decision_outcome=decision_outcome
    )
    
    query = select(Observation.segment_signal, func.count(Observation.observation_id))
    query = query.where(Observation.segment_signal != "unknown", Observation.segment_signal.is_not(None))
    if db_filters: query = query.where(*db_filters)
    query = query.group_by(Observation.segment_signal).order_by(desc(func.count(Observation.observation_id))).limit(10)
    
    result = await db.execute(query)
    items = [{"name": row[0], "count": row[1]} for row in result.all()]
    
    denom_query = select(func.count(Observation.observation_id))
    if db_filters: denom_query = denom_query.where(*db_filters)
    denom_result = await db.execute(denom_query)
    denominator = denom_result.scalar() or 0
    
    return {
        "items": items,
        "denominator": denominator,
        "denominator_definition": "Observations matching active filters",
        "denominator_scope": "filtered" if active_filters else "global",
        "active_filters": active_filters
    }
