from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any
import json

from backend.api.dependencies import get_db_session
from backend.store.database import UnmetNeedContext

router = APIRouter()

@router.get("")
async def list_unmet_needs(db: AsyncSession = Depends(get_db_session)):
    query = select(UnmetNeedContext)
    result = await db.execute(query)
    needs = result.scalars().all()
    
    return [
        {
            "unmet_need": n.unmet_need,
            "observation_count": n.observation_count,
            "associated_barriers": json.loads(n.associated_barriers_json) if n.associated_barriers_json else [],
            "associated_intents": json.loads(n.associated_intents_json) if n.associated_intents_json else []
        } for n in needs
    ]
