import json
import os
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.sqlite import insert
from backend.ingestion.schemas import RawRecordSchema
from backend.store.database import RawRecord, RunRecord

class IngestionWriter:
    def __init__(self, run_id: str, data_dir: str = "data/raw"):
        self.run_id = run_id
        self.data_dir = Path(data_dir)
        self.jsonl_path = self.data_dir / f"run_{run_id}.jsonl"
        
        # Ensure directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    async def write_records(self, session: AsyncSession, records: list[RawRecordSchema]):
        if not records:
            return

        # 1. Write to JSONL
        with open(self.jsonl_path, "a", encoding="utf-8") as f:
            for record in records:
                # Use model_dump_json for Pydantic v2
                f.write(record.model_dump_json(exclude_none=True) + "\n")
        
        # 2. Upsert into database
        for record in records:
            # We use sqlite's ON CONFLICT DO UPDATE for idempotency, or just ignore.
            # Assuming upsert for raw_records
            stmt = insert(RawRecord).values(
                raw_record_id=record.raw_record_id,
                source=record.source,
                source_type=record.source_type,
                source_url=record.source_url,
                published_at=record.published_at,
                collected_at=record.collected_at,
                title=record.title,
                raw_text=record.raw_text,
                rating=record.rating,
                product_context=record.product_context,
                evidence_type=record.evidence_type,
                parent_post_id=record.parent_post_id,
                video_id=record.video_id,
                video_title=record.video_title,
            ).on_conflict_do_update(
                index_elements=['raw_record_id'],
                set_={
                    'title': record.title,
                    'raw_text': record.raw_text,
                    'rating': record.rating,
                    'collected_at': record.collected_at
                }
            )
            await session.execute(stmt)

            # Insert into RunRecord junction table (ignore if exists)
            run_stmt = insert(RunRecord).values(
                run_record_id=f"{self.run_id}_{record.raw_record_id}",
                pipeline_run_id=self.run_id,
                raw_record_id=record.raw_record_id
            ).on_conflict_do_nothing()
            
            await session.execute(run_stmt)
            
        await session.commit()
