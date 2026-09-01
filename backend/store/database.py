from datetime import datetime, date
from typing import List, Optional, Any
import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import json

class Base(DeclarativeBase):
    pass

class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    
    run_id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    triggered_by: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    started_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime, nullable=True)
    status: Mapped[str] = mapped_column(sa.String)
    review_window_start: Mapped[Optional[date]] = mapped_column(sa.Date, nullable=True)
    review_window_end: Mapped[Optional[date]] = mapped_column(sa.Date, nullable=True)
    source_statuses: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)
    source_record_counts: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)
    relevant_record_count: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    observation_count: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    theme_count: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    opportunity_count: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    provider_model_versions: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    warnings: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)
    errors: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)

class RawRecord(Base):
    __tablename__ = "raw_records"

    raw_record_id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    source: Mapped[str] = mapped_column(sa.String, nullable=False)
    source_type: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    raw_text: Mapped[str] = mapped_column(sa.String, nullable=False)
    rating: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    product_context: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    evidence_type: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    parent_post_id: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    video_id: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    video_title: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)

class RunRecord(Base):
    __tablename__ = "run_records"
    
    run_record_id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    pipeline_run_id: Mapped[str] = mapped_column(sa.String, sa.ForeignKey("pipeline_runs.run_id"))
    raw_record_id: Mapped[str] = mapped_column(sa.String, sa.ForeignKey("raw_records.raw_record_id"))

class CleanedRecord(Base):
    __tablename__ = "cleaned_records"
    
    cleaned_record_id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    raw_record_id: Mapped[str] = mapped_column(sa.String, sa.ForeignKey("raw_records.raw_record_id"))
    cleaned_text: Mapped[str] = mapped_column(sa.String, nullable=False)
    is_duplicate: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    is_spam: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    cleaning_flags: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)

class ClassifiedRecord(Base):
    __tablename__ = "classified_records"
    
    classified_record_id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    cleaned_record_id: Mapped[str] = mapped_column(sa.String, sa.ForeignKey("cleaned_records.cleaned_record_id"))
    relevance_label: Mapped[str] = mapped_column(sa.String, nullable=False)
    relevance_confidence: Mapped[float] = mapped_column(sa.Float, nullable=False)
    signals_detected: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)

class Observation(Base):
    __tablename__ = "observations"
    
    observation_id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    source_record_id: Mapped[str] = mapped_column(sa.String, sa.ForeignKey("raw_records.raw_record_id"))
    cleaned_record_id: Mapped[str] = mapped_column(sa.String, sa.ForeignKey("cleaned_records.cleaned_record_id"))
    source: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    is_myntra_specific: Mapped[Optional[bool]] = mapped_column(sa.Boolean, nullable=True)
    journey_stage: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    wishlist_intent: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    purchase_intent: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    product_category: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    theme: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    topic: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    sentiment: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    problem_status: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    evidence_scope: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    primary_barrier: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    secondary_barriers: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)
    root_cause: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    uncertainty: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    information_needed: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    workaround: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    external_platform_used: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    alternative_considered: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    occasion: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    decision_outcome: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    segment_signal: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    evidence_quote: Mapped[str] = mapped_column(sa.String, nullable=False)
    ai_confidence: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    extracted_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime, nullable=True)
    model_id: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    created_in_pipeline_run_id: Mapped[str] = mapped_column(sa.String, sa.ForeignKey("pipeline_runs.run_id"))

class Theme(Base):
    __tablename__ = "themes"
    
    theme_id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    theme_name: Mapped[str] = mapped_column(sa.String, nullable=False)
    theme_label: Mapped[str] = mapped_column(sa.String, nullable=False)
    is_predefined: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    description: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    observation_count: Mapped[int] = mapped_column(sa.Integer, default=0)
    pct_of_relevant: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    common_root_causes: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)
    associated_wishlist_intents: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)
    associated_purchase_intents: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)
    affected_segments: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)
    recurring_uncertainties: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)
    recurring_info_needs: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)
    common_workarounds: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)
    external_research_behaviors: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)
    representative_quotes: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)
    source_distribution: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)
    myntra_specific_count: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    category_level_count: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    avg_ai_confidence: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)

class ThemeObservation(Base):
    __tablename__ = "theme_observations"
    
    theme_id: Mapped[str] = mapped_column(sa.String, sa.ForeignKey("themes.theme_id"), primary_key=True)
    observation_id: Mapped[str] = mapped_column(sa.String, sa.ForeignKey("observations.observation_id"), primary_key=True)

class OpportunityArea(Base):
    __tablename__ = "opportunity_areas"
    
    opportunity_id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    opportunity_title: Mapped[str] = mapped_column(sa.String, nullable=False)
    opportunity_description: Mapped[str] = mapped_column(sa.String, nullable=False)
    source_theme_ids: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)
    supporting_observation_count: Mapped[int] = mapped_column(sa.Integer, default=0)
    pct_of_relevant_observations: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    source_distribution: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)
    myntra_specific_count: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    category_level_count: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    associated_wishlist_intents: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)
    associated_purchase_intents: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)
    associated_segments: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)
    recurring_root_causes: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)
    recurring_uncertainties: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)
    recurring_info_needs: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)
    recurring_workarounds: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)
    external_research_behaviors: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)
    avg_evidence_confidence: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    representative_quotes: Mapped[Optional[str]] = mapped_column(sa.JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)

class OpportunityObservation(Base):
    __tablename__ = "opportunity_observations"
    
    opportunity_id: Mapped[str] = mapped_column(sa.String, sa.ForeignKey("opportunity_areas.opportunity_id"), primary_key=True)
    observation_id: Mapped[str] = mapped_column(sa.String, sa.ForeignKey("observations.observation_id"), primary_key=True)

class DatasetStats(Base):
    __tablename__ = "dataset_stats"
    
    run_id: Mapped[str] = mapped_column(sa.String, sa.ForeignKey("pipeline_runs.run_id"), primary_key=True)
    raw_record_count: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    cleaned_record_count: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    pct_cleaned: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    relevant_count: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    pct_relevant: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    observation_count: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    avg_observations_per_record: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    avg_ai_confidence: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    low_confidence_observation_count: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    extraction_failure_count: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)

class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    analysis_run_id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime, nullable=True)
    clustering_config_version: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    mapping_threshold_version: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)

class PredefinedTheme(Base):
    __tablename__ = "predefined_themes"
    theme_id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    canonical_name: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)

class ThemeAssignment(Base):
    __tablename__ = "theme_assignments"
    analysis_run_id: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    observation_id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    predefined_theme_id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    assignment_type: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    similarity_score: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    threshold_version: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)

class SemanticCluster(Base):
    __tablename__ = "semantic_clusters"
    cluster_id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    analysis_run_id: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    clustering_config_version: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    observation_count: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    unique_source_count: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    is_noise: Mapped[Optional[bool]] = mapped_column(sa.Boolean, nullable=True)
    canonical_label: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime, nullable=True)

class ClusterMembership(Base):
    __tablename__ = "cluster_memberships"
    cluster_id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    observation_id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    membership_probability: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)

class ClusterRepresentative(Base):
    __tablename__ = "cluster_representatives"
    analysis_run_id: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    cluster_id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    observation_id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    source_record_id: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    evidence_quote: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    primary_barrier: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    uncertainty: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)

class ClusterAggregation(Base):
    __tablename__ = "cluster_aggregations"
    analysis_run_id: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    cluster_id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    observation_count: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    unique_source_count: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    distributions_json: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)

class ClusterSynthesis(Base):
    __tablename__ = "cluster_synthesis"
    analysis_run_id: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    cluster_id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    canonical_name: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    primary_root_cause: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    primary_unmet_need: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)

class UnmetNeedContext(Base):
    __tablename__ = "unmet_need_context"
    unmet_need: Mapped[str] = mapped_column(sa.String, primary_key=True)
    observation_count: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    associated_barriers_json: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    associated_intents_json: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)

class Phase4OpportunityArea(Base):
    __tablename__ = "phase4_opportunity_areas"
    opportunity_id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    analysis_run_id: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    purchase_metric_relevance: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    wishlist_metric_relevance: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    supporting_needs_json: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)

class OpportunityEvidence(Base):
    __tablename__ = "opportunity_evidence"
    opportunity_id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    observation_id: Mapped[str] = mapped_column(sa.String, primary_key=True)
