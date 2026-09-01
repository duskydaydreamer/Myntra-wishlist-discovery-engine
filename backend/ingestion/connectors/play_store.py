import uuid
from datetime import datetime, timedelta, timezone
from google_play_scraper import reviews, Sort
from typing import List, Dict, Any

from backend.ingestion.schemas import RawRecordSchema
from backend.ingestion.normalizer import normalize_record, NormalizerError

class PlayStoreAdapter:
    def __init__(self, window_weeks: int = 12):
        self.app_id = "com.myntra.android"
        self.window_weeks = window_weeks
        # Play Store reviews usually don't have timezone attached natively, we will assume UTC or local.
        # google-play-scraper returns datetime object.
        self.cutoff_date = datetime.now() - timedelta(weeks=window_weeks)
        
    def fetch_records(self) -> List[RawRecordSchema]:
        records: List[RawRecordSchema] = []
        continuation_token = None
        
        while True:
            # Fetch batch
            result, continuation_token = reviews(
                self.app_id,
                lang='en',
                country='in',
                sort=Sort.NEWEST,
                count=100, # fetch 100 at a time
                continuation_token=continuation_token
            )
            
            if not result:
                break
                
            oldest_in_batch = result[-1]['at']
            
            for review in result:
                if review['at'] < self.cutoff_date:
                    continue
                    
                # Strip userName and other PII
                review.pop('userName', None)
                review.pop('userImage', None)
                
                raw_dict = {
                    "raw_record_id": f"play_store_{review['reviewId']}",
                    "source": "play_store",
                    "source_type": "review",
                    "source_url": f"https://play.google.com/store/apps/details?id={self.app_id}",
                    "published_at": review['at'],
                    "raw_text": review.get('content', ''),
                    "rating": float(review.get('score', 0)),
                    "evidence_type": "myntra_specific",
                    "product_context": "myntra"
                }
                
                try:
                    normalized = normalize_record(raw_dict)
                    records.append(normalized)
                except NormalizerError:
                    pass # Ignore records missing text
            
            if oldest_in_batch < self.cutoff_date or continuation_token is None:
                break
                
        return records
