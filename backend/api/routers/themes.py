from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any

from backend.api.dependencies import get_db_session
from backend.store.database import PredefinedTheme, ThemeAssignment, Observation

router = APIRouter()

@router.get("")
async def list_themes(db: AsyncSession = Depends(get_db_session)):
    query = select(PredefinedTheme)
    result = await db.execute(query)
    themes = result.scalars().all()
    
    return [
        {
            "theme_id": t.theme_id,
            "canonical_name": t.canonical_name,
            "description": t.description
        } for t in themes
    ]

@router.get("/{theme_id}")
async def get_theme_detail(theme_id: str, db: AsyncSession = Depends(get_db_session)):
    query = select(PredefinedTheme).where(PredefinedTheme.theme_id == theme_id)
    result = await db.execute(query)
    theme = result.scalars().first()
    
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
        
    assignment_q = select(ThemeAssignment.observation_id).where(ThemeAssignment.predefined_theme_id == theme_id)
    assignment_res = await db.execute(assignment_q)
    obs_ids = assignment_res.scalars().all()
    
    supporting_observations = []
    if obs_ids:
        obs_q = select(Observation).where(Observation.observation_id.in_(obs_ids)).limit(50)
        obs_res = await db.execute(obs_q)
        obs_list = obs_res.scalars().all()
        supporting_observations = [
            {
                "observation_id": o.observation_id,
                "evidence_quote": o.evidence_quote,
                "source": o.source
            } for o in obs_list
        ]
        
    return {
        "theme_id": theme.theme_id,
        "canonical_name": theme.canonical_name,
        "description": theme.description,
        "supporting_observations": supporting_observations
    }
