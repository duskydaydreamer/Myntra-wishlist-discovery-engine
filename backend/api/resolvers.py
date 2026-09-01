from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from fastapi import HTTPException
from backend.store.database import PipelineRun

async def get_latest_successful_run(db: AsyncSession) -> PipelineRun:
    """
    Returns the canonical latest successfully completed pipeline run.
    - status MUST equal "completed"
    - order deterministically by completion timestamp, then started_at, then run_id
    """
    query = (
        select(PipelineRun)
        .where(PipelineRun.status == "completed")
        .order_by(
            desc(PipelineRun.completed_at),
            desc(PipelineRun.started_at),
            desc(PipelineRun.run_id)
        )
        .limit(1)
    )
    result = await db.execute(query)
    run = result.scalars().first()
    
    if not run:
        raise HTTPException(status_code=404, detail="No completed pipeline run found")
        
    return run
