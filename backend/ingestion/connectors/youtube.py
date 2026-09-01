import os
from typing import List, Set, Dict
from datetime import datetime

# You need to run: pip install google-api-python-client
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from backend.ingestion.schemas import RawRecordSchema
from backend.ingestion.normalizer import normalize_record, NormalizerError

class MissingCredentialsError(Exception):
    pass

class YouTubeAPIIngester:
    def __init__(self, search_queries: List[str]):
        self.search_queries = search_queries
        api_key = os.getenv('YOUTUBE_API_KEY')
        if api_key:
            self.youtube = build('youtube', 'v3', developerKey=api_key)
        else:
            raise MissingCredentialsError("YOUTUBE_API_KEY is missing from environment.")

    def fetch_records(self) -> List[RawRecordSchema]:

        records: List[RawRecordSchema] = []
        video_ids: Set[str] = set()
        video_metadata: Dict[str, str] = {} # video_id -> title

        # Discovery step
        for query in self.search_queries:
            try:
                search_response = self.youtube.search().list(
                    q=query,
                    type='video',
                    part='snippet',
                    maxResults=25
                ).execute()
                
                for item in search_response.get('items', []):
                    video_id = item['id']['videoId']
                    video_ids.add(video_id)
                    video_metadata[video_id] = item['snippet']['title']
            except HttpError as e:
                print(f"YouTube search error for query '{query}': {e}")

        # Ingestion step
        for video_id in video_ids:
            title = video_metadata.get(video_id, "")
            
            # Check comment count if needed (optional optimization, here we just try to fetch comments)
            try:
                page_token = None
                while True:
                    response = self.youtube.commentThreads().list(
                        videoId=video_id,
                        part='snippet,replies',
                        maxResults=100,
                        pageToken=page_token
                    ).execute()
                    
                    for item in response.get('items', []):
                        top_comment = item['snippet']['topLevelComment']['snippet']
                        self._process_comment(top_comment, video_id, title, video_id, records)
                        
                        # Process replies included in the thread response
                        if 'replies' in item:
                            for reply in item['replies']['comments']:
                                self._process_comment(reply['snippet'], video_id, title, item['id'], records)
                                
                    page_token = response.get('nextPageToken')
                    if not page_token:
                        break
            except HttpError as e:
                # E.g., comments disabled for this video
                print(f"YouTube comment fetch error for video '{video_id}': {e}")
                
        return records

    def _process_comment(self, snippet, video_id, video_title, parent_id, records):
        raw_text = snippet.get('textOriginal', '')
        if not raw_text.strip():
            return
            
        published_at_str = snippet.get('publishedAt')
        published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00")) if published_at_str else None
        
        raw_dict = {
            "raw_record_id": f"youtube_{snippet.get('authorChannelId', {}).get('value', 'unknown')}_{published_at_str}", 
            # Note: authorChannelId is not stored in final dict but used for unique ID generation
            "source": "youtube",
            "source_type": "video_comment",
            "source_url": f"https://www.youtube.com/watch?v={video_id}",
            "video_id": video_id,
            "video_title": video_title,
            "parent_post_id": parent_id,
            "published_at": published_at,
            "raw_text": raw_text,
            "evidence_type": "myntra_specific" if "myntra" in raw_text.lower() else "category_level"
        }
        
        try:
            records.append(normalize_record(raw_dict))
        except NormalizerError:
            pass
