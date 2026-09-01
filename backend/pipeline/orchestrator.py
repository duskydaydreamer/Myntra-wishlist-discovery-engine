import asyncio
import datetime
import sqlite3
import os

from sqlalchemy.orm import Session
from backend.store.database import PipelineRun

# Phase 1
from backend.pipeline.runner import run_ingestion as phase1_ingestion
from backend.cleaning.cleaning_runner import run_pipeline as run_cleaning

# Phase 2
from scripts.phase2b_scaling_optimized import run_classification

# Phase 3
from scripts.phase3b_production_run import run_extraction

# Phase 4
from backend.analysis.phase4_1_representation_eval import run_representation_eval
from backend.analysis.phase4_2_predefined_mapping import run_predefined_mapping
from backend.analysis.phase4_3_emergent_clustering import run_emergent_clustering
from backend.analysis.phase4_4_aggregation import run_aggregation
from backend.analysis.phase4_5_llm_synthesis import run_llm_synthesis
from backend.analysis.phase4_6_taxonomy import run_taxonomy
from backend.analysis.phase4_7_unmet_need_context import run_unmet_need_context
from backend.analysis.phase4_8_opportunities import run_opportunities
from backend.analysis.phase4_9_knowledge_graph import run_knowledge_graph
from backend.analysis.phase4_10_quantification import run_quantification


async def run_canonical_pipeline(db_session: Session, run_id: str):
    """
    The canonical end-to-end pipeline runner for Myntra NL Discovery Pulse.
    """
    db_path = "data/discovery_pulse.db"
    conn = sqlite3.connect(db_path)
    
    # 1. Ingestion
    print(f"[{run_id}] Running Ingestion...")
    await phase1_ingestion(db_session, run_id)
    
    # 2. Cleaning
    print(f"[{run_id}] Running Cleaning...")
    await run_cleaning(db_session)
    
    # 3. Classification
    print(f"[{run_id}] Running Classification...")
    await run_classification(db_path)
    
    # 4. Extraction & Embeddings
    print(f"[{run_id}] Running Extraction & Embeddings...")
    run_extraction(db_path, run_id)
    
    # 5. Check effective Phase 4 Observation Set fingerprint
    import hashlib
    
    current_obs_query = """
        SELECT o.observation_id 
        FROM observations o
        JOIN run_records rr ON o.source_record_id = rr.raw_record_id
        WHERE rr.pipeline_run_id = ?
        ORDER BY o.observation_id
    """
    current_obs_ids = [row[0] for row in conn.execute(current_obs_query, (run_id,)).fetchall()]
    current_fingerprint = hashlib.sha256(",".join(current_obs_ids).encode()).hexdigest()
    
    # Find previous successful run
    prev_run_row = conn.execute(
        "SELECT run_id FROM pipeline_runs WHERE status = 'completed' AND run_id != ? ORDER BY completed_at DESC LIMIT 1",
        (run_id,)
    ).fetchone()
    
    prev_fingerprint = None
    if prev_run_row:
        prev_run_id = prev_run_row[0]
        prev_obs_ids = [row[0] for row in conn.execute(current_obs_query, (prev_run_id,)).fetchall()]
        prev_fingerprint = hashlib.sha256(",".join(prev_obs_ids).encode()).hexdigest()
    
    if prev_fingerprint and current_fingerprint == prev_fingerprint:
        print(f"[{run_id}] EFFECTIVE PHASE 4 OBSERVATION SET UNCHANGED (Fingerprint: {current_fingerprint[:8]}). SKIPPING PHASE 4.")
    else:
        print(f"[{run_id}] EFFECTIVE PHASE 4 OBSERVATION SET CHANGED. RUNNING PHASE 4.")
        
        # 5. Phase 4 - run stages sequentially
        # Note: run_representation_eval is skipped as it is an HP sweep, not part of regular pipeline.
        print(f"[{run_id}] Running Predefined Mapping...")
        run_predefined_mapping(run_id)
        
        print(f"[{run_id}] Running Emergent Clustering...")
        run_emergent_clustering(run_id)
        
        print(f"[{run_id}] Running Aggregation...")
        run_aggregation(run_id)
        
        print(f"[{run_id}] Running LLM Synthesis...")
        run_llm_synthesis(run_id)
        
        print(f"[{run_id}] Running Taxonomy...")
        run_taxonomy(run_id)
        
        print(f"[{run_id}] Running Unmet Need Context...")
        run_unmet_need_context(run_id)
        
        print(f"[{run_id}] Running Opportunities...")
        run_opportunities(run_id)
        
        print(f"[{run_id}] Running Knowledge Graph...")
        run_knowledge_graph(run_id)
        
        print(f"[{run_id}] Running Quantification...")
        run_quantification(run_id)
        
    conn.close()
    
    # Finalize run status
    run_record = db_session.query(PipelineRun).filter(PipelineRun.run_id == run_id).first()
    if run_record:
        run_record.status = "completed"
        run_record.completed_at = datetime.datetime.utcnow()
        run_record.observation_count = len(current_obs_ids)
        db_session.commit()
    
    print(f"[{run_id}] Pipeline Completed Successfully.")
