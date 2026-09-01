from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import os
import uuid
import datetime
from datetime import timezone
from pydantic import BaseModel
from typing import Optional

from backend.api.dependencies import get_db_session
from backend.store.database import PipelineRun, SessionLocal
from backend.pipeline.orchestrator import run_canonical_pipeline

router = APIRouter()

def verify_scheduler_secret(authorization: Optional[str] = Header(None)):
    secret = os.getenv("SCHEDULER_SECRET")
    if not secret:
        raise HTTPException(status_code=500, detail="SCHEDULER_SECRET not configured")
    if not authorization or authorization != f"Bearer {secret}":
        raise HTTPException(status_code=401, detail="Unauthorized")

@router.post("/refresh")
async def trigger_pipeline_refresh(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
    _=Depends(verify_scheduler_secret)
):
    # Concurrency and Stale run protection
    query = select(PipelineRun).where(PipelineRun.status == "running")
    result = await db.execute(query)
    running = result.scalars().first()
    
    if running:
        # Check for stale run
        stale_hours = float(os.getenv("PIPELINE_STALE_AFTER_HOURS", "12.0"))
        now_utc = datetime.datetime.now(timezone.utc).replace(tzinfo=None)
        run_duration = now_utc - running.started_at
        
        if run_duration.total_seconds() > stale_hours * 3600:
            running.status = "interrupted"
            if running.errors is None:
                running.errors = []
            else:
                import json
                if isinstance(running.errors, str):
                    running.errors = json.loads(running.errors)
            
            # Since errors is a JSON column, we'll append to it (assuming it's a list)
            current_errors = running.errors or []
            if isinstance(current_errors, str):
                current_errors = json.loads(current_errors)
            current_errors.append(f"Marked interrupted due to being stale for {run_duration.total_seconds()/3600:.1f} hours.")
            running.errors = json.dumps(current_errors)
            
            await db.commit()
        else:
            raise HTTPException(status_code=409, detail=f"Pipeline run {running.run_id} is already in progress.")
        
    new_run = PipelineRun(run_id=f"run_{uuid.uuid4().hex[:8]}", status="running", started_at=datetime.datetime.now(timezone.utc))
    db.add(new_run)
    await db.commit()
    
    # Run canonical pipeline in background
    background_tasks.add_task(run_pipeline_task, new_run.run_id)
    
    return {"message": "Pipeline refresh started", "run_id": new_run.run_id, "status": "running"}

async def run_pipeline_task(run_id: str):
    # Obtain a separate session for the background task
    db = SessionLocal()
    try:
        await run_canonical_pipeline(db, run_id)
    except Exception as e:
        run_record = db.query(PipelineRun).filter(PipelineRun.run_id == run_id).first()
        if run_record:
            run_record.status = "failed"
            if run_record.errors is None:
                run_record.errors = []
            run_record.errors.append({"error": str(e), "timestamp": datetime.datetime.utcnow().isoformat()})
            db.commit()
    finally:
        db.close()
