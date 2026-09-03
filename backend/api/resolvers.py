from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from fastapi import HTTPException
from backend.store.database import PipelineRun

async def get_latest_successful_run(db: AsyncSession) -> PipelineRun:
    """
    Returns the canonical latest successfully completed pipeline run
    that processed a comprehensive dataset (> 1000 records).
    """
    from backend.store.database import RunRecord
    from sqlalchemy import func

    query = (
        select(PipelineRun)
        .where(PipelineRun.status == "completed")
        .order_by(
            desc(PipelineRun.completed_at),
            desc(PipelineRun.started_at),
            desc(PipelineRun.run_id)
        )
    )
    result = await db.execute(query)
    
    for run in result.scalars().all():
        count_q = select(func.count(RunRecord.run_record_id)).where(RunRecord.pipeline_run_id == run.run_id)
        count_res = await db.execute(count_q)
        count = count_res.scalar() or 0
        if count > 1000:
            return run
            
    raise HTTPException(status_code=404, detail="No comprehensive completed pipeline run found")
