from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Dict, Any
import json

from backend.api.dependencies import get_db_session
from backend.store.database import Phase4OpportunityArea, Observation, ClusterMembership
from backend.research_rules import OPPORTUNITY_RULES

router = APIRouter()

@router.get("")
async def list_opportunities(db: AsyncSession = Depends(get_db_session)):
    query = select(Phase4OpportunityArea)
    result = await db.execute(query)
    opportunities = result.scalars().all()
    
    return [
        {
            "opportunity_id": o.opportunity_id,
            "title": OPPORTUNITY_RULES[o.opportunity_id]["title"],
            "original_generated_label": o.title,
            "description": OPPORTUNITY_RULES[o.opportunity_id]["description"],
            "purchase_metric_relevance": "directional",
            "validation_status": "directional_reviewed_clusters",
        } for o in opportunities if o.opportunity_id in OPPORTUNITY_RULES
    ]

@router.get("/{opportunity_id}")
async def get_opportunity_detail(opportunity_id: str, db: AsyncSession = Depends(get_db_session)):
    query = select(Phase4OpportunityArea).where(Phase4OpportunityArea.opportunity_id == opportunity_id)
    result = await db.execute(query)
    opp = result.scalars().first()
    
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    rule = OPPORTUNITY_RULES.get(opportunity_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Opportunity has not been reviewed for publication")

    cluster_ids = rule["cluster_ids"]
    obs_q = (
        select(Observation)
        .join(ClusterMembership, ClusterMembership.observation_id == Observation.observation_id)
        .where(ClusterMembership.cluster_id.in_(cluster_ids))
        .order_by(desc(func.length(Observation.evidence_quote)))
        .limit(50)
    )
    
    obs_res = await db.execute(obs_q)
    observations = obs_res.scalars().all()
    
    # Count distinct feedback records, not observations or people.
    sources_q = (
        select(Observation.source, Observation.source_record_id)
        .join(ClusterMembership, ClusterMembership.observation_id == Observation.observation_id)
        .where(ClusterMembership.cluster_id.in_(cluster_ids))
        .distinct()
    )
    sources_res = await db.execute(sources_q)
    source_rows = [(r[0], r[1]) for r in sources_res.all() if r[1]]
    unique_source_count = len(source_rows)
    
    source_distribution = {}
    for s, _ in source_rows:
        if not s:
            continue
        source_distribution[s] = source_distribution.get(s, 0) + 1

    total_result = await db.execute(select(func.count(func.distinct(Observation.source_record_id))))
    total_processed_records = total_result.scalar() or 0
    
    return {
        "opportunity_id": opp.opportunity_id,
        "title": rule["title"],
        "original_generated_label": opp.title,
        "description": rule["description"],
        "purchase_metric_relevance": "directional",
        "wishlist_metric_relevance": "directional",
        "unique_source_count": unique_source_count,
        "dataset_percentage": round(unique_source_count / total_processed_records * 100, 1) if total_processed_records > 0 else 0,
        "denominator": total_processed_records,
        "denominator_definition": "Successfully processed public-feedback records",
        "source_distribution": source_distribution,
        "supporting_needs": list(rule["supporting_needs"]),
        "calculation_note": rule["calculation_note"],
        "validation_status": "directional_reviewed_clusters",
        "supporting_observations": [
            {
                "observation_id": o.observation_id,
                "evidence_quote": o.evidence_quote,
                "source": o.source,
                "source_url": o.source_url
            } for o in observations
        ]
    }
