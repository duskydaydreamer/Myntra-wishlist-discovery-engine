from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, case
from typing import List, Optional
import csv
from io import StringIO
from fastapi.responses import StreamingResponse

from backend.api.dependencies import get_db_session
from backend.api.schemas.evidence import EvidenceListResponse, ObservationResponse, ObservationDetailResponse
from backend.store.database import Observation, ThemeAssignment, ClusterMembership, OpportunityEvidence
from backend.api.routers.dashboard import _build_filters
from backend.research_rules import OPPORTUNITY_RULES

router = APIRouter()

@router.get("", response_model=EvidenceListResponse)
async def list_evidence(
    source: Optional[str] = Query(None),
    wishlist_intent: Optional[str] = Query(None),
    purchase_intent: Optional[str] = Query(None),
    primary_barrier: Optional[str] = Query(None),
    journey_stage: Optional[str] = Query(None),
    decision_outcome: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    predefined_theme: Optional[str] = Query(None),
    cluster_id: Optional[str] = Query(None),
    opportunity_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session)
):
    db_filters = _build_filters(
        source=source, wishlist_intent=wishlist_intent, purchase_intent=purchase_intent,
        primary_barrier=primary_barrier, journey_stage=journey_stage, decision_outcome=decision_outcome
    )
    if search:
        db_filters.append(Observation.evidence_quote.ilike(f"%{search}%"))
    if predefined_theme:
        db_filters.append(Observation.observation_id.in_(
            select(ThemeAssignment.observation_id).where(ThemeAssignment.predefined_theme_id == predefined_theme)
        ))
    if cluster_id:
        db_filters.append(Observation.observation_id.in_(
            select(ClusterMembership.observation_id).where(ClusterMembership.cluster_id == cluster_id)
        ))
    if opportunity_id:
        rule = OPPORTUNITY_RULES.get(opportunity_id)
        if rule:
            db_filters.append(Observation.observation_id.in_(
                select(ClusterMembership.observation_id).where(
                    ClusterMembership.cluster_id.in_(rule["cluster_ids"])
                )
            ))
        else:
            db_filters.append(Observation.observation_id == "__unreviewed_opportunity__")
    
    count_query = select(func.count(Observation.observation_id))
    if db_filters: count_query = count_query.where(*db_filters)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    query = select(Observation)
    if db_filters: query = query.where(*db_filters)

    # Lead with quotes that are substantial and have enough structured context
    # to be useful. This changes presentation order only; no evidence is removed.
    quote_length = func.length(func.trim(Observation.evidence_quote))
    unknown_values = ("", "unknown", "unclear", "none", "null", "not_classified")
    classification_score = (
        case((func.lower(func.coalesce(Observation.primary_barrier, "")).notin_(unknown_values), 1), else_=0)
        + case((func.lower(func.coalesce(Observation.journey_stage, "")).notin_(unknown_values), 1), else_=0)
        + case((func.lower(func.coalesce(Observation.decision_outcome, "")).notin_(unknown_values), 1), else_=0)
        + case((func.lower(func.coalesce(Observation.purchase_intent, "")).notin_(unknown_values), 1), else_=0)
    )
    writing_quality_band = case(
        (quote_length >= 120, 0),
        (quote_length >= 70, 1),
        (quote_length >= 35, 2),
        else_=3,
    )
    has_privacy_mask = case(
        (Observation.evidence_quote.ilike("%[NAME]%"), 1),
        else_=0,
    )
    query = query.order_by(
        writing_quality_band,
        has_privacy_mask,
        desc(classification_score),
        desc(func.coalesce(Observation.ai_confidence, 0)),
        desc(quote_length),
        Observation.observation_id,
    ).offset((page - 1) * size).limit(size)
    
    result = await db.execute(query)
    observations = result.scalars().all()
    
    items = []
    for obs in observations:
        # Fetch derived data (mocked slightly for speed, but ideally use joins)
        theme_q = select(ThemeAssignment.predefined_theme_id).where(ThemeAssignment.observation_id == obs.observation_id)
        cluster_q = select(ClusterMembership.cluster_id).where(ClusterMembership.observation_id == obs.observation_id)
        themes = (await db.execute(theme_q)).scalars().all()
        clusters = (await db.execute(cluster_q)).scalars().all()
        
        items.append(ObservationResponse(
            observation_id=obs.observation_id,
            source=obs.source,
            evidence_quote=obs.evidence_quote,
            primary_barrier=obs.primary_barrier,
            wishlist_intent=obs.wishlist_intent,
            purchase_intent=obs.purchase_intent,
            journey_stage=obs.journey_stage,
            decision_outcome=obs.decision_outcome,
            uncertainty=obs.uncertainty,
            ai_confidence=obs.ai_confidence,
            topic=obs.topic,
            sentiment=obs.sentiment,
            problem_status=obs.problem_status,
            evidence_scope=obs.evidence_scope,
            predefined_themes=themes,
            emergent_clusters=clusters
        ))
        
    return EvidenceListResponse(items=items, total=total, page=page, size=size)

@router.get("/export")
async def export_evidence(
    source: Optional[str] = Query(None),
    wishlist_intent: Optional[str] = Query(None),
    purchase_intent: Optional[str] = Query(None),
    primary_barrier: Optional[str] = Query(None),
    journey_stage: Optional[str] = Query(None),
    decision_outcome: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    predefined_theme: Optional[str] = Query(None),
    cluster_id: Optional[str] = Query(None),
    opportunity_id: Optional[str] = Query(None),
    format: Optional[str] = Query("csv"),
    db: AsyncSession = Depends(get_db_session)
):
    db_filters = _build_filters(
        source=source, wishlist_intent=wishlist_intent, purchase_intent=purchase_intent,
        primary_barrier=primary_barrier, journey_stage=journey_stage, decision_outcome=decision_outcome
    )
    if search:
        db_filters.append(Observation.evidence_quote.ilike(f"%{search}%"))
    if predefined_theme:
        db_filters.append(Observation.observation_id.in_(
            select(ThemeAssignment.observation_id).where(ThemeAssignment.predefined_theme_id == predefined_theme)
        ))
    if cluster_id:
        db_filters.append(Observation.observation_id.in_(
            select(ClusterMembership.observation_id).where(ClusterMembership.cluster_id == cluster_id)
        ))
    if opportunity_id:
        rule = OPPORTUNITY_RULES.get(opportunity_id)
        if rule:
            db_filters.append(Observation.observation_id.in_(
                select(ClusterMembership.observation_id).where(
                    ClusterMembership.cluster_id.in_(rule["cluster_ids"])
                )
            ))
        else:
            db_filters.append(Observation.observation_id == "__unreviewed_opportunity__")
    
    query = select(Observation)
    if db_filters: query = query.where(*db_filters)
    
    result = await db.execute(query)
    observations = result.scalars().all()
    
    if format == "json":
        import json
        out_list = []
        for obs in observations:
            out_list.append({
                "observation_id": obs.observation_id,
                "source": obs.source,
                "evidence_quote": obs.evidence_quote,
                "primary_barrier": obs.primary_barrier,
                "wishlist_intent": obs.wishlist_intent,
                "purchase_intent": obs.purchase_intent
            })
        
        output = StringIO()
        json.dump(out_list, output, indent=2)
        output.seek(0)
        return StreamingResponse(output, media_type="application/json", headers={"Content-Disposition": "attachment; filename=evidence_export.json"})
    else:
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Observation ID", "Source", "Quote", "Primary Barrier", "Wishlist Intent", "Purchase Intent"])
        for obs in observations:
            writer.writerow([obs.observation_id, obs.source, obs.evidence_quote, obs.primary_barrier, obs.wishlist_intent, obs.purchase_intent])
            
        output.seek(0)
        return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=evidence_export.csv"})

@router.get("/{observation_id}", response_model=ObservationDetailResponse)
async def get_evidence_detail(observation_id: str, db: AsyncSession = Depends(get_db_session)):
    query = select(Observation).where(Observation.observation_id == observation_id)
    result = await db.execute(query)
    obs = result.scalars().first()
    
    if not obs:
        raise HTTPException(status_code=404, detail="Observation not found")
        
    theme_q = select(ThemeAssignment.predefined_theme_id).where(ThemeAssignment.observation_id == obs.observation_id)
    cluster_q = select(ClusterMembership.cluster_id).where(ClusterMembership.observation_id == obs.observation_id)
    
    themes = (await db.execute(theme_q)).scalars().all()
    clusters = (await db.execute(cluster_q)).scalars().all()
    opps = [
        opportunity_id
        for opportunity_id, rule in OPPORTUNITY_RULES.items()
        if any(cluster_id in rule["cluster_ids"] for cluster_id in clusters)
    ]
    
    import json
    # SQLAlchemy's JSON column may already deserialize this value. Accept both
    # persisted representations while preserving the response contract.
    if isinstance(obs.secondary_barriers, list):
        secondary_barriers = obs.secondary_barriers
    elif isinstance(obs.secondary_barriers, str):
        secondary_barriers = json.loads(obs.secondary_barriers)
    else:
        secondary_barriers = []
    
    return ObservationDetailResponse(
        observation_id=obs.observation_id,
        source=obs.source,
        evidence_quote=obs.evidence_quote,
        primary_barrier=obs.primary_barrier,
        wishlist_intent=obs.wishlist_intent,
        purchase_intent=obs.purchase_intent,
        journey_stage=obs.journey_stage,
        decision_outcome=obs.decision_outcome,
        uncertainty=obs.uncertainty,
        ai_confidence=obs.ai_confidence,
        topic=obs.topic,
        sentiment=obs.sentiment,
        problem_status=obs.problem_status,
        evidence_scope=obs.evidence_scope,
        predefined_themes=themes,
        emergent_clusters=clusters,
        source_url=obs.source_url,
        source_record_id=obs.source_record_id,
        is_myntra_specific=obs.is_myntra_specific,
        product_category=obs.product_category,
        secondary_barriers=secondary_barriers,
        root_cause=obs.root_cause,
        information_needed=obs.information_needed,
        workaround=obs.workaround,
        external_platform_used=obs.external_platform_used,
        alternative_considered=obs.alternative_considered,
        occasion=obs.occasion,
        segment_signal=obs.segment_signal,
        opportunity_ids=opps
    )
