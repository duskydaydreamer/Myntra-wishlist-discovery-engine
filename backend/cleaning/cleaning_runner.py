import argparse
import asyncio
import json
import uuid
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert

from backend.store.database import RawRecord, CleanedRecord, ClassifiedRecord, PipelineRun
from backend.cleaning.pii_masker import PIIMasker
from backend.cleaning.deduplicator import Deduplicator
from backend.cleaning.spam_filter import SpamFilter
from backend.cleaning.normalizer import TextNormalizer
from backend.classification.relevance_classifier import RelevanceClassifier

async def run_cleaning(config):
    run_id = f"clean_run_{uuid.uuid4().hex[:8]}"
    
    db_url = config.get("storage", {}).get("db_url", "sqlite:///data/discovery_pulse.db")
    if db_url.startswith("sqlite:///") and not db_url.startswith("sqlite+aiosqlite:///"):
        db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        
    engine = create_async_engine(db_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    masker = PIIMasker()
    dedup = Deduplicator(near_duplicate_similarity=config.get("thresholds", {}).get("near_duplicate_similarity", 0.92))
    spam_filter = SpamFilter()
    normalizer = TextNormalizer()
    classifier = RelevanceClassifier(confidence_threshold=config.get("thresholds", {}).get("relevance_confidence_min", 0.70))
    
    cleaned_dir = Path("data/cleaned")
    classified_dir = Path("data/classified")
    cleaned_dir.mkdir(parents=True, exist_ok=True)
    classified_dir.mkdir(parents=True, exist_ok=True)
    
    cleaned_file = cleaned_dir / f"{run_id}.jsonl"
    classified_file = classified_dir / f"{run_id}.jsonl"

    async with async_session() as session:
        # 1. Fetch raw records
        stmt = select(RawRecord).outerjoin(
            CleanedRecord, RawRecord.raw_record_id == CleanedRecord.raw_record_id
        ).where(CleanedRecord.cleaned_record_id == None)
        
        result = await session.execute(stmt)
        raw_records = result.scalars().all()
        
        print(f"STAGE 1: Found {len(raw_records)} records for local pre-filtering.")
        
        # Local stats
        stats = {
            "total_raw": len(raw_records),
            "skipped_duplicate": 0,
            "skipped_spam": 0,
            "skipped_non_english": 0, # Strict other languages (Chinese, etc)
            "skipped_app_technical": 0,
            "skipped_generic_low_info": 0,
            "skipped_empty_or_whitespace": 0,
            "skipped_url_only": 0,
            "skipped_emoji_or_symbol_only": 0,
            "kept_shopping_signal_short": 0, # < 8 words but kept
            "kept_fallback": 0,
            "kept_shopping_signal": 0,
            "kept_hinglish": 0,
            "skipped_pure_hindi": 0
        }
        
        kept_for_llm = []
        
        # We can run Stage 1 locally, extremely fast
        from tqdm import tqdm
        import re
        batch_size = 2000
        current_batch = []
        
        for raw in tqdm(raw_records, desc="Local Cleaning & Pre-filtering"):
            is_dup, dup_of = dedup.check_duplicate(raw.raw_record_id, raw.raw_text, raw.source)
            
            cleaned_text = masker.mask(raw.raw_text) if not is_dup else raw.raw_text
            cleaned_text = normalizer.normalize(cleaned_text) if not is_dup else cleaned_text
            lang = normalizer.detect_language(cleaned_text) if not is_dup else "unknown"
            
            if not is_dup:
                is_spam, cleaning_flags = await spam_filter.filter_record(cleaned_text)
            else:
                is_spam, cleaning_flags = False, []
                
            # Hinglish vs Pure Hindi detection
            is_pure_hindi = False
            is_hinglish = False
            if lang == "hi" or lang == "mr" or lang == "ne":
                # Check if it contains mostly Devanagari
                devanagari_chars = len(re.findall(r'[\u0900-\u097F]', cleaned_text))
                latin_chars = len(re.findall(r'[a-zA-Z]', cleaned_text))
                if devanagari_chars > 0 and latin_chars == 0:
                    is_pure_hindi = True
                else:
                    is_hinglish = True
            
            # If not english, not unknown, not hinglish, not pure hindi -> strict non_english
            if lang not in ["en", "unknown", "hi", "mr", "ne"]:
                cleaning_flags.append("non_english")
                
            prefilter_status, prefilter_reason = "skipped", "duplicate_or_spam"
            
            if not is_dup and not is_spam and "non_english" not in cleaning_flags:
                if is_pure_hindi:
                    prefilter_status, prefilter_reason = "skipped", "language_skipped_hindi"
                else:
                    prefilter_status, prefilter_reason = classifier.deterministic_prefilter(cleaned_text)
            
            cleaning_flags.append(f"prefilter_status:{prefilter_status}")
            cleaning_flags.append(f"prefilter_reason:{prefilter_reason}")
            
            # Update Stats
            if is_dup: stats["skipped_duplicate"] += 1
            elif is_spam: stats["skipped_spam"] += 1
            elif "non_english" in cleaning_flags: stats["skipped_non_english"] += 1
            elif is_pure_hindi: stats["skipped_pure_hindi"] += 1
            elif prefilter_status == "kept":
                words = cleaned_text.strip().split()
                if len(words) < 8:
                    stats["kept_shopping_signal_short"] += 1
                if is_hinglish:
                    stats["kept_hinglish"] += 1
                
                if prefilter_reason == "fallback_kept":
                    stats["kept_fallback"] += 1
                else:
                    stats["kept_shopping_signal"] += 1
            else:
                if prefilter_reason == "empty_or_whitespace": stats["skipped_empty_or_whitespace"] += 1
                elif prefilter_reason == "url_only": stats["skipped_url_only"] += 1
                elif prefilter_reason == "emoji_or_symbol_only": stats["skipped_emoji_or_symbol_only"] += 1
                elif prefilter_reason == "app_technical_only": stats["skipped_app_technical"] += 1
                else: stats["skipped_generic_low_info"] += 1
            
            clean_id = f"clean_{raw.raw_record_id}"
            
            current_batch.append({
                "cleaned_record_id": clean_id,
                "raw_record_id": raw.raw_record_id,
                "cleaned_text": cleaned_text,
                "is_duplicate": is_dup,
                "is_spam": is_spam,
                "cleaning_flags": json.dumps(cleaning_flags)
            })
            
            if prefilter_status == "kept":
                kept_for_llm.append({
                    "raw_id": raw.raw_record_id,
                    "clean_id": clean_id,
                    "text": cleaned_text,
                    "source": raw.source
                })
                
            if len(current_batch) >= batch_size:
                await session.execute(insert(CleanedRecord).on_conflict_do_nothing(), current_batch)
                await session.commit()
                current_batch = []
                
        if current_batch:
            await session.execute(insert(CleanedRecord).on_conflict_do_nothing(), current_batch)
            await session.commit()
        
        # 2. Stratified Sampling & LLM Classification PAUSED
        # As per user instructions, we pause LLM classification until the model is approved.
        
        # 4. Generate Report (Local Only)
        print("\n--- PHASE 2 DEVELOPMENT RUN REPORT (LOCAL ONLY) ---")
        print(f"Total Raw Records Evaluated: {stats['total_raw']}")
        print(f"Skipped - Duplicates: {stats['skipped_duplicate']}")
        print(f"Skipped - Empty/No Text: {stats['skipped_empty_or_whitespace']}")
        print(f"Skipped - Emoji/Symbol Only: {stats['skipped_emoji_or_symbol_only']}")
        print(f"Skipped - Spam (Heuristic): {stats['skipped_spam']}")
        print(f"Skipped - Pure Hindi (Tagged): {stats['skipped_pure_hindi']}")
        print(f"Skipped - App Technical: {stats['skipped_app_technical']}")
        print(f"Skipped - Generic Short/Low Info: {stats['skipped_generic_low_info']}")
        print(f"Skipped - URL Only: {stats['skipped_url_only']}")
        print(f"Skipped - Other Foreign Langs: {stats['skipped_non_english']}")
        
        print(f"\nKEPT FOR LLM:")
        print(f"Total Kept: {len(kept_for_llm)}")
        print(f" -> Kept Shopping Signals: {stats['kept_shopping_signal']}")
        print(f" -> Kept Fallbacks (Recall focus): {stats['kept_fallback']}")
        print(f" -> Kept despite <8 words: {stats['kept_shopping_signal_short']}")
        print(f" -> Kept Hinglish/Mixed: {stats['kept_hinglish']}")
            
        with open("data/phase2_dev_report.txt", "w") as f:
            f.write(json.dumps({"local_stats": stats}, indent=2))
            
    await engine.dispose()

def main():
    import yaml
    config_path = Path("config/config.yaml")
    config = {}
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            
    asyncio.run(run_cleaning(config))

if __name__ == "__main__":
    main()
