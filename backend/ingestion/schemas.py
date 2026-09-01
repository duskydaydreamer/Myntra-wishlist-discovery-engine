from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class RawRecordSchema(BaseModel):
    raw_record_id: str
    source: str
    source_type: Optional[str] = None
    source_url: Optional[str] = None
    published_at: Optional[datetime] = None
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    title: Optional[str] = None
    raw_text: str
    rating: Optional[float] = None
    product_context: Optional[str] = None
    evidence_type: Optional[str] = None
    parent_post_id: Optional[str] = None
    video_id: Optional[str] = None
    video_title: Optional[str] = None
    search_query: Optional[str] = None
    selection_reason: Optional[str] = None
    comment_sampling_rule: Optional[str] = None
