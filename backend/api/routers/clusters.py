from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any

from backend.api.dependencies import get_db_session
from backend.store.database import SemanticCluster, ClusterSynthesis, ClusterAggregation, ClusterRepresentative, Observation, ClusterMembership

router = APIRouter()

@router.get("")
async def list_clusters(db: AsyncSession = Depends(get_db_session)):
    query = select(SemanticCluster).where(SemanticCluster.is_noise == False)
    result = await db.execute(query)
    clusters = result.scalars().all()
    
    return [
        {
            "cluster_id": c.cluster_id,
            "canonical_label": c.canonical_label,
            "observation_count": c.observation_count,
            "unique_source_count": c.unique_source_count
        } for c in clusters
    ]

@router.get("/{cluster_id}")
async def get_cluster_detail(cluster_id: str, db: AsyncSession = Depends(get_db_session)):
    query = select(SemanticCluster).where(SemanticCluster.cluster_id == cluster_id)
    result = await db.execute(query)
    cluster = result.scalars().first()
    
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
        
    synthesis_q = select(ClusterSynthesis).where(ClusterSynthesis.cluster_id == cluster_id)
    synthesis_res = await db.execute(synthesis_q)
    synthesis = synthesis_res.scalars().first()
    
    agg_q = select(ClusterAggregation).where(ClusterAggregation.cluster_id == cluster_id)
    agg_res = await db.execute(agg_q)
    aggregation = agg_res.scalars().first()
    
    rep_q = select(ClusterRepresentative).where(ClusterRepresentative.cluster_id == cluster_id)
    rep_res = await db.execute(rep_q)
    representatives = rep_res.scalars().all()
    
    import json
    return {
        "cluster_id": cluster.cluster_id,
        "canonical_label": cluster.canonical_label,
        "observation_count": cluster.observation_count,
        "unique_source_count": cluster.unique_source_count,
        "synthesis": {
            "canonical_name": synthesis.canonical_name if synthesis else None,
            "description": synthesis.description if synthesis else None,
            "primary_root_cause": synthesis.primary_root_cause if synthesis else None,
            "primary_unmet_need": synthesis.primary_unmet_need if synthesis else None,
        } if synthesis else None,
        "distributions": json.loads(aggregation.distributions_json) if aggregation and aggregation.distributions_json else None,
        "representative_quotes": [
            {
                "observation_id": r.observation_id,
                "evidence_quote": r.evidence_quote,
                "source": r.source,
                "source_url": r.source_url
            } for r in representatives
        ]
    }
