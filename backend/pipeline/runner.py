import argparse
import asyncio
import uuid
import yaml
from pathlib import Path
import os

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from backend.ingestion.connectors.play_store import PlayStoreAdapter
from backend.ingestion.connectors.app_store import AppStoreAdapter
from backend.ingestion.connectors.reddit import RedditThreadIngester
from backend.ingestion.connectors.youtube import YouTubeAPIIngester
from backend.ingestion.writer import IngestionWriter
from backend.ingestion.run_tracker import RunTracker

async def run_ingestion(sources, config):
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    
    db_url = os.environ.get("DATABASE_URL", config.get("storage", {}).get("db_url", "sqlite:///data/discovery_pulse.db"))
    # For async sqlalchemy with sqlite, URL needs to be sqlite+aiosqlite
    if db_url.startswith("sqlite:///") and not db_url.startswith("sqlite+aiosqlite:///"):
        db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        
    engine = create_async_engine(db_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    writer = IngestionWriter(run_id=run_id)
    
    async with async_session() as session:
        tracker = RunTracker(session, run_id)
        await tracker.initialize_run()
        
        has_errors = False
        completed_sources = 0
        
        for source in sources:
            print(f"Starting ingestion for {source}...")
            records = []
            error = None
            
            try:
                if source == "play_store":
                    weeks = config.get("ingestion", {}).get("play_store_window_weeks", 12)
                    adapter = PlayStoreAdapter(window_weeks=weeks)
                    records = adapter.fetch_records()
                    
                elif source == "app_store":
                    weeks = config.get("ingestion", {}).get("app_store_window_weeks", 12)
                    adapter = AppStoreAdapter(window_weeks=weeks)
                    records = adapter.fetch_records()
                    
                elif source == "reddit":
                    threads = config.get("ingestion", {}).get("reddit_threads", [])
                    adapter = RedditThreadIngester(thread_urls=threads)
                    records = adapter.fetch_records()
                    
                elif source == "youtube":
                    queries = config.get("ingestion", {}).get("youtube_search_queries", [])
                    adapter = YouTubeAPIIngester(search_queries=queries)
                    records = adapter.fetch_records()
                else:
                    print(f"Unknown source: {source}")
                    continue
                    
                # Write records
                await writer.write_records(session, records)
                print(f"Ingested {len(records)} records from {source}.")
                
            except Exception as e:
                print(f"Error ingesting from {source}: {e}")
                error = str(e)
                if "MissingCredentialsError" in str(type(e).__name__):
                    error = "skipped_missing_credentials"
                has_errors = True
                
            finally:
                if error == "skipped_missing_credentials":
                    status = "skipped_missing_credentials"
                else:
                    status = "failed" if error else "completed"
                    
                if status == "completed":
                    completed_sources += 1
                await tracker.update_source_status(source, status, len(records), error)
                
        # Final status
        if completed_sources == 0 and sources:
            final_status = "failed"
        elif has_errors:
            final_status = "partial"
        else:
            final_status = "completed"
            
        await tracker.finalize_run(final_status)
        print(f"Pipeline run {run_id} finished with status: {final_status}")
        
    await engine.dispose()

def load_config():
    config_path = Path("config/config.yaml")
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    parser = argparse.ArgumentParser(description="Myntra Discovery Pulse Pipeline Runner")
    parser.add_argument("--step", required=True, choices=["ingestion"], help="Pipeline step to run")
    parser.add_argument("--sources", type=str, help="Comma-separated list of sources to run")
    
    args = parser.parse_args()
    config = load_config()
    
    if args.step == "ingestion":
        # Determine sources
        if args.sources:
            sources = [s.strip() for s in args.sources.split(",")]
        else:
            sources = config.get("ingestion", {}).get("sources_enabled", [])
            
        asyncio.run(run_ingestion(sources, config))

if __name__ == "__main__":
    main()
