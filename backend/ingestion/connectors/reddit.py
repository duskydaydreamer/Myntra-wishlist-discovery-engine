import os
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List
import time

from backend.ingestion.schemas import RawRecordSchema
from backend.ingestion.normalizer import normalize_record, NormalizerError

class MissingCredentialsError(Exception):
    pass

class RedditThreadIngester:
    def __init__(self, thread_urls: List[str]):
        self.thread_urls = thread_urls
        self.use_rss_fallback = True
        
        print("WARNING: Using Reddit RSS Fallback. This is strictly a fallback for limited development testing.")
        print("This method will not pull complete comment trees like PRAW.")
        
    def fetch_records(self) -> List[RawRecordSchema]:
        records: List[RawRecordSchema] = []
        
        headers = {
            'User-Agent': 'python:myntra_research_bot:v1.0 (by /u/test)'
        }
        
        for url in self.thread_urls:
            # Ensure URL ends with .rss
            rss_url = url.rstrip('/')
            if not rss_url.endswith('.rss'):
                rss_url += '.rss'
                
            try:
                response = requests.get(rss_url, headers=headers, timeout=10)
                if response.status_code != 200:
                    print(f"Failed to fetch RSS for {rss_url}: {response.status_code}")
                    continue
                    
                feed = feedparser.parse(response.content)
                
                # The first entry in Reddit RSS is typically the main post, the rest are top-level comments
                for i, entry in enumerate(feed.entries):
                    # Clean HTML from RSS content
                    soup = BeautifulSoup(entry.summary, "html.parser")
                    clean_text = soup.get_text(separator="\n", strip=True)
                    
                    date_str = entry.get('updated', '')
                    try:
                        # e.g., '2023-07-04T17:48:33+00:00'
                        pub_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        pub_date = pub_date.replace(tzinfo=None)
                    except ValueError:
                        pub_date = None
                    
                    record_dict = {
                        "raw_record_id": f"reddit_rss_{entry.id}",
                        "source": "reddit",
                        "source_type": "post" if i == 0 else "comment",
                        "source_url": url,
                        "published_at": pub_date,
                        "title": entry.title if i == 0 else "",
                        "raw_text": clean_text,
                        "evidence_type": "myntra_specific"
                    }
                    
                    try:
                        normalized = normalize_record(record_dict)
                        records.append(normalized)
                    except NormalizerError:
                        pass
                        
                # Reddit's unauthenticated RSS rate limits are very strict. 
                # We need a longer delay to prevent 429 Too Many Requests.
                print(f"Waiting 65 seconds before fetching the next thread...")
                time.sleep(65) 
            except Exception as e:
                print(f"Error processing Reddit RSS {url}: {e}")
                
        return records
