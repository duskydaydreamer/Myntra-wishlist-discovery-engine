import json
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.store.database import PipelineRun

class RunTracker:
    def __init__(self, session: AsyncSession, run_id: str):
        self.session = session
        self.run_id = run_id
        
    async def initialize_run(self, triggered_by: str = "manual"):
        run = PipelineRun(
            run_id=self.run_id,
            triggered_by=triggered_by,
            started_at=datetime.utcnow(),
            status="running",
            source_record_counts=json.dumps({}),
            source_statuses=json.dumps({}),
            errors=json.dumps([])
        )
        self.session.add(run)
        await self.session.commit()
        
    async def update_source_status(self, source: str, status: str, count: int = 0, error: Optional[str] = None):
        result = await self.session.execute(select(PipelineRun).where(PipelineRun.run_id == self.run_id))
        run = result.scalar_one_or_none()
        
        if not run:
            return
            
        counts = json.loads(run.source_record_counts) if run.source_record_counts else {}
        statuses = json.loads(run.source_statuses) if run.source_statuses else {}
        errors = json.loads(run.errors) if run.errors else []
        
        counts[source] = count
        statuses[source] = status
        if error:
            errors.append({"source": source, "error": error})
            
        run.source_record_counts = json.dumps(counts)
        run.source_statuses = json.dumps(statuses)
        run.errors = json.dumps(errors)
        
        await self.session.commit()
        
    async def finalize_run(self, status: str):
        result = await self.session.execute(select(PipelineRun).where(PipelineRun.run_id == self.run_id))
        run = result.scalar_one_or_none()
        
        if not run:
            return
            
        run.status = status
        run.completed_at = datetime.utcnow()
        await self.session.commit()
