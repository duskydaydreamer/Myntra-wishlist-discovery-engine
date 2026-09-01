from pydantic import BaseModel
from typing import List, Optional

class ObservationResponse(BaseModel):
    observation_id: str
    source: Optional[str]
    evidence_quote: str
    primary_barrier: Optional[str]
    wishlist_intent: Optional[str]
    purchase_intent: Optional[str]
    journey_stage: Optional[str]
    decision_outcome: Optional[str]
    uncertainty: Optional[str]
    ai_confidence: Optional[float]
    topic: Optional[str]
    sentiment: Optional[str]
    problem_status: Optional[str]
    evidence_scope: Optional[str]
    predefined_themes: List[str]
    emergent_clusters: List[str]

class EvidenceListResponse(BaseModel):
    items: List[ObservationResponse]
    total: int
    page: int
    size: int

class ObservationDetailResponse(ObservationResponse):
    source_url: Optional[str]
    source_record_id: str
    is_myntra_specific: Optional[bool]
    product_category: Optional[str]
    secondary_barriers: Optional[List[str]]
    root_cause: Optional[str]
    information_needed: Optional[str]
    workaround: Optional[str]
    external_platform_used: Optional[str]
    alternative_considered: Optional[str]
    occasion: Optional[str]
    segment_signal: Optional[str]
    opportunity_ids: List[str]
