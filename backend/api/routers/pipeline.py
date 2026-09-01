from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Dict, Any

from backend.api.dependencies import get_db_session
from backend.store.database import PipelineRun

router = APIRouter()

@router.get("/runs")
async def list_pipeline_runs(db: AsyncSession = Depends(get_db_session)):
    query = select(PipelineRun).order_by(desc(PipelineRun.started_at)).limit(10)
    result = await db.execute(query)
    runs = result.scalars().all()
    
    return [
        {
            "run_id": r.run_id,
            "status": r.status,
            "started_at": r.started_at,
            "completed_at": r.completed_at,
            "relevant_record_count": r.relevant_record_count,
            "observation_count": r.observation_count
        } for r in runs
    ]

@router.get("/runs/{run_id}")
async def get_pipeline_run(run_id: str, db: AsyncSession = Depends(get_db_session)):
    query = select(PipelineRun).where(PipelineRun.run_id == run_id)
    result = await db.execute(query)
    run = result.scalars().first()
    
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
        
    import json
    return {
        "run_id": run.run_id,
        "status": run.status,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "triggered_by": run.triggered_by,
        "review_window_start": run.review_window_start,
        "review_window_end": run.review_window_end,
        "source_statuses": json.loads(run.source_statuses) if run.source_statuses else {},
        "source_record_counts": json.loads(run.source_record_counts) if run.source_record_counts else {},
        "relevant_record_count": run.relevant_record_count,
        "observation_count": run.observation_count,
        "theme_count": run.theme_count,
        "opportunity_count": run.opportunity_count,
        "errors": json.loads(run.errors) if run.errors else []
    }

@router.post("/run")
async def trigger_pipeline_run(background_tasks: BackgroundTasks):
    # Triggers the pipeline via backend pipeline runner
    # We will just return a placeholder for now as requested by the plan not to expand Phase 5 into orchestration.
    return {"status": "accepted", "message": "Pipeline run triggered (placeholder)"}
