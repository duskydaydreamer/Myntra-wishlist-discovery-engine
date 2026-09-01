from fastapi import APIRouter, Depends
import yaml
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.api.dependencies import get_db_session
from backend.store.database import ThemeAssignment, ClusterMembership, OpportunityEvidence, Observation

router = APIRouter()

@router.get("/filter-options")
async def get_filter_options(db: AsyncSession = Depends(get_db_session)):
    taxonomies_path = os.path.join(os.getcwd(), "config", "taxonomies.yaml")
    options = {}
    if os.path.exists(taxonomies_path):
        with open(taxonomies_path, "r") as f:
            taxonomies = yaml.safe_load(f)
            options = taxonomies
    
    # Add source options which might be in config.yaml instead
    options["source"] = ["play_store", "app_store", "reddit", "youtube"]
    options["journey_stage"] = ["discovery", "research", "evaluation", "purchase", "post_purchase", "unknown"]
    options["decision_outcome"] = ["bought", "postponed", "abandoned", "switched", "delayed", "unknown"]

    # Evidence Explorer filters must use the values that are actually stored in
    # observations. The taxonomy config uses different, pluralized keys and is
    # not a reliable source for these query parameters.
    evidence_fields = {
        "source": Observation.source,
        "wishlist_intent": Observation.wishlist_intent,
        "purchase_intent": Observation.purchase_intent,
        "primary_barrier": Observation.primary_barrier,
        "journey_stage": Observation.journey_stage,
        "decision_outcome": Observation.decision_outcome,
    }
    for key, column in evidence_fields.items():
        values_res = await db.execute(select(column).where(column.is_not(None)).distinct().order_by(column))
        options[key] = [value for value in values_res.scalars().all() if value]
    
    # Fetch dynamic relationship filters
    themes_res = await db.execute(select(ThemeAssignment.predefined_theme_id).distinct())
    options["predefined_theme"] = [t for t in themes_res.scalars().all() if t]
    
    clusters_res = await db.execute(select(ClusterMembership.cluster_id).distinct())
    options["cluster_id"] = [c for c in clusters_res.scalars().all() if c]
    
    opps_res = await db.execute(select(OpportunityEvidence.opportunity_id).distinct())
    options["opportunity_id"] = [o for o in opps_res.scalars().all() if o]
    
    return options
