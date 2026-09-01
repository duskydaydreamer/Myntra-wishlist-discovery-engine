import requests
import time
from datetime import datetime, timedelta
from typing import List

from backend.ingestion.schemas import RawRecordSchema
from backend.ingestion.normalizer import normalize_record, NormalizerError

class AppStoreAdapter:
    def __init__(self, window_weeks: int = 12):
        self.app_name = 'myntra'
        self.app_id = 907394059
        self.country = 'in'
        self.window_weeks = window_weeks
        self.cutoff_date = datetime.now() - timedelta(weeks=window_weeks)
        
    def fetch_records(self) -> List[RawRecordSchema]:
        records: List[RawRecordSchema] = []
        pages = 10 # RSS only supports up to 10 pages (500 reviews)
        
        for page in range(1, pages + 1):
            url = f"https://itunes.apple.com/{self.country}/rss/customerreviews/page={page}/id={self.app_id}/sortby=mostrecent/json"
            
            try:
                response = requests.get(url, timeout=10)
                if response.status_code != 200:
                    break
                    
                data = response.json()
                entries = data.get('feed', {}).get('entry', [])
                
                # Skip metadata entry if present
                if entries and 'im:name' in entries[0]:
                    entries = entries[1:]
                    
                if not entries:
                    break
                    
                for entry in entries:
                    date_str = entry.get('updated', {}).get('label')
                    # Example format: "2023-01-01T12:00:00-07:00"
                    # Python 3.9 fromisoformat handles simple offsets if format is strictly ISO
                    try:
                        pub_date = datetime.fromisoformat(date_str)
                        # Make naive for comparison
                        pub_date = pub_date.replace(tzinfo=None)
                    except ValueError:
                        continue
                        
                    if pub_date < self.cutoff_date:
                        continue
                        
                    raw_dict = {
                        "raw_record_id": f"app_store_{entry.get('id', {}).get('label')}",
                        "source": "app_store",
                        "source_type": "review",
                        "source_url": f"https://apps.apple.com/{self.country}/app/{self.app_name}/id{self.app_id}",
                        "published_at": pub_date,
                        "raw_text": entry.get('content', {}).get('label', ''),
                        "title": entry.get('title', {}).get('label', ''),
                        "rating": float(entry.get('im:rating', {}).get('label', 0)),
                        "evidence_type": "myntra_specific",
                        "product_context": "myntra"
                    }
                    
                    try:
                        normalized = normalize_record(raw_dict)
                        records.append(normalized)
                    except NormalizerError:
                        pass
                        
                time.sleep(1) # Be gentle to the API
                
            except Exception as e:
                print(f"App Store ingestion error on page {page}: {e}")
                break
                
        return records
