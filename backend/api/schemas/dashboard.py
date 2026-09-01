from pydantic import BaseModel
from typing import List, Dict, Optional, Any

class ThemeStat(BaseModel):
    theme_id: str
    canonical_name: str
    observation_count: int
    unique_source_count: int
    mapping_rate_pct: float

class ClusterStat(BaseModel):
    cluster_id: str
    canonical_label: Optional[str]
    observation_count: int
    unique_source_count: int
    evidence_role: str = "unreviewed"
    review_status: str = "unreviewed"

class RepresentativeQuote(BaseModel):
    quote: str
    source: Optional[str] = None
    source_url: Optional[str] = None

class OpportunityStat(BaseModel):
    opportunity_id: str
    title: str
    description: Optional[str] = None
    original_generated_label: Optional[str] = None
    metric_relevance: str
    unique_source_count: int
    dataset_percentage: float
    denominator: int
    denominator_definition: str
    supporting_unmet_needs: List[str]
    representative_quotes: List[RepresentativeQuote]
    calculation_note: str
    validation_status: str


class DistributionStat(BaseModel):
    name: str
    count: int

class DistributionResponse(BaseModel):
    items: List[DistributionStat]
    denominator: int
    denominator_definition: str
    denominator_scope: str
    active_filters: Dict[str, Any]
    classified_count: Optional[int] = None
    unclassified_count: Optional[int] = None

class DatasetStatsResponse(BaseModel):
    total_raw_records: int
    cleaned_records: int
    relevant_records: int
    processed_source_records: int
    canonical_observations: int
    source_distribution_analyzed: Dict[str, int]
    source_distribution_raw: Dict[str, int]
    date_range: Dict[str, str]
    analysis_run_metadata: Dict[str, str]
